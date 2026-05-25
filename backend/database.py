from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "recipeai.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    _seed_admin()


def _seed_admin() -> None:
    from auth import get_password_hash
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("admin@recipeai.com",)
        ).fetchone()
        if not existing:
            hashed = get_password_hash("admin123")
            conn.execute(
                "INSERT INTO users (email, hashed_password, role) VALUES (?, ?, ?)",
                ("admin@recipeai.com", hashed, "admin"),
            )
            conn.commit()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def create_user(email: str, hashed_password: str, role: str = "user") -> sqlite3.Row:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (email, hashed_password, role) VALUES (?, ?, ?)",
            (email, hashed_password, role),
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def get_all_users() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, email, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()


def delete_user(user_id: int) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,)
        )
        conn.commit()
        return result.rowcount > 0
