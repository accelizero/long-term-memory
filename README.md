# Long-Term Memory

一个为 AI Agent（Claude Code / OpenClaw）设计的持久化长期记忆系统。基于 SQLite + sqlite-vec + FTS5，支持向量语义搜索与全文关键词检索的混合查询，让 Agent 跨会话记住用户偏好、技术决策和项目上下文。

## 快速开始

### 前置要求

- Python 3.9+
- Git
- Claude Code 或 OpenClaw
- 磁盘空间：~300MB（light 模式）或 ~4GB（standard 模式）

### 第 1 步：克隆仓库

```bash
git clone https://github.com/accelizero/long-term-memory.git
cd long-term-memory
```

### 第 2 步：运行环境安装

```bash
# light 模式（推荐，300MB，适合大多数场景）
bash skills/long-term-memory/scripts/setup_env.sh light

# 或 standard 模式（4GB，更高精度的语义搜索）
bash skills/long-term-memory/scripts/setup_env.sh standard
```

安装过程需要 2-10 分钟（取决于网络），脚本会自动完成：

1. 在 `~/.agents/long-term-memory/.venv/` 创建 Python 虚拟环境
2. 安装依赖包（sqlite-vec、sentence-transformers 等）
3. 下载 BGE Embedding 模型到本地
4. 初始化 SQLite 数据库（`~/.agents/long-term-memory/memory.db`）
5. 生成 `ltm` 命令行包装器

看到 `{"status": "ok", ...}` 表示安装成功。

### 第 3 步：注册为全局 Skill

将 SKILL.md 复制到 Agent 的全局 skill 目录，让每个会话都能自动使用记忆功能。

**Claude Code：**

```bash
mkdir -p ~/.claude/skills/long-term-memory
cp skills/long-term-memory/SKILL.md ~/.claude/skills/long-term-memory/SKILL.md
```

**OpenClaw：**

```bash
mkdir -p ~/.openclaw/skills/long-term-memory
cp skills/long-term-memory/SKILL.md ~/.openclaw/skills/long-term-memory/SKILL.md
```

### 第 4 步：验证安装

在 Claude Code / OpenClaw 中开启新会话，Agent 会自动检测到 skill 并在后台使用记忆系统。你也可以手动验证：

```bash
# 检查安装状态
~/.agents/long-term-memory/ltm memory_status

# 写入一条测试记忆
~/.agents/long-term-memory/ltm memory_write \
  --stdin --category fact --importance 5 \
  --session-id "test" <<'CONTENT'
这是一条测试记忆，用于验证安装是否成功。
CONTENT

# 查询测试记忆
~/.agents/long-term-memory/ltm memory_query \
  --stdin --top-k 3 <<'QUERY'
测试记忆
QUERY
```

如果查询返回了刚才写入的记忆，说明一切正常。

## 架构

```
┌─────────────────────────────────────────────┐
│           Claude Code / OpenClaw            │
│    (读取 ~/.claude/skills/ 中的 SKILL.md     │
│     获得记忆操作指令，通过 Bash 调用脚本)      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│           ~/.agents/long-term-memory/        │
│                  ltm wrapper                 │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
 query      write      status    maintain
   │          │          │          │
   └──────────┴──────────┴──────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│              SQLite (WAL mode)               │
│  ┌────────────┬────────────┬───────────────┐ │
│  │  memories   │ memories_  │  memories_    │ │
│  │  (主表)     │ fts (FTS5) │  vec (向量)   │ │
│  └────────────┴────────────┴───────────────┘ │
│        ▲ 触发器自动同步 FTS5                   │
└──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│         BGE Embedding Model (本地)            │
│  light:  bge-small-zh-v1.5 (512d, ~300MB)   │
│  standard: bge-m3 (1024d, ~4GB)             │
└──────────────────────────────────────────────┘
```

### 核心设计思路

**混合检索（Hybrid Search）**
优先使用 FTS5 全文检索（< 100ms，零模型开销），当关键词匹配不足（结果 < 2 条）时自动回退到向量语义搜索，兼顾速度和召回率。

**本地优先**
Embedding 模型（BGE）运行在本地，数据存储在本地 SQLite，无需任何外部 API 调用，完全离线可用，数据不出本机。

**渐进式遗忘**
通过 importance 衰减（超过 N 天自动降低重要性）+ 相似记忆合并（余弦相似度 > 0.92 合并为一条）+ 低价值条目淘汰（超出容量上限时删除最不重要的），模拟人类记忆的自然遗忘机制，防止数据库无限膨胀。

