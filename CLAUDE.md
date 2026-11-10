# CLAUDE.md

这个文件告诉 AI 助手（Claude Code、Cowork 等）如何在当前仓库里工作。

## 项目是什么

`review_insights`：把一份评论数据（CSV/Excel）变成一份中文 HTML 洞察报告。面向跨境电商卖家，自动完成多语言翻译、情感分析、高频词统计与时间趋势可视化。

- 技术栈：Python 3.10+，pandas / matplotlib / nltk(VADER) / langdetect / deep-translator / jieba / openai(可选 DeepSeek)
- 运行环境：本地命令行（macOS / Windows 均可）
- 当前阶段：MVP，核心流水线已跑通，尚未接真实客户数据

## 怎么跑起来

```bash
# 安装依赖
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 跑样例
python -m review_insights.cli data/sample_reviews.csv -o output/report.html

# 跑测试
pytest
```

提交前请把上面两条命令（样例 + 测试）实际跑一遍再报告「完成」。

## 目录地图

| 路径 | 放什么 |
| --- | --- |
| `review_insights/` | 主包，模块职责见各文件 docstring |
| `tests/` | pytest 单元测试，与模块对应 |
| `data/` | 输入数据，**不进版本库**（`sample_reviews.csv` 例外，用于演示） |
| `output/` | 生成的 HTML 报告，**不进版本库** |

## 代码约定

- Python 用 snake_case，类名 PascalCase；模块 docstring 说明职责
- 每处新增注释用中文，解释「为什么」而不是「做了什么」
- 依赖要最小：不为了一个功能拉进大框架；新增依赖先说明理由
- 面向结果，不追求花哨抽象；改动聚焦在当前任务

## 关键设计（改动前先读）

- **多档引擎**：`sentiment.py` 里 `get_engine(config, engine)` 返回 `OfflineEngine`（SnowNLP 中文 + VADER 英文）、`SmallModelEngine`（硅基流动 Qwen）、`KimiEngine`（Moonshot）或 `DeepseekEngine` 之一；全部实现 `analyze(texts) -> DataFrame(sentiment/score/lang/untranslated)`。`LLMEngine` 是后三者的 OpenAI 兼容基类
- **清洗分两层**：`clean.py` 的 `light_clean`（给情感分析，保留 emoji 和标点）与 `tokenize_for_freq`（给词频，去停用词、中文走 jieba）。不要把 VADER 需要的标点删掉
- **报告单文件**：`report.py` 生成单文件 HTML，图表以 base64 内嵌，离线可看

## 测试要求

- 修 bug 先写能复现的测试再修
- 新增函数至少覆盖一条正常路径和一条边界情况
- 测试没跑通就不要说「已完成」，如实报告失败原因

## Git 约定

- 分支：`main` 随时可发布；功能走 `feat/简短描述`，修复走 `fix/简短描述`
- 提交信息：`feat:` / `fix:` / `refactor:` / `docs:` / `test:` / `chore:`
- **不要**未经确认执行 `git push --force`、`git reset --hard`、删除分支
- 提交前确认 `.env`、密钥、`data/` 下的真实数据没有进入暂存区

## 安全红线

- 绝不把密钥写进代码或提交；DeepSeek Key 走 `.env`（已在 `.gitignore`）
- 数据合规：只处理客户自己导出或公开可查的评论；不绕过平台反爬、不批量抓取倒卖
- 涉及删除、批量改文件的操作，执行前说明影响范围
