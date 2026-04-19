from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class PromptRecord:
    name: str
    content: str
    updated_at: str


@dataclass(frozen=True)
class RuntimeSettingRecord:
    key: str
    value: str
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromptStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)

    def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompts (
                  name TEXT PRIMARY KEY,
                  content TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """,
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_settings (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """,
            )
            conn.commit()

    def get_prompt(self, name: str) -> PromptRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT name, content, updated_at FROM prompts WHERE name = ?",
                (name,),
            ).fetchone()
            if row is None:
                return None
            return PromptRecord(name=row[0], content=row[1], updated_at=row[2])

    def set_prompt(self, name: str, content: str) -> PromptRecord:
        updated_at = _utc_now_iso()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO prompts(name, content, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                  content = excluded.content,
                  updated_at = excluded.updated_at
                """,
                (name, content, updated_at),
            )
            conn.commit()
        return PromptRecord(name=name, content=content, updated_at=updated_at)

    def list_prompts(self) -> list[PromptRecord]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT name, content, updated_at FROM prompts ORDER BY name ASC",
            ).fetchall()
        return [PromptRecord(name=row[0], content=row[1], updated_at=row[2]) for row in rows]

    def get_setting(self, key: str) -> RuntimeSettingRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT key, value, updated_at FROM runtime_settings WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            return RuntimeSettingRecord(key=row[0], value=row[1], updated_at=row[2])

    def set_setting(self, key: str, value: str) -> RuntimeSettingRecord:
        updated_at = _utc_now_iso()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO runtime_settings(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  value = excluded.value,
                  updated_at = excluded.updated_at
                """,
                (key, value, updated_at),
            )
            conn.commit()
        return RuntimeSettingRecord(key=key, value=value, updated_at=updated_at)
