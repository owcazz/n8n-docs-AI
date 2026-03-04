"""Persistent memory system using SQLite for conversation history and context."""

import json
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, category, key)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    category TEXT DEFAULT 'general',
    priority INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id, category);
CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, category);
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags);
"""


class Memory:
    """Persistent memory for conversations, facts, and notes."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info("Memory database initialized at %s", self.db_path)

    async def close(self):
        if self._db:
            await self._db.close()

    # --- Conversation History ---

    async def add_message(self, user_id: int, role: str, content: str, metadata: dict | None = None):
        await self._db.execute(
            "INSERT INTO conversations (user_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, role, content, json.dumps(metadata or {}), datetime.now(timezone.utc).isoformat()),
        )
        await self._db.commit()

    async def get_recent_messages(self, user_id: int, limit: int = 20) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT role, content, metadata, created_at FROM conversations "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in reversed(rows)
        ]

    # --- Facts (Long-term Knowledge) ---

    async def store_fact(self, user_id: int, category: str, key: str, value: str, confidence: float = 1.0):
        await self._db.execute(
            """INSERT INTO facts (user_id, category, key, value, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, category, key) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at""",
            (user_id, category, key, value, confidence, datetime.now(timezone.utc).isoformat()),
        )
        await self._db.commit()

    async def get_facts(self, user_id: int, category: str | None = None) -> list[dict]:
        if category:
            cursor = await self._db.execute(
                "SELECT category, key, value, confidence FROM facts WHERE user_id = ? AND category = ?",
                (user_id, category),
            )
        else:
            cursor = await self._db.execute(
                "SELECT category, key, value, confidence FROM facts WHERE user_id = ?",
                (user_id,),
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # --- Notes ---

    async def add_note(
        self,
        user_id: int,
        title: str,
        content: str,
        tags: list[str] | None = None,
        category: str = "general",
        priority: int = 0,
    ) -> int:
        cursor = await self._db.execute(
            "INSERT INTO notes (user_id, title, content, tags, category, priority, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, title, content,
                json.dumps(tags or []), category, priority,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def search_notes(self, user_id: int, query: str = "", category: str | None = None, tag: str | None = None) -> list[dict]:
        sql = "SELECT id, title, content, tags, category, priority, created_at FROM notes WHERE user_id = ?"
        params: list = [user_id]

        if query:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            sql += " AND category = ?"
            params.append(category)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        sql += " ORDER BY priority DESC, updated_at DESC LIMIT 50"
        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            {**dict(row), "tags": json.loads(row["tags"])}
            for row in rows
        ]

    async def update_note(self, note_id: int, **fields):
        allowed = {"title", "content", "tags", "category", "priority"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        await self._db.execute(
            f"UPDATE notes SET {set_clause} WHERE id = ?",
            [*updates.values(), note_id],
        )
        await self._db.commit()

    async def delete_note(self, note_id: int):
        await self._db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await self._db.commit()

    # --- Context Builder ---

    async def build_context(self, user_id: int) -> str:
        """Build a context string from facts and recent notes for the AI."""
        facts = await self.get_facts(user_id)
        recent_notes = await self.search_notes(user_id)

        parts = []
        if facts:
            parts.append("=== Known Facts About User ===")
            for f in facts:
                parts.append(f"[{f['category']}] {f['key']}: {f['value']}")

        if recent_notes:
            parts.append("\n=== Recent Notes ===")
            for n in recent_notes[:10]:
                tags_str = ", ".join(n["tags"]) if n["tags"] else ""
                parts.append(f"- [{n['category']}] {n['title']} {f'(#{tags_str})' if tags_str else ''}")

        return "\n".join(parts) if parts else ""
