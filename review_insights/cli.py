"""命令行入口。

用法示例：
  python -m review_insights.cli data/reviews.csv -o output/report.html
  python -m review_insights.cli data/reviews.xlsx --text "评论" --rating "评分" --date "时间"
  python -m review_insights.cli data/reviews.csv --engine deepseek --source "Lazada 竞品A"
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="review_insights",
        description="把一份评论数据变成中文 HTML 洞察报告。",
    )
    parser.add_argument("input", help="评论文件路径（CSV 或 Excel）")
    parser.add_argument("--text", help="评论文本列名（自动识别不到时指定）")
    parser.add_argument("--rating", help="评分列名")
    parser.add_argument("--date", help="日期列名")
    parser.add_argument("-o", "--output", default="output/report.html", help="输出 HTML 路径")
    parser.add_argument("--title", default="跨境电商评论洞察报告", help="报告标题")
    parser.add_argument("--source", help="数据来源说明（显示在报告头部，如品牌/商品名）")
    parser.add_argument(
        "--engine", choices=["auto", "offline", "small", "deepseek"], default="auto",
        help="情感分析引擎：offline 离线（免费）、small 小模型、deepseek 大模型、auto 自动",
    )
    parser.add_argument("--top-n", type=int, default=20, help="高频词数量")
    args = parser.parse_args(argv)

    from .analyze import analyze
    from .config import load_config
    from .io import load_reviews
    from .report import build_report
    from .sentiment import get_engine
    from .translate import translate_words
    from . import visualize

    config = load_config()

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
        analysis["pos_words"] + analysis["neg_words"], config
    )

    charts = {
        "pie": visualize.sentiment_pie_option(analysis["sentiment_counts"]),
        "pos_words": visualize.top_words_option(analysis["pos_words"], "正面高频词", "#2e9e6b"),
        "neg_words": visualize.top_words_option(analysis["neg_words"], "负面高频词（差评归因）", "#d94b4b"),
    }
    if analysis["trend"]:
        charts["trend"] = visualize.trend_line_option(analysis["trend"])

    html = build_report(
        analysis, charts,
        title=args.title, source=args.source, engine_name=engine.name,
    )

    out_path = args.output
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"报告已生成：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
