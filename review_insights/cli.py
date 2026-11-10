"""命令行入口。

自动识别数据类型，走对应分析路径：
  - 文本评论 → 情感分析 + 中文洞察报告
  - 纯数值数据（股票/销售/指标）→ 描述统计 + 趋势 + 分布报告

用法示例：
  python -m review_insights.cli data/reviews.csv -o output/report.html
  python -m review_insights.cli data/reviews.xlsx --text "评论" --rating "评分" --date "时间"
  python -m review_insights.cli data/reviews.csv --engine deepseek --source "Lazada 竞品A"
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd


def _read_raw(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def _write_html(html: str, out_path: str) -> None:
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成：{out_path}")


def _run_numeric(args, raw: pd.DataFrame, config) -> int:
    from . import numeric as num

    print("识别为数值数据，开始数值分析…")
    analysis = num.analyze_numeric(raw)

    charts = {}
    if analysis["trend"]:
        charts["trend"] = num.trend_option(analysis["trend"])
    if analysis["dist"]:
        charts["dist"] = num.dist_option(analysis["dist"], analysis["main_col"])

    insights = num.generate_insights(analysis, config)
    if insights:
        print("已用 LLM 生成分析结论")

    title = args.title or "数据分析报告"
    html = num.build_numeric_report(
        analysis, charts, title=title, source=args.source, insights=insights,
    )
    _write_html(html, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="review_insights",
        description="把一份数据（评论或纯数值）变成中文 HTML 分析报告，自动识别类型。",
    )
    parser.add_argument("input", help="数据文件路径（CSV 或 Excel）")
    parser.add_argument("--text", help="评论文本列名（自动识别不到时指定）")
    parser.add_argument("--rating", help="评分列名")
    parser.add_argument("--date", help="日期列名")
    parser.add_argument("-o", "--output", default="output/report.html", help="输出 HTML 路径")
    parser.add_argument("--title", default=None, help="报告标题")
    parser.add_argument("--source", help="数据来源说明（显示在报告头部，如品牌/商品名）")
    parser.add_argument(
        "--engine", choices=["auto", "offline", "small", "kimi", "deepseek"], default="auto",
        help="情感分析引擎（仅评论数据有效）：offline/small/kimi/deepseek/auto",
    )
    parser.add_argument("--top-n", type=int, default=20, help="高频词数量（仅评论数据）")
    args = parser.parse_args(argv)

    from .config import load_config
    from .detect import detect_mode

    config = load_config()

    # 读原始数据并探测类型
    raw = _read_raw(args.input)
    raw = raw.dropna(axis=1, how="all")
    mode = detect_mode(raw)

    if mode == "numeric":
        return _run_numeric(args, raw, config)

    # ---- 文本评论分析 ----
    from .analyze import analyze
    from .conclusion import generate_findings
    from .io import load_reviews
    from .report import build_report
    from .sentiment import get_engine
    from .translate import translate_sentences, translate_words
    from . import visualize

    try:
        engine = get_engine(config, args.engine)
    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    print(f"分析引擎：{engine.name}")

    df = load_reviews(args.input, text_col=args.text, rating_col=args.rating, date_col=args.date)
    print(f"读取评论 {len(df)} 条，开始情感分析…")

    sent = engine.analyze(df["text"].tolist())
    df = df.join(sent)

    analysis = analyze(df, top_n=args.top_n)
    analysis["word_trans"] = translate_words(
        analysis["pos_words"] + analysis["neg_words"], config, engine.name
    )
    analysis["example_trans"] = translate_sentences(
        analysis["pos_examples"] + analysis["neg_examples"], config, engine.name
    )

    charts = {
        "pie": visualize.sentiment_pie_option(analysis["sentiment_counts"]),
        "pos_words": visualize.top_words_option(analysis["pos_words"], "正面高频词", "#2e9e6b"),
        "neg_words": visualize.top_words_option(analysis["neg_words"], "负面高频词（差评归因）", "#d94b4b"),
    }
    if analysis["trend"]:
        charts["trend"] = visualize.trend_line_option(analysis["trend"])
    if analysis.get("rating_dist"):
        charts["rating_dist"] = visualize.rating_dist_option(analysis["rating_dist"])

    findings = generate_findings(analysis, config, engine.name)
    if findings:
        print("已用 LLM 生成详细结论建议")
    elif engine.name != "offline":
        print("注意：LLM 生成结论失败（可能是限流或网络问题），已退回模板文字")

    title = args.title or "跨境电商评论洞察报告"
    html = build_report(
        analysis, charts,
        title=title, source=args.source, engine_name=engine.name,
        findings=findings,
    )
    _write_html(html, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
