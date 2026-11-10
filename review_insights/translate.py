"""翻译：把高频词和代表性评论翻译成中文，方便中国卖家直接看懂。

已经是中文的内容跳过。优先用已配置的 LLM（DeepSeek → Kimi → 小模型）
批量翻译，质量高；都没有配置时退回 deep-translator 免费翻译（可能失败）。
"""
from __future__ import annotations

import json
import re

from .config import Config, llm_target
from .llm import chat_json

_CJK_RE = re.compile(r"[一-鿿]")


def _translate_with_llm(items: list[str], config: Config, system: str,
                        preferred: str | None = None) -> dict[str, str]:
    """调用 LLM 批量翻译，返回 {原文: 中文}；失败返回空 dict。"""
    target = llm_target(config, preferred)
    if target is None or not items:
        return {}
    api_key, base_url, model = target

    try:
        data = chat_json(api_key, base_url, model, system, "\n".join(items))
    except Exception:
        return {}
    return {k: v for k, v in (data or {}).get("translations", {}).items()}


def translate_words(terms: list[tuple[str, int]], config: Config,
                    preferred: str | None = None) -> dict[str, str]:
    """把（词, 频次）列表翻译成中文，返回 {原词: 中文}。"""
    words = [w.strip() for w, _ in terms if w.strip() and not _CJK_RE.search(w)]
    if not words:
        return {}
    if llm_target(config, preferred) is None:
        return _via_free(words)
    return _translate_with_llm(
        words, config,
        '把下面每个词翻译成简体中文。只输出 JSON：'
        '{"translations":{"原词":"中文翻译"}}，每个词都要有对应翻译。',
        preferred,
    )


def translate_sentences(texts: list[str], config: Config,
                        preferred: str | None = None) -> dict[str, str]:
    """把一组句子（评论原文）翻译成中文，返回 {原文: 中文}。无可用 LLM 时返回空 dict。"""
    texts = [t.strip() for t in texts if t.strip()]
    if not texts or llm_target(config, preferred) is None:
        return {}
    return _translate_with_llm(
        texts, config,
        '把这些评论翻译成简体中文。只输出 JSON：'
        '{"translations":{"原文":"中文翻译"}}，每条都要有翻译。',
        preferred,
    )


def _via_free(words: list[str]) -> dict[str, str]:
    """免费兜底：deep-translator 逐词翻译（Google 接口，国内可能不可用）。"""
    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source="auto", target="zh-CN")
    except Exception:
        return {}
    result = {}
    for w in words:
        try:
            result[w] = translator.translate(w)
        except Exception:
            continue
    return result
