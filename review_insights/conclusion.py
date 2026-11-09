"""结论生成：用 LLM 根据分析结果生成详细、可落地的中文结论与建议。

优先用 DeepSeek（质量高、快），否则用硅基流动小模型；两者都没配 key 时返回 None，
由报告层降级为模板文字。
"""
from __future__ import annotations

import json

from .config import Config


def _build_summary(analysis: dict) -> str:
    """把分析结果转成一段文字摘要，供 LLM 生成结论。"""
    pct = analysis["sentiment_pct"]
    neg_words = [w for w, _ in analysis["neg_words"][:15]]
    pos_words = [w for w, _ in analysis["pos_words"][:15]]
    avg = analysis["avg_rating"]
    rating_max = analysis.get("rating_max")

    parts = [
        f"共 {analysis['total']} 条评论",
        f"情感分布：正面 {pct['positive']:.1f}%、负面 {pct['negative']:.1f}%、中性 {pct['neutral']:.1f}%",
    ]
    if avg is not None:
        parts.append(f"平均评分 {avg}（满分 {rating_max or 5}）")
    if neg_words:
        parts.append("负面高频词：" + "、".join(neg_words))
    if pos_words:
        parts.append("正面高频词：" + "、".join(pos_words))
    if analysis.get("trend"):
        labels = analysis["trend"]["labels"]
        if labels:
            parts.append(f"时间跨度 {labels[0]} 到 {labels[-1]}，共 {len(labels)} 个月")
    return "\n".join(parts)


def generate_findings(analysis: dict, config: Config) -> list[dict] | None:
    """用 LLM 生成详细结论建议，返回 [{tag, text}]；无可用 key 或失败时返回 None。"""
    if config.deepseek_api_key:
        api_key, base_url, model = config.deepseek_api_key, config.deepseek_base_url, config.deepseek_model
    elif config.small_api_key:
        api_key, base_url, model = config.small_api_key, config.small_base_url, config.small_model
    else:
        return None

    summary = _build_summary(analysis)
    system = (
        '你是一名资深电商数据分析师。根据评论分析数据，用中文写详细、专业、可落地的结论与建议。'
        '只输出 JSON：{"findings":[{"tag":"整体口碑","text":"..."},{"tag":"差评归因","text":"..."},'
        '{"tag":"好评亮点","text":"..."},{"tag":"行动建议","text":"..."}]}。'
        '每条 text 要具体、有数据支撑，行动建议可执行，不要空话套话。'
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": summary},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        findings = data.get("findings", [])
        out = []
        for f in findings:
            if isinstance(f, dict) and f.get("tag") and f.get("text"):
                out.append({"tag": str(f["tag"]), "text": str(f["text"])})
        return out if out else None
    except Exception:
        return None
