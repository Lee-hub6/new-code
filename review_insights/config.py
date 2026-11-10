"""配置加载：决定使用哪档情感分析引擎，以及相关参数。

所有配置都通过环境变量传入（.env 自动加载）。三档引擎：

  - offline（第一档）：SnowNLP 中文 + VADER 英文，零成本、离线可用，无需任何 key
  - small（第二档）：硅基流动 Qwen 小模型，便宜，多语言准确
  - deepseek（第三档）：DeepSeek 大模型，最准，多语言

自动档（auto）按已配置的 key 从高到低选择：deepseek → small → offline。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()  # 自动读取项目根目录的 .env 文件
except ImportError:
    pass  # 未安装 python-dotenv 时，依赖用户通过 export 设置环境变量


@dataclass
class Config:
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    kimi_api_key: str | None
    kimi_base_url: str
    kimi_model: str
    small_api_key: str | None
    small_base_url: str
    small_model: str
    batch_size: int

    @property
    def use_deepseek(self) -> bool:
        """兼容旧引用：是否配置了 DeepSeek key。"""
        return bool(self.deepseek_api_key)


def llm_target(config: Config, preferred: str | None = None):
    """选一个可用的 LLM 连接，返回 (api_key, base_url, model)；都没有则返回 None。

    preferred 指定优先使用的引擎（deepseek / kimi / small）；
    传 "offline" 表示不调用任何 LLM（保证零成本），此时返回 None。
    指定的引擎没配 key 时，退回按 deepseek → kimi → small 的优先级选。
    """
    if preferred == "offline":
        return None
    providers = {
        "deepseek": (config.deepseek_api_key, config.deepseek_base_url, config.deepseek_model),
        "kimi": (config.kimi_api_key, config.kimi_base_url, config.kimi_model),
        "small": (config.small_api_key, config.small_base_url, config.small_model),
    }
    order = [preferred] if preferred in providers else []
    order += [p for p in ("deepseek", "kimi", "small") if p != preferred]
    for name in order:
        api_key, base_url, model = providers[name]
        if api_key:
            return api_key, base_url, model
    return None


def load_config() -> Config:
    return Config(
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip() or None,
        deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        kimi_api_key=os.environ.get("MOONSHOT_API_KEY", "").strip() or None,
        kimi_base_url=os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
        kimi_model=os.environ.get("MOONSHOT_MODEL", "kimi-k2-0711-preview"),
        small_api_key=os.environ.get("SMALL_MODEL_API_KEY", "").strip() or None,
        small_base_url=os.environ.get("SMALL_MODEL_BASE_URL", "https://api.siliconflow.cn/v1"),
        small_model=os.environ.get("SMALL_MODEL_NAME", "Qwen/Qwen3-8B"),
        batch_size=int(os.environ.get("BATCH_SIZE", "20") or 20),
    )
