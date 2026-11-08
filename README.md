# 项目名称

一句话说明这个项目是做什么的。（读完这句，别人就该知道要不要往下看）

## 这个项目解决什么问题

两三句话讲清楚背景：谁在用、解决什么痛点、为什么需要它。避免写成宣传语。

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Lee-hub6/new-code.git
cd new-code

# 2. 安装依赖（按实际技术栈替换）
#    Python:  python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
#    Node:    npm install
#    Go:      go mod download

# 3. 配置环境变量
cp .env.example .env   # 然后填入真实的值

# 4. 运行
#    ...
```

## 目录结构

```
.
├── src/            # 主要代码
├── tests/          # 测试
├── docs/           # 文档
├── scripts/        # 一次性脚本、工具脚本
├── CLAUDE.md       # 给 AI 助手的工作说明
└── README.md       # 你正在读的这个
```

按实际结构调整，保持和真实目录一致。

## 常用命令

| 做什么 | 命令 |
| --- | --- |
| 运行测试 | `...` |
| 格式化代码 | `...` |
| 静态检查 | `...` |
| 本地启动 | `...` |

## 约定

- 分支：`main` 保持随时可发布，功能开发走 `feat/xxx`，修复走 `fix/xxx`
- 提交信息：`feat: 新增登录`、`fix: 修复空指针`、`docs: 更新说明`
- 改动较大时先开 Issue 说明背景，再提 PR

## 许可

（如无特殊需要可删掉本节）
