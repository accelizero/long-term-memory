# Long-Term Memory

一个为 AI Agent（如 Claude Code）设计的持久化长期记忆系统。基于 SQLite + sqlite-vec + FTS5，支持向量语义搜索与全文关键词检索的混合查询，让 Agent 跨会话记住用户偏好、技术决策和项目上下文。

## 架构

```
┌─────────────────────────────────────────────┐
│              Claude Code / Agent            │
│         (通过 Bash 调用 CLI 脚本)            │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│                  ltm wrapper                 │
│         ~/.agents/long-term-memory/ltm       │
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

1. **混合检索（Hybrid Search）**：优先使用 FTS5 全文检索（快速、零开销），当关键词匹配不足时自动回退到向量语义搜索，兼顾速度和召回率。

2. **本地优先**：Embedding 模型运行在本地（sentence-transformers / FlagEmbedding），数据存储在本地 SQLite，无需外部 API，完全离线可用。

3. **渐进式遗忘**：通过 importance 衰减 + 相似记忆合并 + 低价值条目淘汰，模拟人类记忆的自然遗忘机制，防止数据库无限膨胀。

4. **透明集成**：对用户完全透明——Agent 自动查询和写入记忆，不会在对话中暴露记忆系统的存在。

## 安装

### 前置要求

- Python 3.9+
- ~300MB 磁盘空间（light 模式）或 ~4GB（standard 模式）

### 快速安装

```bash
# 克隆仓库
git clone git@github.com:accelizero/long-term-memory.git
cd long-term-memory

# 运行安装脚本（默认 light 模式，适合大多数场景）
bash skills/long-term-memory/scripts/setup_env.sh light

# 或使用 standard 模式（更高精度，需要更多资源）
bash skills/long-term-memory/scripts/setup_env.sh standard
```

安装脚本会自动完成：
- 创建 Python 虚拟环境 (`~/.agents/long-term-memory/.venv/`)
- 安装依赖（sqlite-vec、sentence-transformers 等）
- 下载 BGE Embedding 模型
- 初始化 SQLite 数据库
- 生成 `ltm` 命令行包装器

### 作为 GitAgent Skill 使用

如果你使用 [gitagent](https://github.com/anthropics/gitagent) 框架，将本仓库的 `skills/long-term-memory/` 目录复制到你的 agent 的 `skills/` 下，并在 `agent.yaml` 中注册：

```yaml
skills:
  - long-term-memory
```

## 使用

### 写入记忆

```bash
~/.agents/long-term-memory/ltm memory_write \
  --stdin --category decision --importance 8 \
  --session-id "20260309_140000" <<'CONTENT'
用户偏好使用 pytest 而非 unittest，测试文件放在 tests/ 目录下。
CONTENT
```

支持的 category：`general`、`conversation`、`decision`、`fact`、`task`、`preference`、`solution`

importance 范围：1-10（越高越重要，越不容易被自动清理）

### 查询记忆

```bash
~/.agents/long-term-memory/ltm memory_query \
  --stdin --top-k 5 <<'QUERY'
用户的测试框架偏好是什么？
QUERY
```

查询模式：
- `hybrid`（默认）— FTS5 优先，不足时回退向量搜索
- `fts` — 仅关键词搜索（最快）
- `vec` — 仅向量语义搜索（最准）

### 查看状态

```bash
~/.agents/long-term-memory/ltm memory_status
```

输出记忆总数、分类统计、最近会话、数据库大小等信息。

### 数据库维护

```bash
~/.agents/long-term-memory/ltm memory_maintain \
  --max-entries 5000 \
  --decay-days 30 \
  --merge-threshold 0.92
```

维护操作：
- **重要性衰减**：超过 30 天的记忆 importance 自动 -1
- **相似合并**：余弦相似度 > 0.92 的记忆自动合并（保留更重要的）
- **容量淘汰**：超过上限时删除最不重要的条目

## 项目结构

```
long-term-memory/
├── agent.yaml                          # GitAgent 配置
├── README.md
├── SOUL.md
├── RULES.md
├── knowledge/                          # Agent 知识库
└── skills/
    └── long-term-memory/
        ├── SKILL.md                    # Skill 定义与 Agent 使用说明
        ├── references/
        │   └── schema.md              # 数据库 Schema 文档
        └── scripts/
            ├── config.py              # 配置管理
            ├── db_init.py             # 数据库初始化
            ├── embed.py               # Embedding 模块（BGE）
            ├── memory_query.py        # 混合查询（FTS5 + Vec）
            ├── memory_write.py        # 写入记忆
            ├── memory_status.py       # 状态查看
            ├── memory_maintain.py     # 维护（衰减/合并/淘汰）
            └── setup_env.sh           # 一键安装脚本
```

## 运行时数据

安装后在 `~/.agents/long-term-memory/` 生成：

```
~/.agents/long-term-memory/
├── memory.db              # SQLite 数据库（WAL 模式）
├── config.json            # 运行时配置
├── .venv/                 # Python 虚拟环境
├── scripts/               # 脚本运行时副本
├── ltm                    # CLI 包装器
├── .setup_complete        # 安装完成标记
└── .profile               # 当前 profile（light/standard）
```

## 许可证

MIT
