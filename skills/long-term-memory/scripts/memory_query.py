#!/usr/bin/env python3
"""Query long-term memory. FTS5 first, vector search as fallback."""

import argparse
import json
import re
import sqlite3
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH


def serialize_f32(vector):
    return struct.pack(f"{len(vector)}f", *vector)


def escape_fts5(query):
    """Escape FTS5 special characters and build a safe query."""
    cleaned = re.sub(r'[*"(){}[\]^~:+\-]', " ", query)
    tokens = cleaned.split()
    if not tokens:
        return None
    # Use OR for broad matching, quote each token
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def fts5_search(conn, query, top_k=5):
    """Full-text search using FTS5."""
    safe_query = escape_fts5(query)
    if not safe_query:
        return []
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.content, m.summary, m.category, m.importance,
                   m.created_at, m.session_id, fts.rank
            FROM memories_fts fts
            JOIN memories m ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY fts.rank
            LIMIT ?
            """,
            [safe_query, top_k],
        ).fetchall()

        results = []
        # Collect raw ranks for normalization
        raw_ranks = [abs(row[7]) for row in rows]
        max_rank = max(raw_ranks) if raw_ranks else 1.0

        for i, row in enumerate(rows):
            # Normalize FTS5 rank to 0~1 (higher is better)
            normalized_score = raw_ranks[i] / max_rank if max_rank > 0 else 0.0
            results.append({
                "id": row[0],
                "content": row[1],
                "summary": row[2],
                "category": row[3],
                "importance": row[4],
                "created_at": row[5],
                "session_id": row[6],
                "score": round(normalized_score, 4),
                "method": "fts5",
            })
        return results
    except Exception:
        return []


def vec_search(conn, query_text, top_k=5, threshold=0.6):
    """Vector similarity search using sqlite-vec."""
    try:
        from embed import embed_text

        query_embedding = embed_text(query_text)
        rows = conn.execute(
            """
            SELECT v.id, v.distance,
                   m.content, m.summary, m.category,
                   m.importance, m.created_at, m.session_id
            FROM memories_vec v
            JOIN memories m ON m.id = v.id
            WHERE v.embedding MATCH ?
            AND k = ?
            ORDER BY v.distance
            """,
            [serialize_f32(query_embedding), top_k],
        ).fetchall()

        results = []
        for row in rows:
            similarity = 1.0 - row[1]  # cosine distance → similarity
            if similarity >= threshold:
                results.append({
                    "id": row[0],
                    "content": row[2],
                    "summary": row[3],
                    "category": row[4],
                    "importance": row[5],
                    "created_at": row[6],
                    "session_id": row[7],
                    "score": round(similarity, 4),
                    "method": "vector",
                })
        return results
    except Exception:
        return []


def query_memory(query, top_k=5, threshold=0.6, mode="hybrid"):
    if not os.path.exists(DB_PATH):
        print(json.dumps({"results": [], "count": 0, "error": "Database not found"}))
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=5000")

    # Try to load sqlite-vec
    vec_enabled = False
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        vec_enabled = True
    except Exception:
        pass

    results = []

    if mode in ("fts", "hybrid"):
        results = fts5_search(conn, query, top_k)

        # Hybrid: if FTS5 returned fewer than 2 results, try vector search
        if mode == "hybrid" and len(results) < 2 and vec_enabled:
            vec_results = vec_search(conn, query, top_k, threshold)
            seen_ids = {r["id"] for r in results}
            for vr in vec_results:
                if vr["id"] not in seen_ids:
                    results.append(vr)
            results = results[:top_k]

    elif mode == "vec" and vec_enabled:
        results = vec_search(conn, query, top_k, threshold)

    conn.close()

    # Sort by importance (descending) then score (descending)
    results.sort(key=lambda r: (r["importance"], r["score"]), reverse=True)

    print(json.dumps({
        "results": results,
        "count": len(results),
        "mode": mode,
        "vec_available": vec_enabled,
    }, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query long-term memory")
    parser.add_argument("--query", "-q", default=None, help="Search query text")
    parser.add_argument("--stdin", action="store_true", help="Read query from stdin (safer for special characters)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Max results")
    parser.add_argument("--threshold", "-t", type=float, default=0.6, help="Vector similarity threshold")
    parser.add_argument("--mode", "-m", choices=["fts", "vec", "hybrid"], default="hybrid")
    args = parser.parse_args()

    query = args.query
    if args.stdin or query is None:
        query = sys.stdin.read().strip()
    if not query:
        print(json.dumps({"results": [], "count": 0, "error": "No query provided."}))
        sys.exit(1)

    query_memory(query, args.top_k, args.threshold, args.mode)
