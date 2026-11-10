"""LLM 调用统一入口：封装重试、限流退避、temperature 兼容，供各模块复用。

三个调用方（情感分析、结论生成、翻译）都需要同样的健壮性处理：
  - 429 限流：指数退避重试（部分账号 RPM 很低，如 3 次/分钟）
  - 模型只接受特定 temperature（如 kimi-k3 只允许 1）：自动切换后重试
  - key 无效 / 模型不存在：属于配置错误，直接抛出，绝不静默降级
  - 返回非法 JSON：返回 None，由调用方决定如何降级
"""
from __future__ import annotations

import json
import time
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # openai 未安装时，仅离线档可用
    OpenAI = None  # type: ignore


def chat_json(
    api_key: str | None,
    base_url: str,
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_retries: int = 6,
    client: Any = None,
) -> dict | None:
    """调用 OpenAI 兼容接口并解析 JSON，返回 dict；解析失败返回 None。

    参数错误（key 无效、模型不存在、temperature 不支持且无法切换）会抛出异常。
    """
    from openai import AuthenticationError, BadRequestError, NotFoundError, RateLimitError

    if client is None:
        if OpenAI is None:
            raise RuntimeError("需要安装 openai 包才能使用大模型引擎：pip install openai")
        client = OpenAI(api_key=api_key, base_url=base_url)

    temp = temperature
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temp,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content)
        except (AuthenticationError, NotFoundError):
            raise  # 配置问题，立刻暴露
        except BadRequestError as e:
            if "temperature" in str(e) and temp != 1.0:
                temp = 1.0  # 该模型只接受 1，自动切换
                continue
            raise
        except RateLimitError as e:
            last_exc = e
            if attempt == max_retries - 1:
                raise
            # 低配账号 RPM 可能低到 3（每个请求需间隔约 20 秒），
            # 所以退避下限设 20 秒，避免连续重试继续撞限流
            time.sleep(max(20, 2 * (attempt + 1)))
        except json.JSONDecodeError:
            return None
        except Exception as e:
            last_exc = e
            if attempt == max_retries - 1:
                raise
            time.sleep(2)

    if last_exc:
        raise last_exc
    return None
