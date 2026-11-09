"""文本清洗与分词。

这里刻意分成两个层次的清洗，用途不同：

1. light_clean —— 轻度清洗，只去掉 URL、@用户名、多余空白。
   保留表情符号和标点，因为 VADER 需要这些信号来判断情感。
   （原先作业里把 emoji 和标点全删了再喂给 VADER，其实是帮倒忙。）

2. tokenize_for_freq —— 给词频统计用的分词。
   小写、去标点、去停用词；中文用 jieba 分词，其余按空格分词。
"""
from __future__ import annotations

import re

import jieba
from nltk.corpus import stopwords

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)")
_USERNAME_RE = re.compile(r"@\w+")
_WHITESPACE_RE = re.compile(r"\s+")

# 英文停用词（首次调用时下载，若已存在则不重复下载）
try:
    _EN_STOPWORDS = set(stopwords.words("english"))
except LookupError:
    import nltk

    nltk.download("stopwords", quiet=True)
    _EN_STOPWORDS = set(stopwords.words("english"))


def light_clean(text: str) -> str:
    """轻度清洗：去 URL、@用户名、多余空白。保留 emoji 与标点。"""
    if not isinstance(text, str):
        return ""
    text = _URL_RE.sub(" ", text)
    text = _USERNAME_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def tokenize_for_freq(text: str, lang: str = "en") -> list[str]:
    """分词并去停用词，用于词频统计。

    lang 为 langdetect 返回的语言代码；中文（zh）走 jieba，其余按空格切。
    """
    text = light_clean(text).lower()
    if not text:
        return []

    if lang and lang.startswith("zh"):
        tokens = list(jieba.cut(text))
    else:
        # 去掉标点后按空格切分
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()

    # 中文词做长度过滤，避免单字噪声；英文去停用词
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in _EN_STOPWORDS:
            continue
        if lang and lang.startswith("zh") and len(t) < 2:
            continue
        result.append(t)
    return result
