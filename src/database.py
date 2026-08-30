"""История надиктованного.

Раньше здесь была заглушка, которая к тому же не импортировалась: вместо
тройных кавычек в файле стояло ``\\"\\"\\"``, и Python отказывался его читать.

Теперь это работающее хранилище: всё распознанное сохраняется, и текст,
случайно затёртый в буфере обмена, можно найти.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

APP_NAME = "VoiceDictation"

SCHEMA = """
CREATE TABLE IF NOT EXISTS phrases (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    text     TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'ru',
    said_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_phrases_said_at ON phrases(said_at);
"""


def default_path() -> Path:
    """База в системной папке приложения, а не рядом с программой."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_NAME / "history.db"


class Database:
    """История распознанных фраз."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.path = Path(db_path) if db_path else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def add(self, text: str, language: str = "ru") -> Optional[int]:
        """Записать фразу. Пустые не сохраняются."""
        text = (text or "").strip()
        if not text:
            return None
        cursor = self.conn.execute(
            "INSERT INTO phrases (text, language, said_at) VALUES (?, ?, ?)",
            (text, language, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.commit()
        return cursor.lastrowid

    def recent(self, limit: int = 20) -> List[dict]:
        rows = self.conn.execute(
            "SELECT id, text, language, said_at FROM phrases ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]

    def search(self, needle: str, limit: int = 20) -> List[dict]:
        """Найти фразу по куску текста."""
        rows = self.conn.execute(
            "SELECT id, text, language, said_at FROM phrases "
            "WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{needle}%", limit),
        )
        return [dict(row) for row in rows]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM phrases").fetchone()[0])

    def clear(self) -> None:
        self.conn.execute("DELETE FROM phrases")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
