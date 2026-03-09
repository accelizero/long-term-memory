#!/usr/bin/env python3
"""Check memory database status and session history."""

import argparse
import json
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, SETUP_COMPLETE


def check_status(session_id=None):
    # Check setup
    if not os.path.exists(SETUP_COMPLETE):
        print(json.dumps({"status": "not_setup", "message": "Run setup first."}))
        return

    if not os.path.exists(DB_PATH):
        print(json.dumps({"status": "no_db", "message": "Database not found."}))
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=5000")

    result = {"status": "ok"}

    # Total memories
    result["total_memories"] = conn.execute(
        "SELECT COUNT(*) FROM memories"
    ).fetchone()[0]

    # Session-specific info
    if session_id:
        row = conn.execute(
            """
            SELECT COUNT(*), MAX(created_at), GROUP_CONCAT(DISTINCT category)
            FROM memories WHERE session_id = ?
            """,
            [session_id],
        ).fetchone()
        result["session"] = {
            "id": session_id,
            "entries": row[0],
            "last_write": row[1],
            "categories": row[2].split(",") if row[2] else [],
        }

    # Recent sessions
    sessions = conn.execute(
        """
        SELECT session_id, COUNT(*), MAX(created_at)
        FROM memories
        GROUP BY session_id
        ORDER BY MAX(created_at) DESC
        LIMIT 5
        """
    ).fetchall()
    result["recent_sessions"] = [
        {"session_id": s[0], "entries": s[1], "last_write": s[2]}
        for s in sessions
    ]

    # Category breakdown
    categories = conn.execute(
        """
        SELECT category, COUNT(*), AVG(importance)
        FROM memories GROUP BY category
        """
    ).fetchall()
    result["categories"] = {
        c[0]: {"count": c[1], "avg_importance": round(c[2], 1)}
        for c in categories
    }

    # DB file size
    result["db_size_mb"] = round(os.path.getsize(DB_PATH) / 1024 / 1024, 2)

    conn.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check memory status")
    parser.add_argument("--session-id", "-s", default=None)
    args = parser.parse_args()
    check_status(args.session_id)
