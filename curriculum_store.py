"""Curriculum Store — single authoritative owner of lesson log + standing gap.
Pure stdlib (sqlite3). No network dependency. This is the durable layer that
the /home/claude/sie/lessons/*.md files never had: it survives past one sandbox.
"""
import sqlite3
from datetime import datetime, timezone

def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'unvetted',
        vetted_at TEXT,
        vet_note TEXT
    )""")
    # migration path for a db created before this column existed
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(lessons)").fetchall()}
    for col, ddl in [
        ("status", "ALTER TABLE lessons ADD COLUMN status TEXT NOT NULL DEFAULT 'unvetted'"),
        ("vetted_at", "ALTER TABLE lessons ADD COLUMN vetted_at TEXT"),
        ("vet_note", "ALTER TABLE lessons ADD COLUMN vet_note TEXT"),
    ]:
        if col not in existing_cols:
            conn.execute(ddl)
    conn.commit()
    # singleton row pattern: id is always 1, enforced by CHECK, so "the gap" is one owned value
    conn.execute("""CREATE TABLE IF NOT EXISTS gap (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        text TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def record_lesson(conn: sqlite3.Connection, title: str, content: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO lessons (title, content, created_at) VALUES (?, ?, ?)",
        (title, content, now),
    )
    conn.commit()
    return cur.lastrowid

def list_lessons(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status is None:
        rows = conn.execute(
            "SELECT id, title, created_at, status FROM lessons ORDER BY id"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, created_at, status FROM lessons WHERE status = ? ORDER BY id",
            (status,),
        ).fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2], "status": r[3]} for r in rows]

def get_lesson(conn: sqlite3.Connection, lesson_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, content, created_at, status, vetted_at, vet_note "
        "FROM lessons WHERE id = ?",
        (lesson_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "title": row[1], "content": row[2], "created_at": row[3],
        "status": row[4], "vetted_at": row[5], "vet_note": row[6],
    }

def promote_lesson(conn: sqlite3.Connection, lesson_id: int, note: str) -> None:
    """The gate. A lesson only counts as reusable after an explicit, on-record call —
    never automatic just because it ran without erroring."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE lessons SET status='vetted', vetted_at=?, vet_note=? WHERE id=?",
        (now, note, lesson_id),
    )
    conn.commit()

def reject_lesson(conn: sqlite3.Connection, lesson_id: int, note: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE lessons SET status='rejected', vetted_at=?, vet_note=? WHERE id=?",
        (now, note, lesson_id),
    )
    conn.commit()

def get_gap(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT text FROM gap WHERE id = 1").fetchone()
    return row[0] if row else None

def set_gap(conn: sqlite3.Connection, text: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO gap (id, text, updated_at) VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET text=excluded.text, updated_at=excluded.updated_at",
        (text, now),
    )
    conn.commit()
