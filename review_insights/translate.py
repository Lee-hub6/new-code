"""高频词翻译：把分析得到的高频词翻译成中文，方便中国卖家直接看懂。

已经是中文的词跳过；DeepSeek 可用时用大模型批量翻译（质量高），
否则退回 deep-translator 免费翻译（可能失败）。翻译失败返回空 dict，
报告层会降级为只显示原文。
"""
from __future__ import annotations

import json
import re

from .config import Config

_CJK_RE = re.compile(r"[一-鿿]")


def translate_sentences(texts: list[str], config: Config) -> dict[str, str]:
    """把一组句子（评论原文）翻译成中文，返回 {原文: 中文}。无可用 LLM 时返回空 dict。"""
    texts = [t.strip() for t in texts if t.strip()]
    if not texts:
        return {}
    if config.deepseek_api_key:
        api_key, base_url, model = config.deepseek_api_key, config.deepseek_base_url, config.deepseek_model
    elif config.small_api_key:
        api_key, base_url, model = config.small_api_key, config.small_base_url, config.small_model
    else:
        return {}

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    user = "\n".join(texts)
    system = '把这些评论翻译成简体中文。只输出 JSON：{"translations":{"原文":"中文翻译"}}，每条都要有翻译。'
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return {k: v for k, v in data.get("translations", {}).items()}
    except Exception:
        return {}


def translate_words(terms: list[tuple[str, int]], config: Config) -> dict[str, str]:
    """把（词, 频次）列表翻译成中文，返回 {原词: 中文}。"""
    words = [w.strip() for w, _ in terms if w.strip() and not _CJK_RE.search(w)]
    if not words:
        return {}
    if config.use_deepseek:
        return _via_deepseek(words, config)
    return _via_free(words)


def _via_deepseek(words: list[str], config: Config) -> dict[str, str]:
    from openai import OpenAI

    client = OpenAI(api_key=config.deepseek_api_key, base_url=config.deepseek_base_url)
    user = "\n".join(words)
    try:
        resp = client.chat.completions.create(
            model=config.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "把下面每个词翻译成简体中文。只输出 JSON，格式："
                        '{"translations":{"原词":"中文翻译"}}，每个词都要有对应翻译。'
                    ),
                },
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return {k: v for k, v in data.get("translations", {}).items()}
    except Exception:
        return {}


def _via_free(words: list[str]) -> dict[str, str]:
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
