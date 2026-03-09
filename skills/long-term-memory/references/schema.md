# Long-Term Memory Database Schema

## Storage Location

```
~/.agents/long-term-memory/
├── memory.db          # SQLite database (WAL mode)
├── config.json        # Runtime configuration
├── .venv/             # Python virtual environment
├── scripts/           # Runtime copies of Python scripts
├── ltm                # Wrapper script
├── .setup_complete    # Setup marker
└── .profile           # Current profile name
```

## Tables

### memories (main table)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment ID |
| session_id | TEXT | Conversation session identifier |
| content | TEXT | Full memory text |
| summary | TEXT | Short summary (auto-generated if omitted) |
| category | TEXT | general/conversation/decision/fact/task/preference/solution |
| importance | INTEGER | 1-10, higher = more important |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |
| metadata | TEXT | Optional JSON for extensibility |

### memories_fts (FTS5 virtual table)

External-content FTS5 table synced with `memories` via triggers. Indexes `content`, `summary`, `category` for full-text search.

Query syntax: `WHERE memories_fts MATCH '"keyword1" OR "keyword2"'`

### memories_vec (sqlite-vec virtual table)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Matches memories.id |
| embedding | float[N] | N=512 (light) or 1024 (standard) |

Query syntax: `WHERE embedding MATCH <serialized_vector> AND k = <top_k>`

### db_config (metadata)

| Key | Value |
|-----|-------|
| embedding_dim | "512" or "1024" |
| model_name | "BAAI/bge-small-zh-v1.5" etc. |
| vec_enabled | "True" or "False" |

## Sync Triggers

Three triggers keep `memories_fts` in sync with `memories`:
- `memories_ai` — AFTER INSERT
- `memories_ad` — AFTER DELETE
- `memories_au` — AFTER UPDATE

## Concurrency

- WAL journal mode enabled (concurrent reads OK)
- `busy_timeout=5000` (5s wait on write lock)
- Multiple Claude Code sessions can safely read simultaneously
- Write conflicts are resolved by SQLite's internal locking

## CLI Interface

All scripts accept `--help` and output JSON to stdout. Progress/warnings go to stderr.

```bash
# Wrapper (recommended)
~/.agents/long-term-memory/ltm memory_query --query "..." --top-k 5
~/.agents/long-term-memory/ltm memory_write --content "..." --category decision
~/.agents/long-term-memory/ltm memory_status
~/.agents/long-term-memory/ltm memory_maintain --max-entries 5000

# Direct (equivalent)
~/.agents/long-term-memory/.venv/bin/python \
  ~/.agents/long-term-memory/scripts/memory_query.py --query "..."
```

## Profiles

| Profile | Model | Dim | Disk | RAM |
|---------|-------|-----|------|-----|
| light | bge-small-zh-v1.5 | 512 | ~300MB | ~200MB |
| standard | bge-m3 | 1024 | ~4GB | ~2GB |

Dimension is locked at setup time. Changing profile requires re-initialization (existing data is incompatible).
