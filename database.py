"""
database.py - ULTIMATE FIXED VERSION
=====================================
قاعدة بيانات شاملة مع دعم كامل للتكتات المتقدمة

✅ جميع الدوال الأساسية
✅ دعم التكتات V2 المتقدمة
✅ دوال الفئات والألواح
✅ Transcripts
✅ دوال مساعدة للـ mystery games
✅ Error handling محسّن
"""

import aiosqlite
import asyncio
import json
from typing import Optional, Any, Dict, List, Tuple
from datetime import datetime
from logger import bot_logger

DB_PATH = 'database.db'


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    # ==================== Connection ====================

    async def connect(self):
        """فتح الاتصال"""
        if self.conn:
            return
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            await self.conn.execute('PRAGMA foreign_keys = ON;')
            await self.create_tables()
            await self.conn.commit()
            bot_logger.success('✅ Database connected')
        except Exception as e:
            bot_logger.exception('❌ Failed to connect to database', e)
            raise

    async def close(self):
        """إغلاق الاتصال"""
        if not self.conn:
            return
        try:
            await self.conn.close()
            self.conn = None
            bot_logger.info('Database closed')
        except Exception as e:
            bot_logger.error(f'Error closing DB: {e}')

    # ==================== Schema Creation ====================

    async def create_tables(self):
        """إنشاء جميع الجداول"""
        if not self.conn:
            raise RuntimeError('DB not connected')

        async with self._lock:
            try:
                # Settings
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        guild_id TEXT PRIMARY KEY,
                        welcome_enabled INTEGER DEFAULT 1,
                        welcome_channel_id TEXT,
                        welcome_message TEXT,
                        welcome_type TEXT DEFAULT 'text',
                        goodbye_enabled INTEGER DEFAULT 0,
                        goodbye_channel_id TEXT,
                        goodbye_message TEXT,
                        logs_channel_id TEXT,
                        support_role_id TEXT,
                        autorole_id TEXT,
                        prefix TEXT DEFAULT '!',
                        language TEXT DEFAULT 'ar',
                        antispam_enabled INTEGER DEFAULT 0,
                        antispam_threshold INTEGER DEFAULT 5,
                        antilink_enabled INTEGER DEFAULT 0,
                        automod_enabled INTEGER DEFAULT 0,
                        leveling_enabled INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Warnings
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        moderator_id TEXT NOT NULL,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Notes
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        moderator_id TEXT NOT NULL,
                        note TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Tickets (legacy)
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS tickets (
                        channel_id TEXT PRIMARY KEY,
                        guild_id TEXT NOT NULL,
                        opener_id TEXT NOT NULL,
                        reason TEXT,
                        status TEXT DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP,
                        closed_by TEXT
                    )
                ''')

                # ✅ Tickets V2 (Advanced) - FIXED
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS tickets_v2 (
                        ticket_id INTEGER PRIMARY KEY,
                        channel_id TEXT UNIQUE,
                        guild_id TEXT NOT NULL,
                        creator_id TEXT NOT NULL,
                        category_id TEXT,
                        reason TEXT,
                        custom_answers TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'open',
                        claimed_by TEXT,
                        priority TEXT DEFAULT 'normal',
                        tags TEXT,
                        notes TEXT,
                        rating INTEGER,
                        closed_at TIMESTAMP,
                        closed_by TEXT,
                        close_reason TEXT
                    )
                ''')

                # ✅ Ticket Categories
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS ticket_categories (
                        guild_id TEXT NOT NULL,
                        category_id TEXT NOT NULL,
                        data TEXT NOT NULL,
                        PRIMARY KEY (guild_id, category_id)
                    )
                ''')

                # ✅ Ticket Panels
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS ticket_panels (
                        message_id TEXT PRIMARY KEY,
                        guild_id TEXT,
                        channel_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data TEXT
                    )
                ''')

                # ✅ Ticket Transcripts
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS ticket_transcripts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket_id INTEGER,
                        file_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Leveling
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS levels (
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 0,
                        messages INTEGER DEFAULT 0,
                        last_xp_time TIMESTAMP,
                        PRIMARY KEY (guild_id, user_id)
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS leveling_config (
                        guild_id TEXT PRIMARY KEY,
                        xp_per_message_min INTEGER DEFAULT 15,
                        xp_per_message_max INTEGER DEFAULT 25,
                        message_cooldown INTEGER DEFAULT 60,
                        xp_per_voice_5min INTEGER DEFAULT 1,
                        xp_per_voice_2min INTEGER DEFAULT 1,
                        level_curve TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS leveling_role_multipliers (
                        guild_id TEXT NOT NULL,
                        role_id TEXT NOT NULL,
                        multiplier REAL DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (guild_id, role_id)
                    )
                ''')

                # Autoresponses
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS autoresponses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        trigger TEXT NOT NULL,
                        response TEXT NOT NULL,
                        trigger_type TEXT DEFAULT 'contains',
                        enabled INTEGER DEFAULT 1,
                        chance INTEGER DEFAULT 100,
                        cooldown INTEGER DEFAULT 0,
                        last_used TIMESTAMP,
                        channels TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS blacklist_words (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        word TEXT NOT NULL,
                        action TEXT DEFAULT 'delete',
                        enabled INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Logs
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        user_id TEXT,
                        moderator_id TEXT,
                        target_id TEXT,
                        reason TEXT,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS lists (
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        list_type TEXT NOT NULL,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (guild_id, user_id, list_type)
                    )
                ''')

                # Polls
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS polls (
                        poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        message_id TEXT,
                        creator_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        options TEXT NOT NULL,
                        duration_minutes INTEGER DEFAULT 60,
                        allow_multiple INTEGER DEFAULT 0,
                        anonymous INTEGER DEFAULT 0,
                        is_closed INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS poll_votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        poll_id INTEGER NOT NULL,
                        user_id TEXT NOT NULL,
                        option_index INTEGER NOT NULL,
                        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
                    )
                ''')

                # Invites
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS invites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        inviter_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS invite_rewards (
                        guild_id TEXT NOT NULL,
                        required_invites INTEGER NOT NULL,
                        role_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (guild_id, required_invites)
                    )
                ''')

                # Stats
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS stats (
                        guild_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        messages INTEGER DEFAULT 0,
                        joins INTEGER DEFAULT 0,
                        leaves INTEGER DEFAULT 0,
                        voice_minutes INTEGER DEFAULT 0,
                        PRIMARY KEY (guild_id, date)
                    )
                ''')

                # Reminders
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        message TEXT NOT NULL,
                        remind_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.commit()
                bot_logger.success('✅ All tables created')

            except Exception as e:
                bot_logger.exception('❌ Failed creating tables', e)
                raise

    # ==================== Raw Helpers ====================

    async def execute(self, sql: str, params: tuple = ()):
        """تنفيذ SQL"""
        if not self.conn:
            raise RuntimeError('DB not connected')
        async with self._lock:
            try:
                cur = await self.conn.execute(sql, params)
                await self.conn.commit()
                return cur
            except Exception as e:
                bot_logger.database_error('execute', str(e))
                raise

    async def fetchone(self, sql: str, params: tuple = ()):
        """جلب صف واحد"""
        if not self.conn:
            raise RuntimeError('DB not connected')
        async with self._lock:
            cur = await self.conn.execute(sql, params)
            row = await cur.fetchone()
            return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple = ()):
        """جلب جميع الصفوف"""
        if not self.conn:
            raise RuntimeError('DB not connected')
        async with self._lock:
            cur = await self.conn.execute(sql, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ==================== Settings ====================

    async def get_settings(self, guild_id: str) -> Optional[Dict]:
        try:
            return await self.fetchone('SELECT * FROM settings WHERE guild_id = ?', (guild_id,))
        except Exception as e:
            bot_logger.database_error('get_settings', str(e))
            return None

    async def update_setting(self, guild_id: str, key: str, value: Any):
        try:
            exists = await self.fetchone('SELECT 1 FROM settings WHERE guild_id = ?', (guild_id,))
            if not exists:
                await self.execute(f'INSERT INTO settings (guild_id, {key}) VALUES (?, ?)', (guild_id, value))
            else:
                await self.execute(f'UPDATE settings SET {key} = ? WHERE guild_id = ?', (value, guild_id))
            bot_logger.database_query('UPDATE', 'settings', True)
        except Exception as e:
            bot_logger.database_error('update_setting', str(e))
            raise

    async def init_guild(self, guild_id: str):
        try:
            if not await self.fetchone('SELECT 1 FROM settings WHERE guild_id = ?', (guild_id,)):
                await self.execute('INSERT INTO settings (guild_id) VALUES (?)', (guild_id,))
                bot_logger.info(f'init_guild: {guild_id}')
        except Exception as e:
            bot_logger.database_error('init_guild', str(e))

    # ==================== ✅ TICKETS V2 - FIXED ====================

    async def save_ticket_v2(
        self,
        ticket_id: int,
        channel_id: str,
        guild_id: str,
        creator_id: str,
        category_id: str = None,
        reason: str = None,
        custom_answers: Optional[dict] = None,
        status: str = 'open'
    ):
        """حفظ تكت جديد V2"""
        try:
            ca = json.dumps(custom_answers or {})
            await self.execute('''
                INSERT INTO tickets_v2
                (ticket_id, channel_id, guild_id, creator_id, category_id, reason, custom_answers, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ticket_id, channel_id, guild_id, creator_id, category_id, reason, ca, datetime.now().isoformat(), status))
            bot_logger.debug(f'✅ Saved ticket #{ticket_id}')
        except Exception as e:
            bot_logger.database_error('save_ticket_v2', str(e))

    async def update_ticket_v2(self, channel_id: str, **fields):
        """تحديث تكت V2"""
        try:
            if not fields:
                return
            cols = []
            params = []
            for k, v in fields.items():
                cols.append(f'{k} = ?')
                params.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
            params.append(channel_id)
            sql = f'UPDATE tickets_v2 SET {", ".join(cols)} WHERE channel_id = ?'
            await self.execute(sql, tuple(params))
        except Exception as e:
            bot_logger.database_error('update_ticket_v2', str(e))

    async def get_ticket_v2(self, channel_id: str) -> Optional[Dict]:
        """جلب تكت V2"""
        try:
            return await self.fetchone('SELECT * FROM tickets_v2 WHERE channel_id = ?', (channel_id,))
        except Exception:
            return None

    async def get_ticket_by_id_v2(self, ticket_id: int) -> Optional[Dict]:
        """جلب تكت بالـ ID"""
        try:
            return await self.fetchone('SELECT * FROM tickets_v2 WHERE ticket_id = ?', (ticket_id,))
        except Exception:
            return None

    async def list_tickets_v2(self, guild_id: str, status: Optional[str] = None) -> List[Dict]:
        """قائمة التكتات"""
        try:
            if status:
                return await self.fetchall(
                    'SELECT * FROM tickets_v2 WHERE guild_id = ? AND status = ? ORDER BY created_at DESC',
                    (guild_id, status)
                )
            return await self.fetchall(
                'SELECT * FROM tickets_v2 WHERE guild_id = ? ORDER BY created_at DESC',
                (guild_id,)
            )
        except Exception:
            return []

    # ==================== ✅ TICKET CATEGORIES ====================

    async def save_ticket_category(self, guild_id: str, category_id: str, data: dict):
        """حفظ فئة تكت"""
        try:
            await self.execute('''
                INSERT INTO ticket_categories (guild_id, category_id, data)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, category_id) DO UPDATE SET data = excluded.data
            ''', (guild_id, category_id, json.dumps(data)))
            bot_logger.debug(f'✅ Saved category {category_id}')
        except Exception as e:
            bot_logger.database_error('save_ticket_category', str(e))

    async def load_ticket_categories(self, guild_id: str) -> List[Dict]:
        """تحميل فئات التكتات"""
        try:
            rows = await self.fetchall(
                'SELECT category_id, data FROM ticket_categories WHERE guild_id = ?',
                (guild_id,)
            )
            out = []
            for r in rows:
                try:
                    rdata = json.loads(r['data']) if r.get('data') else {}
                except Exception:
                    rdata = {}
                out.append({'category_id': r['category_id'], 'data': rdata})
            return out
        except Exception as e:
            bot_logger.database_error('load_ticket_categories', str(e))
            return []

    async def remove_ticket_category(self, guild_id: str, category_id: str):
        """حذف فئة"""
        try:
            await self.execute(
                'DELETE FROM ticket_categories WHERE guild_id = ? AND category_id = ?',
                (guild_id, category_id)
            )
        except Exception as e:
            bot_logger.database_error('remove_ticket_category', str(e))

    # ==================== ✅ TICKET PANELS ====================

    async def save_ticket_panel(self, message_id: str, guild_id: str, channel_id: str, data: dict = None):
        """حفظ لوحة تكت"""
        try:
            await self.execute(
                'INSERT OR REPLACE INTO ticket_panels (message_id, guild_id, channel_id, data) VALUES (?, ?, ?, ?)',
                (message_id, guild_id, channel_id, json.dumps(data or {}))
            )
        except Exception as e:
            bot_logger.database_error('save_ticket_panel', str(e))

    async def get_ticket_panel(self, message_id: str) -> Optional[Dict]:
        """جلب لوحة تكت"""
        try:
            row = await self.fetchone('SELECT * FROM ticket_panels WHERE message_id = ?', (message_id,))
            if row and row.get('data'):
                try:
                    row['data'] = json.loads(row['data'])
                except Exception:
                    pass
            return row
        except Exception as e:
            bot_logger.database_error('get_ticket_panel', str(e))
            return None

    # ==================== ✅ TRANSCRIPTS ====================

    async def save_transcript(self, ticket_id: int, file_path: str):
        """حفظ transcript"""
        try:
            await self.execute(
                'INSERT INTO ticket_transcripts (ticket_id, file_path) VALUES (?, ?)',
                (ticket_id, file_path)
            )
        except Exception as e:
            bot_logger.database_error('save_transcript', str(e))

    async def get_transcripts_for_ticket(self, ticket_id: int) -> List[Dict]:
        """جلب transcripts لتكت"""
        try:
            return await self.fetchall(
                'SELECT * FROM ticket_transcripts WHERE ticket_id = ? ORDER BY created_at DESC',
                (ticket_id,)
            )
        except Exception:
            return []

    # ==================== Warnings ====================

    async def add_warning(self, guild_id: str, user_id: str, moderator_id: str, reason: str = None) -> int:
        try:
            cur = await self.execute(
                'INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)',
                (guild_id, user_id, moderator_id, reason)
            )
            return getattr(cur, 'lastrowid', 0) or 0
        except Exception:
            return 0

    async def get_warnings(self, guild_id: str, user_id: str) -> List[Dict]:
        try:
            return await self.fetchall(
                'SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC',
                (guild_id, user_id)
            )
        except Exception:
            return []

    async def clear_warnings(self, guild_id: str, user_id: str):
        try:
            await self.execute('DELETE FROM warnings WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
        except Exception as e:
            bot_logger.database_error('clear_warnings', str(e))

    async def get_warning_count(self, guild_id: str, user_id: str) -> int:
        try:
            row = await self.fetchone(
                'SELECT COUNT(*) as cnt FROM warnings WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            return row['cnt'] if row else 0
        except Exception:
            return 0

    # ==================== Tickets (Legacy) ====================

    async def create_ticket(self, channel_id: str, guild_id: str, opener_id: str, reason: str = None):
        try:
            await self.execute(
                'INSERT INTO tickets (channel_id, guild_id, opener_id, reason) VALUES (?, ?, ?, ?)',
                (channel_id, guild_id, opener_id, reason)
            )
        except Exception as e:
            bot_logger.database_error('create_ticket', str(e))

    async def get_ticket(self, channel_id: str) -> Optional[Dict]:
        try:
            return await self.fetchone('SELECT * FROM tickets WHERE channel_id = ?', (channel_id,))
        except Exception:
            return None

    async def close_ticket(self, channel_id: str, closed_by: str):
        try:
            await self.execute(
                'UPDATE tickets SET status = ?, closed_at = ?, closed_by = ? WHERE channel_id = ?',
                ('closed', datetime.now().isoformat(), closed_by, channel_id)
            )
        except Exception as e:
            bot_logger.database_error('close_ticket', str(e))

    # ==================== Leveling ====================

    async def add_xp(self, guild_id: str, user_id: str, xp: int) -> Dict:
        try:
            row = await self.fetchone('SELECT * FROM levels WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
            if row:
                data = dict(row)
                new_xp = data.get('xp', 0) + xp
                old_level = data.get('level', 0)
                new_level = int(new_xp ** 0.5) // 10
                new_messages = data.get('messages', 0) + 1
                await self.execute(
                    'UPDATE levels SET xp = ?, level = ?, messages = ?, last_xp_time = ? WHERE guild_id = ? AND user_id = ?',
                    (new_xp, new_level, new_messages, datetime.now().isoformat(), guild_id, user_id)
                )
                return {'xp': new_xp, 'level': new_level, 'old_level': old_level, 'leveled_up': new_level > old_level}
            else:
                await self.execute(
                    'INSERT INTO levels (guild_id, user_id, xp, level, messages, last_xp_time) VALUES (?, ?, ?, ?, ?, ?)',
                    (guild_id, user_id, xp, 0, 1, datetime.now().isoformat())
                )
                return {'xp': xp, 'level': 0, 'old_level': 0, 'leveled_up': False}
        except Exception as e:
            bot_logger.database_error('add_xp', str(e))
            return {'xp': 0, 'level': 0, 'old_level': 0, 'leveled_up': False}

    async def get_level(self, guild_id: str, user_id: str) -> Optional[Dict]:
        try:
            return await self.fetchone('SELECT * FROM levels WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
        except Exception:
            return None

    async def get_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?', (guild_id, limit))
        except Exception:
            return []

    # ==================== Autoresponses ====================

    async def add_autoresponse(
        self,
        guild_id: str,
        trigger: str,
        response: str,
        trigger_type: str = 'contains',
        chance: int = 100,
        cooldown: int = 0,
        enabled: int = 1,
        channels: Optional[str] = None
    ) -> int:
        try:
            cur = await self.execute(
                'INSERT INTO autoresponses (guild_id, trigger, response, trigger_type, enabled, chance, cooldown, channels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (guild_id, trigger, response, trigger_type, enabled, chance, cooldown, channels)
            )
            return getattr(cur, 'lastrowid', 0) or 0
        except Exception as e:
            bot_logger.database_error('add_autoresponse', str(e))
            return 0

    async def get_autoresponses(self, guild_id: str) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM autoresponses WHERE guild_id = ? ORDER BY id ASC', (guild_id,))
        except Exception:
            return []

    async def remove_autoresponse(self, ar_id: int) -> bool:
        try:
            await self.execute('DELETE FROM autoresponses WHERE id = ?', (ar_id,))
            return True
        except Exception:
            return False

    async def toggle_autoresponse(self, ar_id: int) -> bool:
        try:
            row = await self.fetchone('SELECT enabled FROM autoresponses WHERE id = ?', (ar_id,))
            if not row:
                return False
            current = row['enabled']
            new = 0 if (current == 1 or current is True) else 1
            await self.execute('UPDATE autoresponses SET enabled = ? WHERE id = ?', (new, ar_id))
            return bool(new)
        except Exception as e:
            bot_logger.database_error('toggle_autoresponse', str(e))
            return False

    async def update_autoresponse(self, ar_id: int, **fields) -> bool:
        allowed = {'trigger', 'response', 'trigger_type', 'enabled', 'chance', 'cooldown', 'channels', 'last_used'}
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        params.append(ar_id)
        sql = f"UPDATE autoresponses SET {', '.join(updates)} WHERE id = ?"
        try:
            await self.execute(sql, tuple(params))
            return True
        except Exception as e:
            bot_logger.database_error('update_autoresponse', str(e))
            return False

    async def search_autoresponses(self, guild_id: str, query: str) -> List[Dict]:
        try:
            q = f"%{query}%"
            return await self.fetchall(
                'SELECT * FROM autoresponses WHERE guild_id = ? AND (trigger LIKE ? OR response LIKE ?) ORDER BY id ASC',
                (guild_id, q, q)
            )
        except Exception:
            return []

    async def get_autoresponse_stats(self, guild_id: str) -> Dict[str, Any]:
        try:
            total_row = await self.fetchone('SELECT COUNT(*) as cnt FROM autoresponses WHERE guild_id = ?', (guild_id,))
            enabled_row = await self.fetchone('SELECT COUNT(*) as cnt FROM autoresponses WHERE guild_id = ? AND enabled = 1', (guild_id,))
            total = total_row['cnt'] if total_row else 0
            enabled = enabled_row['cnt'] if enabled_row else 0
            disabled = total - enabled
            rows = await self.fetchall('SELECT trigger_type, COUNT(*) as cnt FROM autoresponses WHERE guild_id = ? GROUP BY trigger_type', (guild_id,))
            by_type = {r['trigger_type']: r['cnt'] for r in rows} if rows else {}
            return {'total': total, 'enabled': enabled, 'disabled': disabled, 'by_type': by_type}
        except Exception as e:
            bot_logger.database_error('get_autoresponse_stats', str(e))
            return {'total': 0, 'enabled': 0, 'disabled': 0, 'by_type': {}}

    # ==================== Polls ====================

    async def create_poll(
        self,
        guild_id: str,
        channel_id: str,
        creator_id: str,
        question: str,
        options: List[str],
        duration_minutes: int = 60,
        allow_multiple: int = 0,
        anonymous: int = 0
    ) -> int:
        try:
            opts = json.dumps(options)
            cur = await self.execute(
                'INSERT INTO polls (guild_id, channel_id, creator_id, question, options, duration_minutes, allow_multiple, anonymous) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (guild_id, channel_id, creator_id, question, opts, duration_minutes, allow_multiple, anonymous)
            )
            return getattr(cur, 'lastrowid', 0) or 0
        except Exception as e:
            bot_logger.database_error('create_poll', str(e))
            return 0

    async def get_poll(self, poll_id: int) -> Optional[Dict]:
        try:
            row = await self.fetchone('SELECT * FROM polls WHERE poll_id = ?', (poll_id,))
            if row and row.get('options'):
                try:
                    row['options'] = json.loads(row['options'])
                except Exception:
                    pass
            return row
        except Exception:
            return None

    async def close_poll(self, poll_id: int):
        try:
            await self.execute(
                'UPDATE polls SET is_closed = 1, closed_at = ? WHERE poll_id = ?',
                (datetime.now().isoformat(), poll_id)
            )
        except Exception as e:
            bot_logger.database_error('close_poll', str(e))

    async def vote_poll(self, poll_id: int, user_id: str, option_index: int):
        try:
            poll = await self.get_poll(poll_id)
            if not poll:
                return False
            if not poll.get('allow_multiple'):
                existing = await self.fetchone('SELECT * FROM poll_votes WHERE poll_id = ? AND user_id = ?', (poll_id, user_id))
                if existing:
                    return False
            await self.execute('INSERT INTO poll_votes (poll_id, user_id, option_index) VALUES (?, ?, ?)', (poll_id, user_id, option_index))
            return True
        except Exception as e:
            bot_logger.database_error('vote_poll', str(e))
            return False

    async def get_poll_votes(self, poll_id: int) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM poll_votes WHERE poll_id = ?', (poll_id,))
        except Exception:
            return []

    # ==================== Invites ====================

    async def record_invite(self, guild_id: str, user_id: str, inviter_id: Optional[str] = None):
        try:
            await self.execute('INSERT INTO invites (guild_id, user_id, inviter_id) VALUES (?, ?, ?)', (guild_id, user_id, inviter_id))
        except Exception as e:
            bot_logger.database_error('record_invite', str(e))

    async def get_invites(self, guild_id: str) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM invites WHERE guild_id = ? ORDER BY created_at DESC', (guild_id,))
        except Exception:
            return []

    async def add_invite_reward(self, guild_id: str, required_invites: int, role_id: str):
        try:
            await self.execute('INSERT OR REPLACE INTO invite_rewards (guild_id, required_invites, role_id) VALUES (?, ?, ?)', (guild_id, required_invites, role_id))
        except Exception as e:
            bot_logger.database_error('add_invite_reward', str(e))

    async def get_invite_rewards(self, guild_id: str) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM invite_rewards WHERE guild_id = ?', (guild_id,))
        except Exception:
            return []

    # ==================== Stats ====================

    async def increment_stat(self, guild_id: str, stat_name: str, amount: int = 1):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            row = await self.fetchone('SELECT * FROM stats WHERE guild_id = ? AND date = ?', (guild_id, today))
            if row:
                await self.execute(f'UPDATE stats SET {stat_name} = {stat_name} + ? WHERE guild_id = ? AND date = ?', (amount, guild_id, today))
            else:
                await self.execute(f'INSERT INTO stats (guild_id, date, {stat_name}) VALUES (?, ?, ?)', (guild_id, today, amount))
        except Exception as e:
            bot_logger.database_error('increment_stat', str(e))

    async def get_stats(self, guild_id: str, days: int = 7) -> List[Dict]:
        try:
            rows = await self.fetchall('SELECT date, messages, joins, leaves, voice_minutes FROM stats WHERE guild_id = ? ORDER BY date DESC LIMIT ?', (guild_id, days))
            return list(reversed(rows))
        except Exception as e:
            bot_logger.database_error('get_stats', str(e))
            return []

    # ==================== Logs ====================

    async def add_log(
        self,
        guild_id: str,
        action_type: str,
        user_id: Optional[str] = None,
        moderator_id: Optional[str] = None,
        target_id: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[str] = None
    ):
        try:
            await self.execute(
                'INSERT INTO logs (guild_id, action_type, user_id, moderator_id, target_id, reason, details) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (guild_id, action_type, user_id, moderator_id, target_id, reason, details)
            )
        except Exception as e:
            bot_logger.database_error('add_log', str(e))

    # ==================== Blacklist ====================

    async def get_blacklist_words(self, guild_id: str) -> List[Dict]:
        try:
            return await self.fetchall('SELECT * FROM blacklist_words WHERE guild_id = ? AND enabled = 1', (guild_id,))
        except Exception:
            return []

    # ==================== Lists ====================

    async def is_in_list(self, guild_id: str, user_id: str, list_type: str) -> bool:
        try:
            row = await self.fetchone('SELECT 1 FROM lists WHERE guild_id = ? AND user_id = ? AND list_type = ?', (guild_id, user_id, list_type))
            return row is not None
        except Exception:
            return False


# Global instance
db = Database()