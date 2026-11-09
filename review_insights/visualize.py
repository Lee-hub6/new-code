"""可视化：生成 ECharts 图表的 option 配置（dict）。

从 matplotlib 静态 PNG 升级为 ECharts 交互式图表（可悬停看数据、缩放）。
option 以 dict 形式返回，由 report.py 序列化为 JSON 嵌入 HTML。
中文字体由浏览器负责渲染，不再有 matplotlib 的字体问题。
"""
from __future__ import annotations

_SENTIMENT_CN = {"positive": "正面", "negative": "负面", "neutral": "中性"}
_SENTIMENT_COLOR = {"positive": "#2e9e6b", "negative": "#d94b4b", "neutral": "#9aa3ad"}


def sentiment_pie_option(counts: dict) -> dict:
    """情感分布饼图。"""
    data = []
    for s in ("positive", "negative", "neutral"):
        n = counts.get(s, 0)
        if n > 0:
            data.append({
                "name": _SENTIMENT_CN[s],
                "value": n,
                "itemStyle": {"color": _SENTIMENT_COLOR[s]},
            })
    return {
        "title": {"text": "情感分布", "left": "center", "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} 条 ({d}%)"},
        "legend": {"bottom": 0},
        "series": [{
            "type": "pie",
            "radius": ["35%", "62%"],
            "data": data,
            "label": {"formatter": "{b}\n{c} 条 ({d}%)"},
        }],
    }


def trend_line_option(trend: dict) -> dict:
    """情感时间趋势折线图。"""
    return {
        "title": {"text": "评论情感时间趋势（按月）", "left": "center", "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0, "data": ["正面", "负面", "中性"]},
        "grid": {"left": 45, "right": 20, "top": 50, "bottom": 55},
        "xAxis": {"type": "category", "data": trend["labels"], "axisLabel": {"rotate": 45}},
        "yAxis": {"type": "value", "name": "评论数"},
        "series": [
            {"name": "正面", "type": "line", "smooth": True, "data": trend["positive"],
             "itemStyle": {"color": _SENTIMENT_COLOR["positive"]}},
            {"name": "负面", "type": "line", "smooth": True, "data": trend["negative"],
             "itemStyle": {"color": _SENTIMENT_COLOR["negative"]}},
            {"name": "中性", "type": "line", "smooth": True, "data": trend["neutral"],
             "itemStyle": {"color": _SENTIMENT_COLOR["neutral"]}},
        ],
    }


def top_words_option(words: list[tuple[str, int]], title: str, color: str) -> dict | None:
    """单个横向条形图（高频词），words 为 [(词, 频次)]，按频次降序。"""
    if not words:
        return None
    labels = [w for w, _ in words]
    values = [c for _, c in words]
    # 反转，让频次最高的显示在最上方
    labels = labels[::-1]
    values = values[::-1]
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 100, "right": 30, "top": 45, "bottom": 25},
        "xAxis": {"type": "value", "name": "出现次数"},
        "yAxis": {"type": "category", "data": labels, "axisLabel": {"fontSize": 11}},
        "series": [{
            "type": "bar",
            "data": values,
            "itemStyle": {"color": color, "borderRadius": [0, 4, 4, 0]},
            "barMaxWidth": 18,
        }],
    }


def rating_dist_option(rating_dist: dict) -> dict:
    """评分分布柱状图。"""
    return {
        "title": {"text": "评分分布", "left": "center", "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 45, "right": 20, "top": 50, "bottom": 35},
        "xAxis": {"type": "category", "data": rating_dist["labels"], "name": "评分"},
        "yAxis": {"type": "value", "name": "评论数"},
        "series": [{
            "type": "bar",
            "data": rating_dist["values"],
            "itemStyle": {"color": "#5b8ff9", "borderRadius": [4, 4, 0, 0]},
            "barMaxWidth": 40,
        }],
    }
