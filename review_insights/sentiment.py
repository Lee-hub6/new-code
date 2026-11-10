"""情感分析三档引擎。

统一接口：analyze(texts) -> DataFrame，列固定为
  - sentiment: positive / negative / neutral
  - score:     -1 ~ 1 的情感得分
  - lang:      检测到的语言代码
  - untranslated: 是否因无法处理而被标记（离线引擎对其他语言）

三档实现（借鉴微舆的分层思路，代码独立实现）：
  - OfflineEngine   离线：SnowNLP 处理中文、VADER 处理英文，零成本
  - SmallModelEngine 小模型：硅基流动 Qwen（OpenAI 兼容接口），便宜
  - DeepseekEngine  大模型：DeepSeek，最准
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod

import pandas as pd

from .clean import light_clean
from .config import Config
from .llm import chat_json


def _label(score: float) -> str:
    if score > 0.05:
        return "positive"
    if score < -0.05:
        return "negative"
    return "neutral"


def _neutral_row(lang: str | None = "unknown", untranslated: bool = False) -> dict:
    return {"sentiment": "neutral", "score": 0.0, "lang": lang, "untranslated": untranslated}


class SentimentEngine(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, texts: list[str]) -> pd.DataFrame:
        """输入评论文本列表，返回带 sentiment/score/lang/untranslated 四列的 DataFrame。"""


class OfflineEngine(SentimentEngine):
    """离线引擎：中文用 SnowNLP，英文用 VADER，其他语言标记为无法处理。"""

    name = "offline"

    def __init__(self) -> None:
        self._ensure_nltk()
        from nltk.sentiment.vader import SentimentIntensityAnalyzer

        self._vader = SentimentIntensityAnalyzer()
        self._snownlp = None  # 惰性导入，避免没装 snownlp 时也报错

    @staticmethod
    def _ensure_nltk() -> None:
        import nltk

        nltk.download("vader_lexicon", quiet=True)

    def _detect_lang(self, text: str) -> str:
        try:
            from langdetect import detect

            return detect(text)
        except Exception:
            return "en"

    def _snownlp_score(self, text: str) -> float:
        if self._snownlp is None:
            from snownlp import SnowNLP

            self._snownlp = SnowNLP
        sentiments = self._snownlp(text).sentiments  # 0~1，越大越正面
        return (sentiments - 0.5) * 2  # 映射到 -1~1

    def analyze(self, texts: list[str]) -> pd.DataFrame:
        rows = []
        for raw in texts:
            text = light_clean(raw)
            if not text:
                rows.append(_neutral_row())
                continue
            lang = self._detect_lang(text)
            if lang.startswith("zh"):
                score = self._snownlp_score(text)
                rows.append({"sentiment": _label(score), "score": round(score, 4), "lang": lang, "untranslated": False})
            elif lang == "en":
                score = self._vader.polarity_scores(text)["compound"]
                rows.append({"sentiment": _label(score), "score": round(score, 4), "lang": lang, "untranslated": False})
            else:
                # 离线引擎无法处理其他语言，如实标记
                rows.append(_neutral_row(lang=lang, untranslated=True))
        return pd.DataFrame(rows)


class LLMEngine(SentimentEngine):
    """OpenAI 兼容接口的 LLM 情感分析引擎基类。"""

    _SYSTEM = (
        '判断每条评论情感，只输出 JSON：'
        '{"results":[{"sentiment":"positive|negative|neutral","score":-1到1}]}，'
        'results 数量与评论数一致'
    )

    def __init__(self, api_key: str | None, base_url: str, model: str, batch_size: int) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._batch_size = max(1, batch_size)
        self._temperature = 0.0  # 部分模型（如 kimi-k3）只接受 1，由 llm.chat_json 自动切换

    def _analyze_batch(self, batch: list[str]) -> list[dict]:
        user = "\n".join(f"{i}. {t}" for i, t in enumerate(batch, 1))
        # 重试、限流退避、temperature 兼容、配置错误抛出，统一由 llm.chat_json 处理
        data = chat_json(
            None, "", self._model, self._SYSTEM, user,
            temperature=self._temperature, client=self._client,
        )
        results = (data or {}).get("results", []) or []

        out = []
        for i in range(len(batch)):
            if i < len(results) and isinstance(results[i], dict):
                sent = str(results[i].get("sentiment", "neutral")).lower()
                if sent not in ("positive", "negative", "neutral"):
                    sent = "neutral"
                try:
                    score = float(results[i].get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                out.append({"sentiment": sent, "score": round(score, 4), "lang": None, "untranslated": False})
            else:
                out.append(_neutral_row(lang=None))
        return out

    def analyze(self, texts: list[str]) -> pd.DataFrame:
        rows: list[dict] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            rows.extend(self._analyze_batch(batch))
        return pd.DataFrame(rows)


class DeepseekEngine(LLMEngine):
    """大模型引擎：DeepSeek。"""

    name = "deepseek"

    def __init__(self, config: Config) -> None:
        super().__init__(
            config.deepseek_api_key, config.deepseek_base_url,
            config.deepseek_model, config.batch_size,
        )


class KimiEngine(LLMEngine):
    """大模型引擎：Moonshot Kimi。"""

    name = "kimi"

    def __init__(self, config: Config) -> None:
        super().__init__(
            config.kimi_api_key, config.kimi_base_url,
            config.kimi_model, config.batch_size,
        )


class SmallModelEngine(LLMEngine):
    """小模型引擎：硅基流动 Qwen。"""

    name = "small"

    def __init__(self, config: Config) -> None:
        super().__init__(
            config.small_api_key, config.small_base_url,
            config.small_model, config.batch_size,
        )


def get_engine(config: Config, engine: str = "auto") -> SentimentEngine:
    """按指定档位（或自动）返回引擎。

    engine 可选 offline / small / deepseek / auto。
    指定了某个付费档但没配对应 key 时抛 ValueError。
    """
    if engine == "offline":
        return OfflineEngine()
    if engine == "small":
        if not config.small_api_key:
            raise ValueError("使用小模型引擎需要设置环境变量 SMALL_MODEL_API_KEY")
        return SmallModelEngine(config)
    if engine == "deepseek":
        if not config.deepseek_api_key:
            raise ValueError("使用 DeepSeek 引擎需要设置环境变量 DEEPSEEK_API_KEY")
        return DeepseekEngine(config)
    if engine == "kimi":
        if not config.kimi_api_key:
            raise ValueError("使用 Kimi 引擎需要设置环境变量 MOONSHOT_API_KEY")
        return KimiEngine(config)
    # auto：按已配置的 key 从高到低选
    if config.deepseek_api_key:
        return DeepseekEngine(config)
    if config.kimi_api_key:
        return KimiEngine(config)
    if config.small_api_key:
        return SmallModelEngine(config)
    return OfflineEngine()
