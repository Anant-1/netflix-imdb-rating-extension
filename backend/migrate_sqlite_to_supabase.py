#!/usr/bin/env python3
"""Copy existing SQLite ratings into Supabase without deleting the source DB."""

import sqlite3
import sys
from pathlib import Path

from server import BASE_DIR, _supabase_request, init_db


def migrate():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "ratings_cache.db"
    if not source.is_file():
        raise SystemExit(f"SQLite cache not found: {source}")

    init_db()
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT query_title, title, imdb_id, rating, votes, year, genre, "
            "plot, source, updated_at FROM ratings"
        ).fetchall()

    migrated = 0
    for row in rows:
        _supabase_request(
            "POST",
            "ratings?on_conflict=query_title",
            dict(row),
            # Preserve any rows already written to Supabase after migration began.
            prefer="resolution=ignore-duplicates,return=minimal",
        )
        migrated += 1

    print(f"Migrated {migrated} ratings from {source}; source database was left intact.")


if __name__ == "__main__":
    migrate()
