---
name: review-insights
description: 分析电商评论数据并生成中文 HTML 洞察报告。当用户要求分析评论/评价数据、做差评归因、提炼好评卖点、对比竞品口碑、或提到 review_insights 项目时使用。
---

# 评论洞察分析

把一份评论数据（CSV / Excel）变成一份可直接交付客户的中文 HTML 洞察报告。

## 项目位置

代码是 `review_insights` 包，仓库根目录默认在 `/Volumes/Extreme Pro/new code/new-code`。开始前确认三件事：

```bash
cd "<仓库根目录>"
ls review_insights/ requirements.txt   # 确认是项目根目录
ls .venv/bin/python                    # 确认虚拟环境存在
```

没有 `.venv` 就先建：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

## 标准流程

### 1. 看清数据

先读文件头几行，确认哪一列是评论正文，有没有评分列和日期列：

```bash
head -3 "<数据文件>"
```

列名对不上是常态——程序会自动识别常见别名（content/review/comment/评论 等），识别不到就要手动指定。**不要在没看数据的情况下猜测列名。**

### 2. 选引擎

| 数据情况 | 用哪个 |
| --- | --- |
| 只有中英文，想零成本 | `--engine offline` |
| 有马来语/印尼语/泰语等，量不大 | `--engine deepseek` |
| 想省钱、能接受慢 | `--engine small`（硅基流动 Qwen） |
| 用户明确要求用 Kimi | `--engine kimi`（注意下方限流说明） |

不确定就用 `--engine deepseek`，准确率最高。

**Kimi 特别提醒**：若账号 RPM 只有 3，每个请求要间隔约 20 秒，12 条评论约需 2 分钟，大批量不可行。数据超过 50 条时改用 deepseek。

### 3. 跑分析

```bash
.venv/bin/python -m review_insights.cli "<数据文件>" \
  --text "<评论文本列名>" --rating "<评分列名>" --date "<日期列名>" \
  --engine deepseek --source "<品牌或商品名>" \
  -o "output/<报告名>.html"
```

`--text/--rating/--date` 只在自动识别失败时才需要。`--source` 会显示在报告头部，是给客户看的，别省略。

### 4. 检查结果

报告生成后必须核对，再交给用户：

```bash
ls -la output/            # 文件是否生成、大小是否合理（约 1MB，含 ECharts）
```

然后检查报告内容：

- **负面占比是否为 0%**——若是，几乎肯定是 LLM 调用失败被静默降级了，见下方排查。
- **黄色警告条**——若提示「N 条评论因当前引擎无法处理其语言」，说明用了 offline 档但数据含其他语言，换 deepseek 重跑。
- **结论是否为模板文字**（如「优先修复负面高频词对应的体验问题」）——说明 LLM 结论生成失败，终端会打印提示。

### 5. 交付

`.html` 是单文件、离线可看、图表可交互，直接用 `computer://` 链接给用户。文件名带品牌和日期，例如 `output/airasia_2025-11.html`。

## 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 报告负面占比 0% | LLM 调用失败被降级 | 单独跑一次引擎看报错 |
| `401 Authentication Fails` | key 无效 | 让用户在 `.env` 里换 key，不要自己猜 |
| `404 Not found the model` | 账号没有该模型 | 查可用模型 `GET {base_url}/models`，再设 `MOONSHOT_MODEL` / `DEEPSEEK_MODEL` |
| `invalid temperature: only 1 is allowed` | 该模型只接受 temperature=1 | 代码已自动切换 |
| `429 RateLimitError` | 限流 | 代码已自动退避重试；仍失败就减小批量或换 deepseek |
| 日期解析全是 NaT | 日期带 `21st`/`22nd` 序数词 | 代码已处理；仍失败用 `--date` 换一列 |
| CSV 列错位 | 字段里有逗号但没加引号 | 让用户重新导出，或先清洗 |

## 边界

- 只处理客户自己导出的、或公开可查的评论数据。**不写爬虫绕平台反爬、不批量抓取倒卖数据。**
- 报告里的原话示例可能含用户昵称，交付前确认没有敏感个人信息。
- `.env` 里含密钥，不要读取、打印或提交到 git。
