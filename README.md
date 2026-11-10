# review_insights · 跨境电商评论洞察工具

把一份评论数据（CSV / Excel）变成一份中文 HTML 洞察报告。面向跨境卖家：输入商品评论，自动完成多语言翻译、情感分析、高频词统计和时间趋势，输出可直接转发的单文件报告。

## 这个项目解决什么问题

跨境卖家（尤其是做东南亚市场的中国卖家）面对大量马来语、印尼语、中文、英文混杂的评论，很难快速搞清楚"客户到底在夸什么、骂什么"。这个工具把这些评论自动清洗、翻译、做情感分析，并生成一份带图表的中文报告，让不懂技术的卖家也能直接看懂差评归因和好评亮点。

## 快速开始

```bash
# 1. 安装依赖
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. 用样例数据跑一遍
python -m review_insights.cli data/sample_reviews.csv -o output/report.html

# 3. 换成真实数据（列名会自动识别，识别不到就手动指定）
python -m review_insights.cli 你的评论文件.csv --source "Lazada 竞品A" -o output/report.html
```

## 四档分析引擎

借鉴业界多模型分层的思路，按「成本 × 质量」分档，用 `--engine` 手动选，或 `auto` 自动：

| 档位 | `--engine` | 技术 | 成本 |
| --- | --- | --- | --- |
| 离线 | `offline` | SnowNLP（中文）+ VADER（英文） | 零，离线可用 |
| 小模型 | `small` | 硅基流动 Qwen | 极低 |
| Kimi | `kimi` | Moonshot Kimi | 低 |
| DeepSeek | `deepseek` | DeepSeek | 低 |

`auto` 按已配置的 key 自动从高到低选：deepseek → kimi → small → offline。

```bash
# 离线档（零配置，开箱即用）
python -m review_insights.cli data/sample_reviews.csv --engine offline

# 大模型档（需在 .env 配 DEEPSEEK_API_KEY）
python -m review_insights.cli data/sample_reviews.csv --engine deepseek

# 小模型档（需在 .env 配 SMALL_MODEL_API_KEY，注册 siliconflow.cn）
python -m review_insights.cli data/sample_reviews.csv --engine small
```

| 参数 | 说明 |
| --- | --- |
| `input` | 评论文件路径（CSV 或 Excel） |
| `--text` / `--rating` / `--date` | 手动指定列名（自动识别失败时用） |
| `-o, --output` | 输出 HTML 路径，默认 `output/report.html` |
| `--title` | 报告标题 |
| `--source` | 数据来源说明，显示在报告头部 |
| `--engine` | `auto` / `offline` / `small` / `deepseek` |
| `--top-n` | 高频词数量，默认 20 |

## 目录结构

```
.
├── review_insights/     # 主包
│   ├── cli.py           # 命令行入口
│   ├── config.py        # 配置加载（引擎选择）
│   ├── io.py            # 读取数据、列名自动映射
│   ├── clean.py         # 清洗与分词（中文走 jieba）
│   ├── sentiment.py     # 三档情感分析引擎
│   ├── analyze.py       # 聚合统计
│   ├── visualize.py     # matplotlib 图表（中文、base64）
│   └── report.py        # HTML 报告生成
├── tests/               # 单元测试
├── data/                # 输入数据（不进版本库，sample 除外）
└── output/              # 生成报告（不进版本库）
```

## 运行测试

```bash
pytest
```

## 约定

- 分支：`main` 随时可发布；功能走 `feat/xxx`，修复走 `fix/xxx`
- 提交信息：`feat: 新增功能`、`fix: 修复 bug`
- 数据合规红线：只处理客户自己导出、或公开可查的评论数据，不写程序绕过平台反爬、不批量抓取倒卖数据
