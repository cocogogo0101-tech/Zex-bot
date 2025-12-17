"""
system_analytics.py

Comprehensive analytics subsystem for Zex-Bot.

Features:
- Attempts to reuse project's database connection if available (module `database`).
- Falls back to its own aiosqlite connection (default file 'analytics.db' or ANALYTICS_DB env).
- Creates an `analytics_events` table to store events.
- Provides a module-level `analytics_system` instance with async methods:
    - init(db_path=None)
    - record_event(guild_id, user_id, event, metadata=None)
    - get_recent(limit=50)
    - get_count_by_guild(guild_id)
    - get_top_events(limit=10)
    - close()
- Defensive: failures in analytics do not raise unhandled exceptions (best-effort).
- JSON-friendly metadata handling (stores metadata as JSON string if dict provided).
- Detailed docstrings and examples.

Usage:
    from system_analytics import analytics_system
    await analytics_system.record_event("guild_id", "user_id", "command:help", {"args": []})
"""

from __future__ import annotations

import os
import asyncio
import json
from typing import Optional, List, Dict, Any

# aiosqlite is optional but recommended; we'll handle its absence gracefully.
try:
    import aiosqlite  # type: ignore
except Exception:
    aiosqlite = None  # type: ignore

DEFAULT_DB = os.getenv("ANALYTICS_DB", "analytics.db")


class _NoopCursor:
    """Fallback cursor that does nothing (used when connection is missing)."""

    def execute(self, *args, **kwargs):
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def close(self):
        return None


