"""HTML 中文报告生成。

输入分析结果和 ECharts option 配置，输出一个单文件、离线可看的中文报告。
ECharts JS 内联进 HTML，图表交互式（可悬停看数据、缩放），无需联网。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_ENGINE_NAMES = {
    "offline": "离线（SnowNLP + VADER）",
    "small": "小模型（Qwen）",
    "kimi": "Kimi",
    "deepseek": "DeepSeek",
}


def _load_echarts_js() -> str:
    """读取内嵌的 ECharts 库；找不到时返回空串（降级为无图表）。"""
    p = Path(__file__).parent / "static" / "echarts.min.js"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _fmt_date_range(date_range) -> str:
    if date_range is None:
        return "—"
    start, end = date_range
    return f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"


def _fmt_words(words: list[str], word_trans: dict[str, str]) -> list[str]:
    """把词列表格式化为「原词（中文翻译）」形式。"""
    out = []
    for w in words:
        zh = word_trans.get(w)
        out.append(f"{w}（{zh}）" if zh else w)
    return out


def _make_findings(analysis: dict) -> list[dict]:
    """基于统计结果生成几条中文洞察 + 行动建议（模板化，后续可接 LLM）。"""
    neg_pct = analysis["sentiment_pct"]["negative"]
    pos_pct = analysis["sentiment_pct"]["positive"]
    word_trans = analysis.get("word_trans", {})
    neg_words = _fmt_words([w for w, _ in analysis["neg_words"][:10]], word_trans)
    pos_words = _fmt_words([w for w, _ in analysis["pos_words"][:10]], word_trans)

    items = []

    if neg_pct >= 30:
        items.append({
            "tag": "差评归因",
            "text": f"负面评论占比 {neg_pct:.1f}%，值得优先处理。负面评论反复出现的词是："
                    f"{'、'.join(neg_words) if neg_words else '（暂无集中主题）'}。",
        })
    else:
        items.append({
            "tag": "整体口碑",
            "text": f"负面评论占比 {neg_pct:.1f}%，整体口碑尚可。"
                    f"仍建议关注：{'、'.join(neg_words[:5]) if neg_words else '（暂无）'}。",
        })

    if pos_words:
        items.append({
            "tag": "好评亮点",
            "text": f"正面评论占比 {pos_pct:.1f}%，客户反复提到：{'、'.join(pos_words)}。"
                    f"这些是已得到验证的卖点，可强化到详情页和广告文案里。",
        })

    items.append({
        "tag": "行动建议",
        "text": "优先修复负面高频词对应的体验问题；把正面高频词提炼成卖点；"
                "对涉及物流、客服的差评单独归类，这两类通常占差评大头且可快速改善。",
    })
    return items


def _examples_html(analysis: dict) -> str:
    """生成代表性评论区块的 HTML（原文 + 中文翻译）。"""
    trans = analysis.get("example_trans", {})
    pos = analysis.get("pos_examples", [])
    neg = analysis.get("neg_examples", [])
    if not pos and not neg:
        return ""

    def _item(text: str, cls: str) -> str:
        zh = trans.get(text)
        html = f'<div class="example {cls}"><p class="orig">{text}</p>'
        if zh:
            html += f'<p class="trans">{zh}</p>'
        return html + "</div>"

    parts = ['<section><h2>代表性评论</h2>']
    if neg:
        parts.append('<h3 class="sub">负面示例（客户在骂什么）</h3>')
        parts.extend(_item(t, "neg") for t in neg)
    if pos:
        parts.append('<h3 class="sub">正面示例（客户在夸什么）</h3>')
        parts.extend(_item(t, "pos") for t in pos)
    parts.append("</section>")
    return "".join(parts)


def _extra_stats_html(analysis: dict) -> str:
    """混合数据：评论之外的其他数值字段描述统计表。"""
    stats = analysis.get("extra_stats") or {}
    if not stats:
        return ""
    cols = list(stats.keys())
    rows = [("最小值", "min"), ("最大值", "max"), ("均值", "mean"), ("中位数", "median")]
    table = '<table class="stats"><thead><tr><th>指标</th>'
    for c in cols:
        table += f"<th>{c}</th>"
    table += "</tr></thead><tbody>"
    for name, key in rows:
        table += f"<tr><td>{name}</td>"
        for c in cols:
            table += f"<td>{stats[c][key]}</td>"
        table += "</tr>"
    table += "</tbody></table>"
    return f'<section><h2>其他数据字段</h2>{table}</section>'


def build_report(
    analysis: dict,
    charts: dict,
    title: str = "跨境电商评论洞察报告",
    source: str | None = None,
    engine_name: str = "offline",
    findings: list[dict] | None = None,
) -> str:
    """生成完整 HTML 报告字符串。

    charts 键：pie / trend（可选）/ pos_words / neg_words / rating_dist（可选），
    值均为 ECharts option dict。findings 为 LLM 生成的结论建议，缺省走模板。
    """
    counts = analysis["sentiment_counts"]
    pct = analysis["sentiment_pct"]
    avg = analysis["avg_rating"]
    rating_max = analysis.get("rating_max")
    if avg is not None and rating_max:
        avg_text = f"{avg} / {rating_max}"
    else:
        avg_text = f"{avg}" if avg is not None else "—"
    total = analysis["total"]

    findings_html = "\n".join(
        f'<div class="finding"><span class="tag">{f["tag"]}</span>'
        f'<p>{f["text"]}</p></div>'
        for f in (findings or _make_findings(analysis))
    )

    examples_html = _examples_html(analysis)
    extra_html = _extra_stats_html(analysis)

    warning_html = ""
    if analysis.get("untranslated_count", 0) > 0:
        warning_html = (
            '<div class="warning">⚠️ 有 ' + str(analysis["untranslated_count"]) +
            ' 条评论因当前引擎无法处理其语言而未准确分析（离线引擎仅支持中英文）。'
            '建议用 --engine deepseek 获得全语言情感分析。</div>'
        )

    engine_cn = _ENGINE_NAMES.get(engine_name, engine_name)

    # ---- 组装图表的 div 和渲染脚本 ----
    def _script(chart_id: str, option: dict) -> str:
        return (
            f"echarts.init(document.getElementById('{chart_id}'))"
            f".setOption({json.dumps(option, ensure_ascii=False)});"
        )

    render_scripts = []
    if "pie" in charts:
        render_scripts.append(_script("chart-pie", charts["pie"]))

    rating_block = ""
    if "rating_dist" in charts:
        rating_block = (
            '<section><h2>评分分布</h2>'
            '<div id="chart-rating" class="chart" style="height:300px;"></div></section>'
        )
        render_scripts.append(_script("chart-rating", charts["rating_dist"]))

    trend_block = ""
    if analysis.get("trend") and "trend" in charts:
        trend_block = (
            '<section><h2>情感时间趋势</h2>'
            '<div id="chart-trend" class="chart" style="height:320px;"></div></section>'
        )
        render_scripts.append(_script("chart-trend", charts["trend"]))

    words_block = '<section><h2>高频词分析</h2><div class="charts-row">'
    if charts.get("pos_words"):
        words_block += '<div id="chart-pos" class="chart half" style="height:380px;"></div>'
        render_scripts.append(_script("chart-pos", charts["pos_words"]))
    if charts.get("neg_words"):
        words_block += '<div id="chart-neg" class="chart half" style="height:380px;"></div>'
        render_scripts.append(_script("chart-neg", charts["neg_words"]))
    words_block += "</div></section>"

    render_js = "\n".join(render_scripts)
    echarts_js = _load_echarts_js()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    background: #f4f5f7; color: #1f2937; line-height: 1.6; padding: 32px 16px;
  }}
  .page {{ max-width: 900px; margin: 0 auto; }}
  header {{ background: #ffffff; border-radius: 14px; padding: 28px 32px; margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  header h1 {{ font-size: 24px; margin-bottom: 8px; }}
  header .meta {{ color: #6b7280; font-size: 13px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
              gap: 14px; margin-bottom: 20px; }}
  .metric {{ background: #ffffff; border-radius: 12px; padding: 18px 20px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .metric .label {{ font-size: 13px; color: #6b7280; margin-bottom: 6px; }}
  .metric .value {{ font-size: 26px; font-weight: 600; }}
  .metric .value.neg {{ color: #d94b4b; }}
  .metric .value.green {{ color: #2e9e6b; }}
  section {{ background: #ffffff; border-radius: 14px; padding: 24px 28px; margin-bottom: 20px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  section h2 {{ font-size: 18px; margin-bottom: 16px; }}
  .chart {{ width: 100%; }}
  .charts-row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .charts-row .half {{ flex: 1 1 320px; min-width: 280px; }}
  .finding {{ border-left: 3px solid #e5e7eb; padding: 4px 0 4px 16px; margin-bottom: 16px; }}
  .finding:last-child {{ margin-bottom: 0; }}
  .tag {{ display: inline-block; background: #eef2ff; color: #4338ca; font-size: 12px;
          font-weight: 600; border-radius: 999px; padding: 2px 10px; margin-bottom: 6px; }}
  .finding p {{ font-size: 14.5px; }}
  .sub {{ font-size: 14px; color: #6b7280; margin: 12px 0 8px; }}
  .example {{ background: #f9fafb; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }}
  .example.neg {{ border-left: 3px solid #d94b4b; }}
  .example.pos {{ border-left: 3px solid #2e9e6b; }}
  .example .orig {{ font-size: 14px; }}
  .example .trans {{ font-size: 13px; color: #6b7280; margin-top: 4px; }}
  table.stats {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  table.stats th, table.stats td {{ padding: 10px 12px; text-align: right; border-bottom: 1px solid #eceef1; }}
  table.stats th {{ background: #f9fafb; color: #4b5563; font-weight: 600; }}
  table.stats td:first-child, table.stats th:first-child {{ text-align: left; color: #6b7280; }}
  .warning {{ background: #fff7ed; border: 1px solid #fdba74; color: #9a3412;
              border-radius: 10px; padding: 12px 16px; margin-bottom: 20px; font-size: 14px; }}
  footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="page">
  <header>
    <h1>{title}</h1>
    <div class="meta">
      {f"数据来源：{source} · " if source else ""}分析引擎：{engine_cn} · 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
  </header>

  <div class="metrics">
    <div class="metric"><div class="label">评论总数</div><div class="value">{total}</div></div>
    <div class="metric"><div class="label">平均评分</div><div class="value">{avg_text}</div></div>
    <div class="metric"><div class="label">时间跨度</div><div class="value" style="font-size:16px;padding-top:8px;">{_fmt_date_range(analysis["date_range"])}</div></div>
    <div class="metric"><div class="label">负面占比</div><div class="value neg">{pct["negative"]:.1f}%</div></div>
  </div>

  {warning_html}

  <section>
    <h2>情感分布</h2>
    <div id="chart-pie" class="chart" style="height:340px;"></div>
  </section>

  {rating_block}

  {trend_block}

  {words_block}

  {examples_html}

  {extra_html}

  <section>
    <h2>结论与建议</h2>
    {findings_html}
  </section>

  <footer>由 review_insights 自动生成</footer>
</div>

<script>{echarts_js}</script>
<script>
{render_js}
</script>
</body>
</html>"""
    return html
