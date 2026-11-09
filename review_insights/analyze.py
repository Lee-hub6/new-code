"""聚合统计：把带情感标签的评论数据汇总成报告需要的结构化结果。"""
from __future__ import annotations

from collections import Counter

import pandas as pd

from .clean import tokenize_for_freq

SENTIMENTS = ("positive", "negative", "neutral")


def _top_words(df: pd.DataFrame, sentiment: str, top_n: int) -> list[tuple[str, int]]:
    """某类情感评论的高频词（按出现次数降序）。"""
    sub = df[df["sentiment"] == sentiment]
    langs = sub["lang"] if "lang" in sub.columns else pd.Series([None] * len(sub))

    counter: Counter = Counter()
    for text, lang in zip(sub["text"], langs):
        counter.update(tokenize_for_freq(text, lang if isinstance(lang, str) else None))
    return counter.most_common(top_n)


def analyze(df: pd.DataFrame, top_n: int = 20) -> dict:
    """输入带 sentiment 标签的 DataFrame，输出报告用的结构化结果字典。"""
    total = len(df)

    # 情感分布
    vc = df["sentiment"].value_counts()
    counts = {s: int(vc.get(s, 0)) for s in SENTIMENTS}
    pct = {s: (counts[s] / total * 100 if total else 0.0) for s in SENTIMENTS}

    # 平均评分
    avg_rating = None
    if "rating" in df.columns and df["rating"].notna().any():
        avg_rating = round(float(df["rating"].dropna().mean()), 2)

    # 时间跨度与按月趋势
    date_range = None
    trend = None
    if "date" in df.columns and df["date"].notna().any():
        dated = df.dropna(subset=["date"]).copy()
        date_range = (dated["date"].min(), dated["date"].max())
        dated["month"] = dated["date"].dt.to_period("M")
        pivot = dated.pivot_table(
            index="month", columns="sentiment", values="text",
            aggfunc="count", fill_value=0,
        )
        for s in SENTIMENTS:
            if s not in pivot.columns:
                pivot[s] = 0
        pivot = pivot.sort_index()
        trend = {
            "labels": [str(m) for m in pivot.index],
            "positive": [int(x) for x in pivot["positive"]],
            "negative": [int(x) for x in pivot["negative"]],
            "neutral": [int(x) for x in pivot["neutral"]],
        }

    return {
        "total": total,
        "avg_rating": avg_rating,
        "date_range": date_range,
        "sentiment_counts": counts,
        "sentiment_pct": pct,
        "trend": trend,
        "pos_words": _top_words(df, "positive", top_n),
        "neg_words": _top_words(df, "negative", top_n),
        "untranslated_count": int(df["untranslated"].sum()) if "untranslated" in df.columns else 0,
    }
