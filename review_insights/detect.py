"""数据类型自动识别。

读进一份数据后，自动判断它是「文本评论」还是「纯数值数据」，决定走哪条分析路径：
  - text：存在一列长文本（如评论/评价），走情感分析
  - numeric：主要列是数值（如价格/销量/指标），走数值分析
"""
from __future__ import annotations

import pandas as pd

_TEXT_LEN_THRESHOLD = 20  # 平均长度超过这个值，才认为是评论文本而不是类别/短字段


def find_text_column(df: pd.DataFrame) -> str | None:
    """找一列「像评论正文」的文本列；没有则返回 None。"""
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].dropna().astype(str)
            if len(s) > 0 and s.str.len().mean() >= _TEXT_LEN_THRESHOLD:
                return col
    return None


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """返回所有数值列（排除日期）。"""
    out = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            out.append(col)
    return out


def date_column(df: pd.DataFrame) -> str | None:
    """返回第一列能解析成日期的列；没有则返回 None。"""
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].dropna().astype(str)
            if len(s) > 0:
                d = pd.to_datetime(s, errors="coerce")
                if d.notna().mean() > 0.8:
                    return col
    return None


def detect_mode(df: pd.DataFrame) -> str:
    """返回 "text" 或 "numeric"。"""
    if find_text_column(df) is not None:
        return "text"
    if numeric_columns(df):
        return "numeric"
    return "text"  # 兜底走文本流程，报错信息更明确
