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
    small_api_key: str | None
    small_base_url: str
    small_model: str
    batch_size: int

    @property
    def use_deepseek(self) -> bool:
        """兼容旧引用：是否配置了 DeepSeek key。"""
        return bool(self.deepseek_api_key)


def load_config() -> Config:
    return Config(
        deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip() or None,
        deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        small_api_key=os.environ.get("SMALL_MODEL_API_KEY", "").strip() or None,
        small_base_url=os.environ.get("SMALL_MODEL_BASE_URL", "https://api.siliconflow.cn/v1"),
        small_model=os.environ.get("SMALL_MODEL_NAME", "Qwen/Qwen3-8B"),
        batch_size=int(os.environ.get("BATCH_SIZE", "20") or 20),
    )