class AnalyticsSystem:
    """
    AnalyticsSystem manages a lightweight analytics store.

    It tries to detect and reuse a project's database connection automatically.
    If not found, it opens its own aiosqlite connection.

    The implementation is defensive: if analytics fails it won't crash the bot.
    """

    def __init__(self) -> None:
        self._db_path: str = DEFAULT_DB
        self._conn: Optional[Any] = None
        self._own_connection: bool = False
        self._inited: bool = False
        self._init_lock = asyncio.Lock()

    # ---------------------
    # DB detection & utils
    # ---------------------
    async def _detect_shared_db(self) -> Optional[Any]:
        """
        Try to detect a shared DB connection exported by `database` module.

        Looks for:
        - async/sync functions: get_connection(), get_db(), get_conn()
        - attributes: conn, connection, db, db_conn
        Returns a connection-like object or None.
        """
        try:
            import database  # type: ignore
        except Exception:
            return None

        # Try common async getters
        for fn_name in ("get_connection", "get_db", "get_conn"):
            if hasattr(database, fn_name):
                fn = getattr(database, fn_name)
                if callable(fn):
                    try:
                        # prefer awaiting if coroutine
                        if asyncio.iscoroutinefunction(fn):
                            conn = await fn()
                        else:
                            conn = fn()
                        if conn:
                            return conn
                    except Exception:
                        # continue to next possibility
                        pass

        # Try attributes
        for attr in ("conn", "connection", "db", "db_conn", "connection_obj"):
            if hasattr(database, attr):
                try:
                    c = getattr(database, attr)
                    if c:
                        return c
                except Exception:
                    pass

        # Some projects expose a wrapper object `db` with an internal connection
        # Try db.connection or db._conn
        if hasattr(database, "db"):
            try:
                db_obj = getattr(database, "db")
                for sub in ("connection", "_conn", "_connection", "conn"):
                    if hasattr(db_obj, sub):
                        try:
                            val = getattr(db_obj, sub)
                            if val:
                                return val
                        except Exception:
                            pass
            except Exception:
                pass

        return None

    def _serialize_metadata(self, metadata: Optional[Any]) -> Optional[str]:
        """Serialize metadata to a JSON string when possible; otherwise string-cast."""
        if metadata is None:
            return None
        if isinstance(metadata, str):
            return metadata
        try:
            return json.dumps(metadata, default=str, ensure_ascii=False)
        except Exception:
            try:
                return str(metadata)
            except Exception:
                return None

    # ---------------------
    # Initialization
    # ---------------------
    async def init(self, db_path: Optional[str] = None) -> None:
        """
        Initialize analytics system.

        If `db_path` provided, it overrides the default analytics DB path.
        This function is idempotent.
        """
        async with self._init_lock:
            if self._inited:
                return

            if db_path:
                self._db_path = db_path

            # 1) Try to detect a project's shared DB connection
            shared_conn = None
            try:
                shared_conn = await self._detect_shared_db()
            except Exception:
                shared_conn = None

            if shared_conn:
                # Reuse shared connection (do not close it on close())
                self._conn = shared_conn
                self._own_connection = False
            else:
                # Fallback: create own aiosqlite connection
                if aiosqlite is None:
                    # If aiosqlite not installed, we cannot create an async sqlite connection.
                    # Keep analytics disabled but do not crash.
                    self._conn = None
                    self._own_connection = False
                    self._inited = True
                    return

                # Ensure directory exists
                db_dir = os.path.dirname(self._db_path)
                if db_dir and not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                    except Exception:
                        pass

                try:
                    self._conn = await aiosqlite.connect(self._db_path)
                    self._own_connection = True
                    # performance tweak
                    try:
                        await self._conn.execute("PRAGMA journal_mode=WAL;")
                    except Exception:
                        pass
                except Exception:
                    # if can't open DB, mark as inited to avoid retry loops and return
                    self._conn = None
                    self._own_connection = False
                    self._inited = True
                    return

            # Ensure schema exists (best-effort)
            try:
                if self._conn is not None:
                    # Some connections are sync connections; attempt async execute, else fallback
                    try:
                        await self._conn.execute(
                            """
                            CREATE TABLE IF NOT EXISTS analytics_events (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id TEXT,
                                user_id TEXT,
                                event TEXT NOT NULL,
                                metadata TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                        # commit if possible
                        try:
                            await self._conn.commit()
                        except Exception:
                            pass
                    except Exception:
                        # Try sync execution (for sqlite3.Connection)
                        try:
                            cur = self._conn.cursor()
                            cur.execute(
                                """
                                CREATE TABLE IF NOT EXISTS analytics_events (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    guild_id TEXT,
                                    user_id TEXT,
                                    event TEXT NOT NULL,
                                    metadata TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                                """
                            )
                            try:
                                self._conn.commit()
                            except Exception:
                                pass
                            try:
                                cur.close()
                            except Exception:
                                pass
                        except Exception:
                            pass
            except Exception:
                # swallow any errors related to schema creation
                pass

            self._inited = True

    # ---------------------
    # Recording & Queries
    # ---------------------
    async def record_event(
        self,
        guild_id: Optional[str],
        user_id: Optional[str],
        event: str,
        metadata: Optional[Any] = None,
    ) -> None:
        """
        Record an analytics event. Best-effort only — failures are swallowed.

        `metadata` can be a dict which will be JSON-serialized.
        """
        if not self._inited:
            try:
                await self.init()
            except Exception:
                return

        if self._conn is None:
            # No connection available; no-op
            return

        meta_str = self._serialize_metadata(metadata)

        # Attempt async insert first (aiosqlite-like)
        try:
            await self._conn.execute(
                "INSERT INTO analytics_events (guild_id, user_id, event, metadata) VALUES (?, ?, ?, ?);",
                (guild_id, user_id, event, meta_str),
            )
            try:
                await self._conn.commit()
            except Exception:
                pass
            return
        except Exception:
            # fall through to sync attempt
            pass

        # Try sync insert (sqlite3.Connection)
        try:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO analytics_events (guild_id, user_id, event, metadata) VALUES (?, ?, ?, ?);",
                (guild_id, user_id, event, meta_str),
            )
            try:
                self._conn.commit()
            except Exception:
                pass
            try:
                cur.close()
            except Exception:
                pass
            return
        except Exception:
            # give up silently
            return

    async def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return recent events as list of dicts:
        [{id, guild_id, user_id, event, metadata, created_at}, ...]
        """
        if not self._inited:
            await self.init()

        if self._conn is None:
            return []

        # Async attempt
        try:
            cur = await self._conn.execute(
                "SELECT id, guild_id, user_id, event, metadata, created_at "
                "FROM analytics_events ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
            rows = await cur.fetchall()
            try:
                await cur.close()
            except Exception:
                pass
            result = []
            for r in rows:
                result.append(
                    {
                        "id": r[0],
                        "guild_id": r[1],
                        "user_id": r[2],
                        "event": r[3],
                        "metadata": r[4],
                        "created_at": r[5],
                    }
                )
            return result
        except Exception:
            # Sync fallback
            try:
                cur = self._conn.cursor()
                cur.execute(
                    "SELECT id, guild_id, user_id, event, metadata, created_at "
                    "FROM analytics_events ORDER BY id DESC LIMIT ?;",
                    (limit,),
                )
                rows = cur.fetchall()
                result = []
                for r in rows:
                    result.append(
                        {
                            "id": r[0],
                            "guild_id": r[1],
                            "user_id": r[2],
                            "event": r[3],
                            "metadata": r[4],
                            "created_at": r[5],
                        }
                    )
                try:
                    cur.close()
                except Exception:
                    pass
                return result
            except Exception:
                return []

    async def get_count_by_guild(self, guild_id: str) -> int:
        """Return number of events for a given guild_id."""
        if not self._inited:
            await self.init()

        if self._conn is None:
            return 0

        try:
            cur = await self._conn.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE guild_id = ?;", (guild_id,)
            )
            row = await cur.fetchone()
            try:
                await cur.close()
            except Exception:
                pass
            return row[0] if row else 0
        except Exception:
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT COUNT(*) FROM analytics_events WHERE guild_id = ?;", (guild_id,))
                row = cur.fetchone()
                try:
                    cur.close()
                except Exception:
                    pass
                return row[0] if row else 0
            except Exception:
                return 0

    async def get_top_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return top events by count."""
        if not self._inited:
            await self.init()

        if self._conn is None:
            return []

        try:
            cur = await self._conn.execute(
                "SELECT event, COUNT(*) as cnt FROM analytics_events GROUP BY event ORDER BY cnt DESC LIMIT ?;", (limit,)
            )
            rows = await cur.fetchall()
            try:
                await cur.close()
            except Exception:
                pass
            return [{"event": r[0], "count": r[1]} for r in rows]
        except Exception:
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT event, COUNT(*) as cnt FROM analytics_events GROUP BY event ORDER BY cnt DESC LIMIT ?;", (limit,))
                rows = cur.fetchall()
                try:
                    cur.close()
                except Exception:
                    pass
                return [{"event": r[0], "count": r[1]} for r in rows]
            except Exception:
                return []

    # ---------------------
    # Close
    # ---------------------
    async def close(self) -> None:
        """Close analytics connection only if it was opened by this module."""
        if not self._inited:
            return
        if self._own_connection and self._conn is not None:
            try:
                # aiosqlite
                await self._conn.close()
            except Exception:
                try:
                    # sync sqlite3
                    self._conn.close()
                except Exception:
                    pass

        self._conn = None
        self._own_connection = False
        self._inited = False


# Module-level ready-to-use instance
analytics_system = AnalyticsSystem()