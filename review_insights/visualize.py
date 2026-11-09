"""可视化：用 matplotlib 生成图表，返回 base64 编码的 PNG 字符串。

图表直接以 base64 内嵌进 HTML 报告，保证报告是单文件、离线可看。
中文字体按平台自动选择，避免中文标题变成方块。
"""
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # 无显示环境也能出图
import matplotlib.pyplot as plt
from matplotlib import font_manager

_SENTIMENT_CN = {"positive": "正面", "negative": "负面", "neutral": "中性"}
_SENTIMENT_COLOR = {"positive": "#2e9e6b", "negative": "#d94b4b", "neutral": "#9aa3ad"}


def _setup_chinese_font() -> str | None:
    candidates = [
        "PingFang SC", "Hiragino Sans GB", "Heiti SC", "Songti SC",  # macOS
        "Microsoft YaHei", "SimHei", "SimSun",  # Windows
        # Linux：优先简体中文；matplotlib 对 .ttc 只认第一个 face，
        # 有些环境只能拿到 "Noto Sans CJK JP"（同样含中文字形），作为兜底
        "Noto Sans CJK SC", "Noto Sans CJK JP",
        "WenQuanYi Zen Hei", "WenQuanYi Micro Hei",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    plt.rcParams["axes.unicode_minus"] = False
    return None


_setup_chinese_font()


def _fig_to_base64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def plot_sentiment_pie(counts: dict) -> str:
    labels, sizes, colors = [], [], []
    for s in ("positive", "negative", "neutral"):
        n = counts.get(s, 0)
        if n > 0:
            labels.append(f"{_SENTIMENT_CN[s]} {n} 条")
            sizes.append(n)
            colors.append(_SENTIMENT_COLOR[s])

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%",
           startangle=90, textprops={"fontsize": 11})
    ax.axis("equal")
    ax.set_title("情感分布", fontsize=15)
    return _fig_to_base64(fig)


def plot_trend(trend: dict) -> str:
    labels = trend["labels"]
    x = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(x, trend["positive"], marker="o", label="正面", color=_SENTIMENT_COLOR["positive"])
    ax.plot(x, trend["negative"], marker="o", label="负面", color=_SENTIMENT_COLOR["negative"])
    ax.plot(x, trend["neutral"], marker="o", label="中性", color=_SENTIMENT_COLOR["neutral"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("评论数")
    ax.set_title("评论情感时间趋势（按月）", fontsize=14)
    ax.legend()
    ax.grid(alpha=0.3)
    return _fig_to_base64(fig)


def _barh(ax, words: list[tuple[str, int]], title: str, color: str) -> None:
    if not words:
        ax.text(0.5, 0.5, "无数据", ha="center", va="center", fontsize=13)
        ax.set_title(title, fontsize=13)
        ax.axis("off")
        return
    w, c = zip(*words)
    y = list(range(len(w)))
    ax.barh(y, list(c), color=color)
    ax.set_yticks(y)
    ax.set_yticklabels(w, fontsize=10)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("出现次数")


def plot_top_words(pos_words: list[tuple[str, int]], neg_words: list[tuple[str, int]]) -> str:
    top_n = max(len(pos_words), len(neg_words), 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, max(4.5, top_n * 0.38)))
    _barh(ax1, pos_words, "正面高频词", _SENTIMENT_COLOR["positive"])
    _barh(ax2, neg_words, "负面高频词（差评归因）", _SENTIMENT_COLOR["negative"])
    fig.tight_layout()
    return _fig_to_base64(fig)
