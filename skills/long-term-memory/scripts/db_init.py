#!/usr/bin/env python3
"""Initialize the long-term memory database."""

import sqlite3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, BASE_DIR, load_config


def init_db():
    config = load_config()
    if not config:
        print(json.dumps({"error": "No config found. Run setup first."}))
        sys.exit(1)

    dim = config.get("embedding_dim", 512)
    model_name = config.get("model_name", "")

    os.makedirs(BASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # WAL mode for concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    # Main memories table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            category TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)

    # FTS5 full-text search (external content mode, synced via triggers)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            summary,
            category,
            content=memories,
            content_rowid=id
        )
    """)

    # Triggers to keep FTS5 in sync with memories table
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, summary, category)
            VALUES (new.id, new.content, new.summary, new.category);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, summary, category)
            VALUES ('delete', old.id, old.content, old.summary, old.category);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, summary, category)
            VALUES ('delete', old.id, old.content, old.summary, old.category);
            INSERT INTO memories_fts(rowid, content, summary, category)
            VALUES (new.id, new.content, new.summary, new.category);
        END;
    """)

    # sqlite-vec virtual table (optional)
    vec_enabled = False
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
                id INTEGER PRIMARY KEY,
                embedding float[{dim}] distance_metric=cosine
            )
        """)
        vec_enabled = True
    except Exception as e:
        print(json.dumps({
            "warning": f"sqlite-vec not available: {e}. FTS5-only mode."
        }), file=sys.stderr)

    # Indexes for common queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)
    """)

    # Config table (stores schema metadata)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS db_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO db_config (key, value) VALUES ('embedding_dim', ?)",
        [str(dim)],
    )
    conn.execute(
        "INSERT OR REPLACE INTO db_config (key, value) VALUES ('model_name', ?)",
        [model_name],
    )
    conn.execute(
        "INSERT OR REPLACE INTO db_config (key, value) VALUES ('vec_enabled', ?)",
        [str(vec_enabled)],
    )

    conn.commit()
    conn.close()

    print(json.dumps({
        "status": "ok",
        "db_path": DB_PATH,
        "vec_enabled": vec_enabled,
        "embedding_dim": dim,
    }))


if __name__ == "__main__":
    init_db()
