"""数值数据分析：描述统计、时间趋势、分布，生成中文 HTML 报告。

与评论分析（情感/高频词）不同，数值分析面向纯数值数据（股票、销售、指标等）。
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from .config import llm_target
from .detect import date_column, numeric_columns
from .llm import chat_json
from .report import _load_echarts_js

_MAIN_COL_CANDIDATES = ["Close", "close", "Value", "value", "Sales", "sales", "Price", "price"]


def _pick_main_column(df: pd.DataFrame, num_cols: list[str]) -> str:
    for cand in _MAIN_COL_CANDIDATES:
        if cand in df.columns and cand in num_cols:
            return cand
    return num_cols[0]


def analyze_numeric(df: pd.DataFrame) -> dict:
    """对数值数据做描述统计 + 时间趋势 + 分布，返回结构化结果。"""
    num_cols = numeric_columns(df)
    date_col = date_column(df)
    main_col = _pick_main_column(df, num_cols)

    # 描述统计
    stats = {}
    for col in num_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        stats[col] = {
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "std": round(float(s.std()), 2),
        }

    # 时间趋势（数据点多就按月/周聚合）
    date_range = None
    trend = None
    if date_col is not None:
        d = pd.to_datetime(df[date_col], errors="coerce")
        date_range = (d.min(), d.max()) if d.notna().any() else None
        df2 = df.assign(_d=d).dropna(subset=["_d", main_col])
        n = len(df2)
        if n > 1000:
            df2 = df2.assign(_p=df2["_d"].dt.to_period("M"))
        elif n > 200:
            df2 = df2.assign(_p=df2["_d"].dt.to_period("W"))
        else:
            df2 = df2.assign(_p=df2["_d"].dt.date)
        g = df2.groupby("_p")[main_col].mean()
        trend = {
            "labels": [str(k) for k in g.index],
            "values": [round(float(v), 2) for v in g.values],
            "name": main_col,
        }

    # 分布直方图
    dist = None
    s = df[main_col].dropna()
    if len(s) > 1:
        bins = min(20, max(5, int(len(s) ** 0.5)))
        hist, edges = pd.cut(s, bins=bins, retbins=True)
        dist = {
            "labels": [f"{edges[i]:.2f}~{edges[i+1]:.2f}" for i in range(len(edges) - 1)],
            "values": [int(v) for v in pd.Series(hist).value_counts().sort_index().values],
        }

    return {
        "rows": len(df),
        "columns": num_cols,
        "main_col": main_col,
        "date_col": date_col,
        "date_range": date_range,
        "stats": stats,
        "trend": trend,
        "dist": dist,
    }


# ---------------- 图表 option ----------------

def trend_option(trend: dict) -> dict:
    return {
        "title": {"text": f"{trend['name']} 时间趋势", "left": "center", "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 60, "right": 20, "top": 50, "bottom": 55},
        "xAxis": {"type": "category", "data": trend["labels"], "axisLabel": {"rotate": 45}},
        "yAxis": {"type": "value", "scale": True},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "height": 18, "bottom": 8}],
        "series": [{
            "type": "line",
            "smooth": True,
            "data": trend["values"],
            "showSymbol": False,
            "itemStyle": {"color": "#0b6bcb"},
            "areaStyle": {"opacity": 0.08},
        }],
    }


def dist_option(dist: dict, main_col: str) -> dict:
    return {
        "title": {"text": f"{main_col} 分布", "left": "center", "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 60, "right": 20, "top": 50, "bottom": 55},
        "xAxis": {"type": "category", "data": dist["labels"], "axisLabel": {"rotate": 45, "fontSize": 10}},
        "yAxis": {"type": "value", "name": "频数"},
        "series": [{
            "type": "bar",
            "data": dist["values"],
            "itemStyle": {"color": "#0b6bcb", "borderRadius": [4, 4, 0, 0]},
        }],
    }


# ---------------- LLM 结论 ----------------

def generate_insights(analysis: dict, config) -> list[dict] | None:
    """用 LLM 生成数值数据的分析结论；无可用 key 或失败时返回 None。"""
    target = llm_target(config)
    if target is None:
        return None
    api_key, base_url, model = target

    main = analysis["main_col"]
    st = analysis["stats"].get(main, {})
    summary_parts = [
        f"共 {analysis['rows']} 行数据，主指标 {main}："
        f"均值 {st.get('mean')}、中位数 {st.get('median')}、最小 {st.get('min')}、最大 {st.get('max')}、标准差 {st.get('std')}",
    ]
    if analysis.get("date_range"):
        d0, d1 = analysis["date_range"]
        summary_parts.append(f"时间跨度 {d0.strftime('%Y-%m-%d')} 到 {d1.strftime('%Y-%m-%d')}")
    if analysis.get("trend"):
        t = analysis["trend"]
        summary_parts.append(f"趋势数据 {len(t['labels'])} 个点，从 {t['values'][0]} 到 {t['values'][-1]}")

    system = (
        '你是资深数据分析师。根据数据统计结果，用中文写简洁、有洞察的结论，'
        '包含：数据概览、明显趋势、值得注意的点（异常/波动）、一句话建议。'
        '只输出 JSON：{"insights":[{"tag":"概览","text":"..."},{"tag":"趋势","text":"..."},'
        '{"tag":"建议","text":"..."}]}。'
    )
    try:
        data = chat_json(api_key, base_url, model, system, "\n".join(summary_parts), temperature=0.3)
    except Exception:
        return None
    insights = (data or {}).get("insights", []) or []
    out = []
    for f in insights:
        if isinstance(f, dict) and f.get("tag") and f.get("text"):
            out.append({"tag": str(f["tag"]), "text": str(f["text"])})
    return out if out else None


# ---------------- 报告 ----------------

def _fmt_dr(dr) -> str:
    if dr is None:
        return "—"
    a, b = dr
    return f"{a.strftime('%Y-%m-%d')} ~ {b.strftime('%Y-%m-%d')}"


def build_numeric_report(
    analysis: dict,
    charts: dict,
    title: str = "数据分析报告",
    source: str | None = None,
    insights: list[dict] | None = None,
) -> str:
    st = analysis["stats"]
    main = analysis["main_col"]

    # 指标卡片
    latest = "—"
    if analysis.get("trend") and analysis["trend"]["values"]:
        latest = analysis["trend"]["values"][-1]
    mean_v = st.get(main, {}).get("mean", "—")

    # 描述统计表
    stat_rows = ["min", "max", "mean", "median", "std"]
    stat_cn = {"min": "最小值", "max": "最大值", "mean": "均值", "median": "中位数", "std": "标准差"}
    table_html = '<table class="stats"><thead><tr><th>指标</th>'
    for col in analysis["columns"]:
        if col in st:
            table_html += f"<th>{col}</th>"
    table_html += "</tr></thead><tbody>"
    for key in stat_rows:
        table_html += f"<tr><td>{stat_cn[key]}</td>"
        for col in analysis["columns"]:
            if col in st:
                table_html += f"<td>{st[col][key]}</td>"
        table_html += "</tr>"
    table_html += "</tbody></table>"

    # 图表渲染
    def _script(cid, opt):
        return f"echarts.init(document.getElementById('{cid}')).setOption({json.dumps(opt, ensure_ascii=False)});"

    render = []
    trend_block = ""
    if "trend" in charts:
        trend_block = '<section><h2>时间趋势</h2><div id="c-trend" class="chart" style="height:340px;"></div></section>'
        render.append(_script("c-trend", charts["trend"]))
    dist_block = ""
    if "dist" in charts:
        dist_block = '<section><h2>分布</h2><div id="c-dist" class="chart" style="height:300px;"></div></section>'
        render.append(_script("c-dist", charts["dist"]))

    insights_html = ""
    if insights:
        insights_html = "".join(
            f'<div class="finding"><span class="tag">{f["tag"]}</span><p>{f["text"]}</p></div>'
            for f in insights
        )
        insights_html = f"<section><h2>分析结论</h2>{insights_html}</section>"

    echarts_js = _load_echarts_js()
    render_js = "\n".join(render)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
          background: #f4f5f7; color: #1f2937; line-height: 1.6; padding: 32px 16px; }}
  .page {{ max-width: 900px; margin: 0 auto; }}
  header {{ background: #fff; border-radius: 14px; padding: 28px 32px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  header h1 {{ font-size: 24px; margin-bottom: 8px; }}
  header .meta {{ color: #6b7280; font-size: 13px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 20px; }}
  .metric {{ background: #fff; border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .metric .label {{ font-size: 13px; color: #6b7280; margin-bottom: 6px; }}
  .metric .value {{ font-size: 24px; font-weight: 600; }}
  section {{ background: #fff; border-radius: 14px; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  section h2 {{ font-size: 18px; margin-bottom: 16px; }}
  table.stats {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  table.stats th, table.stats td {{ padding: 10px 12px; text-align: right; border-bottom: 1px solid #eceef1; }}
  table.stats th {{ background: #f9fafb; color: #4b5563; font-weight: 600; }}
  table.stats td:first-child, table.stats th:first-child {{ text-align: left; color: #6b7280; }}
  .chart {{ width: 100%; }}
  .finding {{ border-left: 3px solid #e5e7eb; padding: 4px 0 4px 16px; margin-bottom: 16px; }}
  .finding:last-child {{ margin-bottom: 0; }}
  .tag {{ display: inline-block; background: #eef2ff; color: #4338ca; font-size: 12px; font-weight: 600;
          border-radius: 999px; padding: 2px 10px; margin-bottom: 6px; }}
  .finding p {{ font-size: 14.5px; }}
  footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="page">
  <header>
    <h1>{title}</h1>
    <div class="meta">
      {f"数据来源：{source} · " if source else ""}生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
  </header>

  <div class="metrics">
    <div class="metric"><div class="label">数据行数</div><div class="value">{analysis["rows"]}</div></div>
    <div class="metric"><div class="label">主指标 {main}</div><div class="value">{mean_v}</div></div>
    <div class="metric"><div class="label">最新值</div><div class="value">{latest}</div></div>
    <div class="metric"><div class="label">时间跨度</div><div class="value" style="font-size:14px;padding-top:8px;">{_fmt_dr(analysis["date_range"])}</div></div>
  </div>

  <section><h2>描述统计</h2>{table_html}</section>

  {trend_block}

  {dist_block}

  {insights_html}

  <footer>由 review_insights 自动生成</footer>
</div>
<script>{echarts_js}</script>
<script>{render_js}</script>
</body>
</html>"""
    return html
