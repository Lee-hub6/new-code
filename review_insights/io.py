"""数据读取：支持 CSV / Excel，自动识别评论文本、评分、日期三列。

客户导出的文件列名五花八门，这里维护一组常见别名做自动匹配。
匹配不到时也可以由用户在命令行手动指定列名。
"""
from __future__ import annotations

import os

import pandas as pd

# 常见列名别名（统一小写后匹配）
TEXT_ALIASES = [
    "content", "review", "reviewtext", "review_text", "text", "comment",
    "comments", "review_content", "reviewcontent", "body", "message",
    "评论", "评语", "内容", "评论内容", "评价",
]
RATING_ALIASES = [
    "score", "rating", "star", "stars", "rating_num", "star_rating",
    "star_ratings", "ratings", "评分", "星级", "打分",
]
DATE_ALIASES = [
    "at", "date", "time", "created", "created_at", "createdat",
    "review_date", "reviewdate", "review_time", "reviewtime", "datetime",
    "日期", "时间", "评论时间", "评论日期",
]


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """在 df 的列里找第一个命中别名的列名，找不到返回 None。"""
    lowered = {str(col).strip().lower(): col for col in df.columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def load_reviews(
    path: str,
    text_col: str | None = None,
    rating_col: str | None = None,
    date_col: str | None = None,
) -> pd.DataFrame:
    """读取评论文件，返回标准化后的 DataFrame。

    返回列固定为：text（文本）、rating（评分，可为空）、date（日期，可为空）。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件：{path}")

    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    # 去掉整列全空的无用列
    df = df.dropna(axis=1, how="all")

    text_col = text_col or _find_column(df, TEXT_ALIASES)
    if text_col is None:
        raise ValueError(
            f"无法自动识别评论文本列，请在命令行用 --text 指定。现有列：{list(df.columns)}"
        )

    result = pd.DataFrame({"text": df[text_col].fillna("").astype(str)})

    rating_col = rating_col or _find_column(df, RATING_ALIASES)
    if rating_col is not None:
        result["rating"] = pd.to_numeric(df[rating_col], errors="coerce")

    date_col = date_col or _find_column(df, DATE_ALIASES)
    if date_col is not None:
        # 去除英文日期里的序数词后缀（21st -> 21），否则 pd.to_datetime 解析不了
        cleaned = df[date_col].astype(str).str.replace(
            r"(\d+)(st|nd|rd|th)", r"\1", regex=True
        )
        result["date"] = pd.to_datetime(cleaned, errors="coerce")

    # 保留其他数值列（混合数据：评论 + 数值指标），供报告做描述统计
    for col in df.columns:
        if col in (text_col, rating_col, date_col):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            result[col] = df[col]

    # 去掉文本为空的行
    before = len(result)
    result = result[result["text"].str.strip().astype(bool)]
    dropped = before - len(result)
    if dropped:
        print(f"已忽略 {dropped} 条空评论")

    return result.reset_index(drop=True)
