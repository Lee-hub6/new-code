"""配置加载：决定使用哪套情感分析引擎，以及相关参数。

所有配置都通过环境变量传入，不写死在代码里：
  - DEEPSEEK_API_KEY   设置了就走 DeepSeek 引擎，不设置走免费方案
  - DEEPSEEK_BASE_URL  默认 https://api.deepseek.com
  - DEEPSEEK_MODEL     默认 deepseek-chat
  - BATCH_SIZE         DeepSeek 每批处理的评论条数，默认 20
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
    use_deepseek: bool
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    batch_size: int


def load_config() -> Config:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    return Config(
        use_deepseek=bool(key),
        deepseek_api_key=key or None,
        deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        batch_size=int(os.environ.get("BATCH_SIZE", "20") or 20),
    )
