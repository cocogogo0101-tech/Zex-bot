"""
system_analytics.py

Improved analytics system for Zex-Bot.

Design goals:
- Integrate with project's existing DB connection if available (module `database`).
- Fall back to its own aiosqlite connection (analytics.db) if no shared DB present.
- Provide a module-level `analytics_system` with async methods used by the rest of the project.
- Be defensive: failing analytics should not crash the bot.
- Keep API flexible: record_event, get_recent, get_count_by_guild, get_top_events, init, close

Behavior:
- On init(), tries to detect and reuse an existing connection from a module named `database`:
    - looks for attributes: `get_connection`, `conn`, `connection`, `db`, or a function `get_db`
    - if a shared connection is found, uses it (and will not close it on close())
- If no shared DB, opens its own aiosqlite connection using ANALYTICS_DB env or 'analytics.db'.
- Creates table `analytics_events` if missing.
"""

import os
import asyncio
from typing import Optional, List, Dict, Any

try:
    import aiosqlite  # type: ignore
except Exception:
    aiosqlite = None  # Will raise on usage if missing

DEFAULT_DB = os.getenv("ANALYTICS_DB", "analytics.db")

class AnalyticsSystem:
    def __init__(self):
        self._db_path = DEFAULT_DB
        self._conn: Optional["aiosqlite.Connection"] = None
        self._own_connection = False  # whether this instance opened the connection
        self._init_lock = asyncio.Lock()
        self._inited = False

    async def _detect_shared_db(self):
        """
        Try to detect a shared DB connection in the project's database module.
        Returns a connection-like object or None.
        """
        try:
            import database  # try project's database module
        except Exception:
            return None

        # Common patterns to look for
        # functions
        if hasattr(database, "get_connection") and callable(getattr(database, "get_connection")):
            try:
                conn = await database.get_connection()  # some projects use async getter
                return conn
            except Exception:
                try:
                    conn = database.get_connection()  # sync getter
                    return conn
                except Exception:
                    pass

        if hasattr(database, "get_db") and callable(getattr(database, "get_db")):
            try:
                conn = await database.get_db()
                return conn
            except Exception:
                try:
                    conn = database.get_db()
                    return conn
                except Exception:
                    pass

        # attributes
        for attr in ("conn", "connection", "db", "db_conn", "connection_obj"):
            if hasattr(database, attr):
                try:
                    c = getattr(database, attr)
                    if c is not None:
                        return c
                except Exception:
                    pass

        return None

    async def init(self, db_path: Optional[str] = None):
        """Initialize analytics system. If a shared DB connection exists, reuse it."""
        async with self._init_lock:
            if self._inited:
                return
            if db_path:
                self._db_path = db_path

            # Try to detect a shared connection in project's database module
            shared = None
            try:
                shared = await self._detect_shared_db()
            except Exception:
                shared = None

            if shared is not None:
                # Reuse shared connection (do not close it on analytics.close)
                self._conn = shared
                self._own_connection = False
            else:
                # Fallback: open our own aiosqlite connection
                if aiosqlite is None:
                    raise RuntimeError("aiosqlite is required for analytics but not installed.")
                # ensure directory exists
                db_dir = os.path.dirname(self._db_path)
                if db_dir and not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                    except Exception:
                        pass
                self._conn = await aiosqlite.connect(self._db_path)
                self._own_connection = True
                # tweak pragmas if possible
                try:
                    await self._conn.execute("PRAGMA journal_mode=WAL;")
                except Exception:
                    pass

            # Ensure table exists (use try/except to prevent crashes)
            try:
                await self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT,
                        user_id TEXT,
                        event TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # If using aiosqlite, commit
                try:
                    await self._conn.commit()
                except Exception:
                    pass
            except Exception:
                # swallow; analytics mustn't break bot
                pass

            self._inited = True

    async def record_event(self, guild_id: Optional[str], user_id: Optional[str], event: str, metadata: Optional[str] = None):
        """Record a simple analytics event in DB. Best-effort only."""
        if not self._inited:
            try:
                await self.init()
            except Exception:
                return
        try:
            # Some shared dbs (e.g., aiosqlite) use .execute; some use SQLAlchemy-like APIs.
            # Try basic insert for sqlite-like connections.
            await self._conn.execute(
                "INSERT INTO analytics_events (guild_id, user_id, event, metadata) VALUES (?, ?, ?, ?);",
                (guild_id, user_id, event, metadata)
            )
            try:
                await self._conn.commit()
            except Exception:
                pass
        except Exception:
            # best-effort: attempt to use fallback methods (e.g., execute may be sync)
            try:
                # synchronous execute (if connection is sqlite3.Connection)
                cur = self._conn.cursor()
                cur.execute(
                    "INSERT INTO analytics_events (guild_id, user_id, event, metadata) VALUES (?, ?, ?, ?);",
                    (guild_id, user_id, event, metadata)
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
                # give up silently
                return

    async def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent events as list of dicts"""
        if not self._inited:
            await self.init()
        try:
            cur = await self._conn.execute("SELECT id, guild_id, user_id, event, metadata, created_at FROM analytics_events ORDER BY id DESC LIMIT ?;", (limit,))
            rows = await cur.fetchall()
            try:
                await cur.close()
            except Exception:
                pass
            result = []
            for r in rows:
                result.append({
                    "id": r[0],
                    "guild_id": r[1],
                    "user_id": r[2],
                    "event": r[3],
                    "metadata": r[4],
                    "created_at": r[5]
                })
            return result
        except Exception:
            # Try sync cursor fallback
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT id, guild_id, user_id, event, metadata, created_at FROM analytics_events ORDER BY id DESC LIMIT ?;", (limit,))
                rows = cur.fetchall()
                result = []
                for r in rows:
                    result.append({
                        "id": r[0],
                        "guild_id": r[1],
                        "user_id": r[2],
                        "event": r[3],
                        "metadata": r[4],
                        "created_at": r[5]
                    })
                return result
            except Exception:
                return []

    async def get_count_by_guild(self, guild_id: str) -> int:
        if not self._inited:
            await self.init()
        try:
            cur = await self._conn.execute("SELECT COUNT(*) FROM analytics_events WHERE guild_id = ?;", (guild_id,))
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
                return row[0] if row else 0
            except Exception:
                return 0

    async def get_top_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._inited:
            await self.init()
        try:
            cur = await self._conn.execute("SELECT event, COUNT(*) as cnt FROM analytics_events GROUP BY event ORDER BY cnt DESC LIMIT ?;", (limit,))
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
                return [{"event": r[0], "count": r[1]} for r in rows]
            except Exception:
                return []

    async def close(self):
        """Close analytics connection only if we opened it."""
        if not self._inited:
            return
        if self._own_connection and self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._inited = False
        self._own_connection = False

# Module-level ready-to-use instance
analytics_system = AnalyticsSystem()
```0