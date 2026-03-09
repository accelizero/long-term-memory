#!/usr/bin/env python3
"""Maintain the memory database: decay importance, merge similar, prune old entries."""

import argparse
import json
import sqlite3
import struct
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH


def serialize_f32(vector):
    return struct.pack(f"{len(vector)}f", *vector)


def deserialize_f32(blob):
    n = len(blob) // 4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)


def decay_importance(conn, days_threshold=30, decay_amount=1):
    """Reduce importance of memories older than threshold days."""
    updated = conn.execute(
        """
        UPDATE memories
        SET importance = MAX(1, importance - ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE julianday('now') - julianday(created_at) > ?
        AND importance > 1
        """,
        [decay_amount, days_threshold],
    ).rowcount
    return updated


def prune_low_importance(conn, max_entries=5000, min_importance=2):
    """Delete lowest importance entries when over limit."""
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    if total <= max_entries:
        return 0

    to_delete = total - max_entries

    # Get IDs to delete
    ids = conn.execute(
        """
        SELECT id FROM memories
        WHERE importance <= ?
        ORDER BY importance ASC, created_at ASC
        LIMIT ?
        """,
        [min_importance, to_delete],
    ).fetchall()
    id_list = [row[0] for row in ids]

    if not id_list:
        return 0

    placeholders = ",".join("?" * len(id_list))

    # Delete from vec table first
    try:
        conn.execute(
            f"DELETE FROM memories_vec WHERE id IN ({placeholders})",
            id_list,
        )
    except Exception:
        pass

    # Delete from memories (FTS5 trigger handles fts cleanup)
    deleted = conn.execute(
        f"DELETE FROM memories WHERE id IN ({placeholders})",
        id_list,
    ).rowcount

    return deleted


def merge_similar(conn, vec_loaded, threshold=0.92, batch_limit=500):
    """Merge very similar memories based on vector similarity.

    Uses numpy for vectorized dot product (O(n^2) but fast in practice).
    Only processes the most recent batch_limit entries.
    """
    if not vec_loaded:
        return 0

    rows = conn.execute(
        """
        SELECT v.id, v.embedding
        FROM memories_vec v
        JOIN memories m ON m.id = v.id
        ORDER BY m.created_at DESC
        LIMIT ?
        """,
        [batch_limit],
    ).fetchall()

    if len(rows) < 2:
        return 0

    ids = [row[0] for row in rows]
    # Build matrix of all embeddings (numpy vectorized)
    matrix = np.stack([deserialize_f32(row[1]) for row in rows])

    # Preload importance values
    placeholders = ",".join("?" * len(ids))
    imp_rows = conn.execute(
        f"SELECT id, importance FROM memories WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    imp_map = {r[0]: r[1] for r in imp_rows}

    to_delete = set()
    merged = 0

    for i in range(len(ids)):
        if ids[i] in to_delete:
            continue
        # Vectorized cosine similarity against all subsequent vectors
        sims = matrix[i] @ matrix[i + 1:].T  # normalized vectors → dot = cosine
        for j_offset in range(len(sims)):
            j = i + 1 + j_offset
            if ids[j] in to_delete:
                continue
            if sims[j_offset] >= threshold:
                imp1 = imp_map.get(ids[i], 0)
                imp2 = imp_map.get(ids[j], 0)
                if imp1 >= imp2:
                    to_delete.add(ids[j])
                else:
                    to_delete.add(ids[i])
                    break  # id[i] is deleted, stop comparing
                merged += 1

    for mid in to_delete:
        conn.execute("DELETE FROM memories WHERE id=?", [mid])
        conn.execute("DELETE FROM memories_vec WHERE id=?", [mid])

    return merged


def maintain(max_entries=5000, decay_days=30, merge_thresh=0.92):
    if not os.path.exists(DB_PATH):
        print(json.dumps({"error": "Database not found"}))
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=5000")

    # Load sqlite-vec once for all operations
    vec_loaded = False
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        vec_loaded = True
    except Exception:
        pass

    result = {"vec_loaded": vec_loaded}

    with conn:
        result["decayed"] = decay_importance(conn, decay_days)
        result["merged"] = merge_similar(conn, vec_loaded, merge_thresh)
        result["pruned"] = prune_low_importance(conn, max_entries)
        result["remaining"] = conn.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]

    conn.close()
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maintain memory database")
    parser.add_argument("--max-entries", type=int, default=5000)
    parser.add_argument("--decay-days", type=int, default=30)
    parser.add_argument("--merge-threshold", type=float, default=0.92)
    args = parser.parse_args()
    maintain(args.max_entries, args.decay_days, args.merge_threshold)
