"""情感分析双引擎。

统一接口：analyze(texts) -> DataFrame，列固定为
  - sentiment: positive / negative / neutral
  - score:     -1 ~ 1 的情感得分
  - lang:      检测到的语言代码（DeepSeek 引擎下可能为 NaN）

两套实现：
  - VaderEngine    免费：langdetect 检测语言 -> 非英文用 deep-translator 翻成英文 -> VADER
  - DeepseekEngine 付费：OpenAI 兼容接口批量调用大模型，多语言直接分析，质量更高
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

import pandas as pd

from .clean import light_clean
from .config import Config


def _label(score: float) -> str:
    if score > 0.05:
        return "positive"
    if score < -0.05:
        return "negative"
    return "neutral"


class SentimentEngine(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, texts: list[str]) -> pd.DataFrame:
        """输入评论文本列表，返回带 sentiment/score/lang 三列的 DataFrame。"""


class VaderEngine(SentimentEngine):
    """免费方案：语言检测 + 翻译 + VADER。"""

    name = "vader"

    def __init__(self) -> None:
        self._ensure_nltk()
        from nltk.sentiment.vader import SentimentIntensityAnalyzer

        self._analyzer = SentimentIntensityAnalyzer()
        self._translator = None  # 惰性初始化，避免没装 deep-translator 时也报错

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

    def _translate(self, text: str) -> str:
        if self._translator is None:
            from deep_translator import GoogleTranslator

            self._translator = GoogleTranslator(source="auto", target="en")
        try:
            return self._translator.translate(text)
        except Exception:
            return None  # 翻译失败返回 None，由调用方降级并标记

    def analyze(self, texts: list[str]) -> pd.DataFrame:
        rows = []
        for raw in texts:
            text = light_clean(raw)
            if not text:
                rows.append({"sentiment": "neutral", "score": 0.0, "lang": "unknown", "untranslated": False})
                continue
            lang = self._detect_lang(text)
            untranslated = False
            if lang != "en":
                work = self._translate(text)
                if work is None:
                    work = text  # 翻译失败降级用原文，但标记为未翻译
                    untranslated = True
            else:
                work = text
            score = self._analyzer.polarity_scores(work)["compound"]
            rows.append({
                "sentiment": _label(score),
                "score": round(score, 4),
                "lang": lang,
                "untranslated": untranslated,
            })
        return pd.DataFrame(rows)


class DeepseekEngine(SentimentEngine):
    """付费方案：直接让大模型做多语言情感分析，马来语/印尼语/中文都更准。"""

    name = "deepseek"

    def __init__(self, config: Config) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=config.deepseek_api_key, base_url=config.deepseek_base_url)
        self._model = config.deepseek_model
        self._batch_size = max(1, config.batch_size)

    _SYSTEM = (
        "你是电商评论情感分析助手。用户会给你一批评论（可能是马来语、印尼语、"
        "中文或英文）。请判断每条评论的情感倾向。"
        "只输出 JSON，格式为：{\"results\":[{\"sentiment\":\"positive|negative|neutral\","
        "\"score\":-1到1之间的数字}]}，results 数量必须与输入评论数量一致。"
    )

    def _analyze_batch(self, batch: list[str]) -> list[dict]:
        from openai import AuthenticationError

        user = "\n".join(f"{i}. {t}" for i, t in enumerate(batch, 1))
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            data = json.loads(content)
            results = data.get("results", [])
        except AuthenticationError:
            # key 无效是致命错误，必须让用户看到，不能静默降级
            raise
        except Exception:
            # 网络抖动、JSON 解析失败等可容错错误，才降级为中性
            results = []

        # 容错：数量对不上或解析失败，用中性补齐
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
                out.append({"sentiment": "neutral", "score": 0.0, "lang": None, "untranslated": False})
        return out

    def analyze(self, texts: list[str]) -> pd.DataFrame:
        rows: list[dict] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            rows.extend(self._analyze_batch(batch))
        return pd.DataFrame(rows)


def get_engine(config: Config) -> SentimentEngine:
    """根据配置返回对应的情感分析引擎。"""
    if config.use_deepseek:
        return DeepseekEngine(config)
    return VaderEngine()
