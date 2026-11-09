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

try:
    import zhconv

    _HAS_ZHCONV = True
except ImportError:
    _HAS_ZHCONV = False

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

# 中文停用词（精简集合，覆盖高频虚词/代词/连词/介词/语气词）
# 借鉴 funNLP 中文停用词表的思路自行整理，避免直接搬运其文件
_ZH_STOPWORDS = {
    # 助词、语气词
    "的", "了", "着", "过", "吗", "呢", "吧", "啊", "哦", "嗯", "呀", "啦", "嘛",
    "之", "乎", "者", "也", "矣", "而已",
    # 代词
    "我", "你", "他", "她", "它", "我们", "你们", "他们", "她们", "自己", "大家",
    "这", "那", "这些", "那些", "这个", "那个", "这样", "那样",
    "什么", "怎么", "怎样", "如何", "为什么",
    # 副词
    "很", "太", "都", "就", "还", "也", "又", "再", "更", "最", "非常", "挺", "比较", "稍微",
    "已经", "正在", "曾经", "马上", "立刻", "一直", "总是", "经常", "有时", "有点",
    # 连词
    "和", "与", "或", "及", "而", "但", "但是", "因为", "所以", "如果", "虽然", "然而",
    "于是", "然后", "接着", "不过", "只是", "还是", "并且", "而且", "或者",
    # 介词
    "在", "于", "对", "从", "向", "把", "被", "让", "给", "为", "按", "按照", "通过", "关于", "对于",
    # 判断/存在/情态
    "是", "有", "没有", "不是", "就是", "可以", "可能", "应该", "需要", "能够", "会", "要", "去", "来", "能",
    # 数词、量词
    "一", "二", "两", "三", "四", "五", "个", "只", "条", "件", "次", "遍", "些", "点", "第", "每", "各", "此", "其",
}


def light_clean(text: str) -> str:
    """轻度清洗：去 URL、@用户名、繁体转简体、多余空白。保留 emoji 与标点。"""
    if not isinstance(text, str):
        return ""
    text = _URL_RE.sub(" ", text)
    text = _USERNAME_RE.sub(" ", text)
    text = _to_simplified(text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _to_simplified(text: str) -> str:
    """繁体转简体（zhconv）；未安装 zhconv 时原样返回。"""
    return zhconv.convert(text, "zh-cn") if _HAS_ZHCONV else text


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

    # 中文词做长度过滤 + 停用词过滤，避免单字和虚词噪声；英文去停用词
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in _EN_STOPWORDS:
            continue
        if lang and lang.startswith("zh"):
            if len(t) < 2:
                continue
            if t in _ZH_STOPWORDS:
                continue
        result.append(t)
    return result
