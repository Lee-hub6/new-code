"""review_insights —— 跨境电商评论洞察工具。

输入一份评论数据（CSV/Excel），输出一份中文 HTML 分析报告。
支持两套情感分析引擎：
  - 免费方案：langdetect 检测语言 -> deep-translator 翻译成英文 -> NLTK VADER 情感分析
  - DeepSeek：设置 DEEPSEEK_API_KEY 后自动切换，直接调用大模型做多语言情感分析
"""

__version__ = "0.1.0"