**透明集成**
Agent 在后台自动查询和写入记忆，用户无感知。不会在对话中说"让我查一下记忆"或"已保存到记忆"，除非用户主动询问记忆系统。

## 使用方式

安装完成后，Agent 会根据 SKILL.md 中的指令自动操作记忆。你也可以在对话中直接触发：

- 说 **"记住..."** 或 **"remember..."** → Agent 写入一条高优先级记忆
- 说 **"上次我们讨论了什么？"** 或 **"previously..."** → Agent 查询相关记忆
- 新会话开始时 → Agent 自动检查状态，在你提出第一个实质问题时查询相关上下文

### 手动 CLI 用法

```bash
# 写入记忆
~/.agents/long-term-memory/ltm memory_write \
  --stdin --category decision --importance 8 \
  --session-id "20260309_140000" <<'CONTENT'
用户偏好使用 pytest 而非 unittest，测试文件放在 tests/ 目录下。
CONTENT

# 查询记忆
~/.agents/long-term-memory/ltm memory_query \
  --stdin --top-k 5 <<'QUERY'
测试框架偏好
QUERY

# 查看状态
~/.agents/long-term-memory/ltm memory_status

# 数据库维护（记忆条目 > 3000 或数据库 > 50MB 时运行）
~/.agents/long-term-memory/ltm memory_maintain \
  --max-entries 5000 --decay-days 30 --merge-threshold 0.92
```

**记忆分类（category）：**

| 分类 | 用途 | 典型 importance |
|------|------|----------------|
| `preference` | 用户偏好（工具、风格、习惯） | 8-9 |
| `decision` | 技术/架构决策 | 8 |
| `task` | 待办事项、后续任务 | 8 |
| `solution` | 已解决的问题和方案 | 7 |
| `fact` | 用户/项目的关键事实 | 6 |
| `conversation` | 对话摘要 | 5 |
| `general` | 其他 | 5 |

## 项目结构

```
long-term-memory/
├── README.md
├── agent.yaml                          # GitAgent 配置
├── SOUL.md
├── RULES.md
├── knowledge/                          # Agent 知识库
└── skills/
    └── long-term-memory/
        ├── SKILL.md                    # Skill 定义（复制到全局 skill 目录）
        ├── references/
        │   └── schema.md              # 数据库 Schema 文档
        └── scripts/
            ├── config.py              # 配置管理
            ├── db_init.py             # 数据库初始化（建表、索引、触发器）
            ├── embed.py               # Embedding 模块（BGE 模型封装）
            ├── memory_query.py        # 混合查询（FTS5 + 向量）
            ├── memory_write.py        # 写入记忆（自动同步 FTS5 和向量索引）
            ├── memory_status.py       # 状态查看
            ├── memory_maintain.py     # 维护（衰减 / 合并 / 淘汰）
            └── setup_env.sh           # 一键安装脚本
```

### 运行时数据（安装后自动生成）

```
~/.agents/long-term-memory/
├── memory.db              # SQLite 数据库（WAL 模式，支持并发读）
├── config.json            # 运行时配置（profile、模型、路径）
├── .venv/                 # Python 虚拟环境
├── scripts/               # 脚本运行时副本
├── ltm                    # CLI 包装器
├── .setup_complete        # 安装完成标记
└── .profile               # 当前 profile（light / standard）
```

## 卸载

```bash
# 删除运行时数据和数据库
rm -rf ~/.agents/long-term-memory

# 删除全局 skill（Claude Code）
rm -rf ~/.claude/skills/long-term-memory

# 删除全局 skill（OpenClaw）
rm -rf ~/.openclaw/skills/long-term-memory
```

## 常见问题

**Q: 安装脚本报错 "Python3 not found"**
A: 请先安装 Python 3.9+。Ubuntu/Debian: `sudo apt install python3 python3-venv`

**Q: 模型下载太慢**
A: 可以设置 HuggingFace 镜像：`export HF_ENDPOINT=https://hf-mirror.com`，然后重新运行安装脚本（先 `rm ~/.agents/long-term-memory/.setup_in_progress` 和 `rm -rf ~/.agents/long-term-memory/.venv`）。

**Q: 换 profile 怎么操作？**
A: 需要重新初始化：`rm -rf ~/.agents/long-term-memory`，然后重新运行 `setup_env.sh standard`。注意：已有记忆数据会丢失。

**Q: 多个 Agent 会话能同时使用吗？**
A: 可以。SQLite 使用 WAL 模式，支持并发读取。写入有锁保护（5 秒超时），多会话同时写入偶尔会短暂等待，但不会丢数据。

## 许可证

MIT
