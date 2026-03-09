#!/usr/bin/env python3
"""Write a memory entry to the database."""

import argparse
import json
import sqlite3
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, load_config

VALID_CATEGORIES = [
    "general", "conversation", "decision", "fact",
    "task", "preference", "solution",
]


def serialize_f32(vector):
    return struct.pack(f"{len(vector)}f", *vector)


def write_memory(content, category="general", importance=5,
                 session_id="", summary=None, metadata=None):
    if not os.path.exists(DB_PATH):
        print(json.dumps({"error": "Database not found. Run setup first."}))
        sys.exit(1)

    if category not in VALID_CATEGORIES:
        print(json.dumps({"error": f"Invalid category: {category}. Valid: {VALID_CATEGORIES}"}))
        sys.exit(1)

    importance = max(1, min(10, importance))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=5000")

    # Load sqlite-vec if available
    vec_enabled = False
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        vec_enabled = True
    except Exception:
        pass

    try:
        with conn:
            # Auto-generate summary if not provided
            auto_summary = summary or content[:200]

            # Insert into memories (FTS5 trigger handles fts table)
            cur = conn.execute(
                """
                INSERT INTO memories (session_id, content, summary, category, importance, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    session_id,
                    content,
                    auto_summary,
                    category,
                    importance,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                ],
            )
            memory_id = cur.lastrowid

            # Insert embedding into vec table
            vec_indexed = False
            if vec_enabled:
                try:
                    from embed import embed_text
                    embedding = embed_text(content)
                    conn.execute(
                        "INSERT INTO memories_vec (id, embedding) VALUES (?, ?)",
                        [memory_id, serialize_f32(embedding)],
                    )
                    vec_indexed = True
                except Exception as e:
                    print(json.dumps({
                        "warning": f"Embedding failed: {e}. Written to FTS5 only."
                    }), file=sys.stderr)

        print(json.dumps({
            "status": "ok",
            "id": memory_id,
            "vec_indexed": vec_indexed,
            "category": category,
            "importance": importance,
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write a memory entry")
    parser.add_argument("--content", "-c", default=None, help="Memory content text")
    parser.add_argument("--stdin", action="store_true", help="Read content from stdin (safer for special characters)")
    parser.add_argument("--category", default="general", choices=VALID_CATEGORIES)
    parser.add_argument("--importance", "-i", type=int, default=5, help="1-10")
    parser.add_argument("--session-id", "-s", default="", help="Session identifier")
    parser.add_argument("--summary", default=None, help="Short summary (auto-generated if omitted)")
    parser.add_argument("--metadata", default=None, help="JSON string of extra metadata")
    args = parser.parse_args()

    content = args.content
    if args.stdin or content is None:
        content = sys.stdin.read().strip()
    if not content:
        print(json.dumps({"error": "No content provided. Use --content or --stdin."}))
        sys.exit(1)

    meta = json.loads(args.metadata) if args.metadata else None
    write_memory(content, args.category, args.importance,
                 args.session_id, args.summary, meta)
