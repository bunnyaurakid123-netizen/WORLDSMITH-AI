from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Memory:
    id: int
    kind: str
    content: str
    world_path: str | None
    created_at: str


class MemoryStore:
    """Local SQLite memory for preferences, feedback and recent WorldSmith sessions."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                world_path TEXT,
                created_at TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_path TEXT,
                prompt TEXT NOT NULL,
                plan_summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_path TEXT,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL,
                feedback TEXT,
                created_at TEXT NOT NULL
            )""")

    def remember(self, content: str, kind: str = "user", world_path: str | None = None) -> int:
        content = content.strip()
        if not content:
            raise ValueError("Memory cannot be empty")
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO memories(kind, content, world_path, created_at) VALUES (?, ?, ?, ?)",
                (kind, content, world_path, datetime.now(timezone.utc).isoformat()),
            )
            return int(cur.lastrowid)

    def forget(self, memory_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    def list(self, limit: int = 200) -> list[Memory]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT id, kind, content, world_path, created_at FROM memories ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 1000)),),
            ).fetchall()
        return [Memory(int(r["id"]), r["kind"], r["content"], r["world_path"], r["created_at"]) for r in rows]

    def search(self, query: str, world_path: str | None = None, limit: int = 12) -> list[Memory]:
        tokens = {t for t in re.findall(r"[a-zA-Z0-9_'-]+", query.lower()) if len(t) >= 3}
        memories = self.list(500)
        scored: list[tuple[int, Memory]] = []
        for memory in memories:
            text = memory.content.lower()
            score = sum(1 for token in tokens if token in text)
            if world_path and memory.world_path == world_path:
                score += 3
            if score:
                scored.append((score, memory))
        scored.sort(key=lambda item: (item[0], item[1].id), reverse=True)
        return [memory for _, memory in scored[:limit]]

    def save_conversation(self, world_path: str | None, prompt: str, plan_summary: str) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO conversations(world_path, prompt, plan_summary, created_at) VALUES (?, ?, ?, ?)",
                (world_path, prompt.strip(), plan_summary.strip(), datetime.now(timezone.utc).isoformat()),
            )

    def save_outcome(self, world_path: str | None, prompt: str, status: str, score: float | None = None, feedback: str = "") -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO outcomes(world_path, prompt, status, score, feedback, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (world_path, prompt.strip(), status.strip(), score, feedback.strip(), datetime.now(timezone.utc).isoformat()),
            )

    def recent_outcomes(self, world_path: str | None = None, limit: int = 10) -> list[dict]:
        with self._connect() as con:
            if world_path:
                rows = con.execute(
                    "SELECT prompt, status, score, feedback, created_at FROM outcomes WHERE world_path = ? ORDER BY id DESC LIMIT ?",
                    (world_path, max(1, min(limit, 50))),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT prompt, status, score, feedback, created_at FROM outcomes ORDER BY id DESC LIMIT ?",
                    (max(1, min(limit, 50))),
                ).fetchall()
        return [dict(r) for r in rows]

    def recent_conversations(self, world_path: str | None = None, limit: int = 10) -> list[dict]:
        with self._connect() as con:
            if world_path:
                rows = con.execute(
                    "SELECT prompt, plan_summary, created_at FROM conversations WHERE world_path = ? ORDER BY id DESC LIMIT ?",
                    (world_path, max(1, min(limit, 50))),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT prompt, plan_summary, created_at FROM conversations ORDER BY id DESC LIMIT ?",
                    (max(1, min(limit, 50)),),
                ).fetchall()
        return [dict(r) for r in rows]

    def build_context(self, query: str, world_path: str | None = None) -> str:
        memories = self.search(query, world_path=world_path)
        recent = self.recent_conversations(world_path, 5)
        outcomes = self.recent_outcomes(world_path, 5)
        parts: list[str] = []
        if memories:
            parts.append("RELEVANT LONG-TERM MEMORY:\n" + "\n".join(f"- {m.content}" for m in memories))
        if recent:
            parts.append("RECENT WORLDSMITH SESSIONS:\n" + "\n".join(f"- User: {r['prompt']}\n  Result: {r['plan_summary']}" for r in recent))
        if outcomes:
            parts.append("RECENT BUILD OUTCOMES:\n" + "\n".join(
                f"- Status: {r['status']} | Score: {r['score']} | Feedback: {r['feedback'] or 'none'} | Request: {r['prompt']}"
                for r in outcomes
            ))
        return "\n\n".join(parts)[:8000]
