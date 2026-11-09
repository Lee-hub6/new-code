"""HTML 中文报告生成。

输入分析结果和图表（base64 PNG），输出一个单文件、离线可看的中文报告。
图表以 data URI 内嵌，方便直接转发给客户。
"""
from __future__ import annotations

from datetime import datetime


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


def build_report(
    analysis: dict,
    charts: dict,
    title: str = "跨境电商评论洞察报告",
    source: str | None = None,
    engine_name: str = "vader",
) -> str:
    """生成完整 HTML 报告字符串。charts 键：pie / trend / words。"""
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
        for f in _make_findings(analysis)
    )

    warning_html = ""
    if analysis.get("untranslated_count", 0) > 0:
        warning_html = (
            '<div class="warning">⚠️ 有 ' + str(analysis["untranslated_count"]) +
            ' 条非英文评论翻译失败（免费翻译接口限流），这部分评论已按原文粗略分析，'
            '情感判断可能不够准确。建议设置 DEEPSEEK_API_KEY 改用大模型引擎获得更准结果。</div>'
        )

    img = lambda b64, alt: (
        f'<figure class="chart"><img src="data:image/png;base64,{b64}" alt="{alt}"></figure>'
    )

    trend_block = ""
    if analysis["trend"] and "trend" in charts:
        trend_block = (
            '<section><h2>情感时间趋势</h2>'
            + img(charts["trend"], "情感时间趋势")
            + "</section>"
        )

    engine_cn = "DeepSeek" if engine_name == "deepseek" else "VADER（免费方案）"

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
  .chart {{ text-align: center; }}
  .chart img {{ max-width: 100%; height: auto; }}
  .finding {{ border-left: 3px solid #e5e7eb; padding: 4px 0 4px 16px; margin-bottom: 16px; }}
  .finding:last-child {{ margin-bottom: 0; }}
  .tag {{ display: inline-block; background: #eef2ff; color: #4338ca; font-size: 12px;
          font-weight: 600; border-radius: 999px; padding: 2px 10px; margin-bottom: 6px; }}
  .finding p {{ font-size: 14.5px; }}
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
    {img(charts["pie"], "情感分布")}
  </section>

  {trend_block}

  <section>
    <h2>高频词分析</h2>
    {img(charts["words"], "高频词")}
  </section>

  <section>
    <h2>结论与建议</h2>
    {findings_html}
  </section>

  <footer>由 review_insights 自动生成</footer>
</div>
</body>
</html>"""
    return html
