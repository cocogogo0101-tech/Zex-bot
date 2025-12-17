"""
نظام قاعدة البيانات الشامل - SQLite
✅ تم إصلاح جميع الجداول الناقصة
✅ تم إضافة logging
✅ تم تحسين error handling
"""

import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import asyncio
from logger import bot_logger

DB_PATH = 'database.db'

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            await self.create_tables()
            bot_logger.success('قاعدة البيانات متصلة بنجاح')
        except Exception as e:
            bot_logger.exception('فشل الاتصال بقاعدة البيانات', e)
            raise

    async def close(self):
        """إغلاق الاتصال"""
        if self.conn:
            try:
                await self.conn.close()
                bot_logger.info('تم إغلاق قاعدة البيانات')
            except Exception as e:
                bot_logger.error(f'خطأ في إغلاق قاعدة البيانات: {e}')

    async def create_tables(self):
        """إنشاء جميع الجداول - مُصلح ومُحسّن"""
        try:
            # تفعيل مفاتيح الارتباط الخارجية في SQLite
            try:
                await self.conn.execute('PRAGMA foreign_keys = ON;')
            except Exception:
                pass

            # جدول الإعدادات
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

            # جدول التحذيرات
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

            # جدول التكتات
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

            # جدول المستويات
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

            # ✅ جدول إعدادات المستويات (جديد - كان ناقص!)
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

            # ✅ جدول مضاعفات الأدوار (جديد - كان ناقص!)
            await self.conn.execute('''
                CREATE TABLE IF NOT EXISTS leveling_role_multipliers (
                    guild_id TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    multiplier REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, role_id)
                )
            ''')

            # جدول الردود التلقائية
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

            # جدول الكلمات المحظورة
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

            # جدول السجلات
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

            # جدول الملاحظات
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

            # جدول القوائم (Blacklist/Whitelist)
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

            # جدول الإحصائيات
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

            # جدول التذكيرات
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

            # ==================== جداول الدعوات والاستطلاعات (المطلوبة) ====================

            # ✅ جدول الدعوات (جديد - كان ناقص!)
            await self.conn.execute('''
                CREATE TABLE IF NOT EXISTS invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    inviter_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # ✅ جدول مكافآت الدعوات (جديد - كان ناقص!)
            await self.conn.execute('''
                CREATE TABLE IF NOT EXISTS invite_rewards (
                    guild_id TEXT NOT NULL,
                    required_invites INTEGER NOT NULL,
                    role_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, required_invites)
                )
            ''')

            # ✅ جدول الاستطلاعات (جديد!)
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

            # ✅ جدول أصوات الاستطلاعات (جديد!)
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

            await self.conn.commit()
            bot_logger.success('جميع الجداول جاهزة ✅')

        except Exception as e:
            bot_logger.exception('فشل إنشاء الجداول', e)
            raise

    # ==================== الإعدادات ====================

    async def get_settings(self, guild_id: str) -> Optional[Dict]:
        """الحصول على إعدادات السيرفر"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM settings WHERE guild_id = ?',
                (guild_id,)
            )
            row = await cursor.fetchone()
            bot_logger.database_query('SELECT', 'settings', row is not None)
            return dict(row) if row else None
        except Exception as e:
            bot_logger.database_error('get_settings', str(e))
            return None

    async def update_setting(self, guild_id: str, key: str, value: Any):
        """تحديث إعداد معين"""
        try:
            settings = await self.get_settings(guild_id)

            if not settings:
                await self.conn.execute(
                    f'INSERT INTO settings (guild_id, {key}) VALUES (?, ?)',
                    (guild_id, value)
                )
            else:
                await self.conn.execute(
                    f'UPDATE settings SET {key} = ? WHERE guild_id = ?',
                    (value, guild_id)
                )
            await self.conn.commit()
            bot_logger.database_query('UPDATE', 'settings', True)
        except Exception as e:
            bot_logger.database_error(f'update_setting: {key}', str(e))
            raise

    async def init_guild(self, guild_id: str):
        """تهيئة إعدادات السيرفر"""
        try:
            exists = await self.get_settings(guild_id)
            if not exists:
                await self.conn.execute(
                    'INSERT INTO settings (guild_id) VALUES (?)',
                    (guild_id,)
                )
                await self.conn.commit()
                bot_logger.info(f'تهيئة إعدادات السيرفر: {guild_id}')
        except Exception as e:
            bot_logger.database_error('init_guild', str(e))

    # ==================== التحذيرات ====================

    async def add_warning(self, guild_id: str, user_id: str, moderator_id: str, reason: str = None) -> int:
        """إضافة تحذير"""
        try:
            cursor = await self.conn.execute(
                'INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)',
                (guild_id, user_id, moderator_id, reason)
            )
            await self.conn.commit()
            bot_logger.database_query('INSERT', 'warnings', True)
            return cursor.lastrowid
        except Exception as e:
            bot_logger.database_error('add_warning', str(e))
            return 0

    async def get_warnings(self, guild_id: str, user_id: str) -> List[Dict]:
        """الحصول على تحذيرات العضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC',
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_warnings', str(e))
            return []

    async def remove_warning(self, warning_id: int) -> bool:
        """إزالة تحذير"""
        try:
            cursor = await self.conn.execute(
                'DELETE FROM warnings WHERE id = ?',
                (warning_id,)
            )
            await self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            bot_logger.database_error('remove_warning', str(e))
            return False

    async def clear_warnings(self, guild_id: str, user_id: str):
        """مسح جميع تحذيرات العضو"""
        try:
            await self.conn.execute(
                'DELETE FROM warnings WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            await self.conn.commit()
            bot_logger.database_query('DELETE', 'warnings', True)
        except Exception as e:
            bot_logger.database_error('clear_warnings', str(e))

    async def get_warning_count(self, guild_id: str, user_id: str) -> int:
        """عدد تحذيرات العضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            bot_logger.database_error('get_warning_count', str(e))
            return 0

    # ==================== التكتات ====================

    async def create_ticket(self, channel_id: str, guild_id: str, opener_id: str, reason: str = None):
        """إنشاء تكت"""
        try:
            await self.conn.execute(
                'INSERT INTO tickets (channel_id, guild_id, opener_id, reason) VALUES (?, ?, ?, ?)',
                (channel_id, guild_id, opener_id, reason)
            )
            await self.conn.commit()
            bot_logger.database_query('INSERT', 'tickets', True)
        except Exception as e:
            bot_logger.database_error('create_ticket', str(e))

    async def get_ticket(self, channel_id: str) -> Optional[Dict]:
        """الحصول على معلومات التكت"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM tickets WHERE channel_id = ?',
                (channel_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            bot_logger.database_error('get_ticket', str(e))
            return None

    async def close_ticket(self, channel_id: str, closed_by: str):
        """إغلاق تكت"""
        try:
            await self.conn.execute(
                'UPDATE tickets SET status = ?, closed_at = ?, closed_by = ? WHERE channel_id = ?',
                ('closed', datetime.now().isoformat(), closed_by, channel_id)
            )
            await self.conn.commit()
            bot_logger.database_query('UPDATE', 'tickets', True)
        except Exception as e:
            bot_logger.database_error('close_ticket', str(e))

    async def get_user_tickets(self, guild_id: str, user_id: str) -> List[Dict]:
        """الحصول على تكتات العضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM tickets WHERE guild_id = ? AND opener_id = ? ORDER BY created_at DESC',
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_user_tickets', str(e))
            return []

    # ==================== المستويات ====================

    async def add_xp(self, guild_id: str, user_id: str, xp: int) -> Dict:
        """إضافة XP للعضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM levels WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            row = await cursor.fetchone()

            if row:
                data = dict(row)
                new_xp = data['xp'] + xp
                new_level = int(new_xp ** 0.5) // 10
                new_messages = data['messages'] + 1

                await self.conn.execute(
                    'UPDATE levels SET xp = ?, level = ?, messages = ?, last_xp_time = ? WHERE guild_id = ? AND user_id = ?',
                    (new_xp, new_level, new_messages, datetime.now().isoformat(), guild_id, user_id)
                )
                await self.conn.commit()

                return {
                    'xp': new_xp,
                    'level': new_level,
                    'old_level': data['level'],
                    'leveled_up': new_level > data['level']
                }
            else:
                await self.conn.execute(
                    'INSERT INTO levels (guild_id, user_id, xp, level, messages, last_xp_time) VALUES (?, ?, ?, ?, ?, ?)',
                    (guild_id, user_id, xp, 0, 1, datetime.now().isoformat())
                )
                await self.conn.commit()
                return {'xp': xp, 'level': 0, 'old_level': 0, 'leveled_up': False}
        except Exception as e:
            bot_logger.database_error('add_xp', str(e))
            return {'xp': 0, 'level': 0, 'old_level': 0, 'leveled_up': False}

    async def get_level(self, guild_id: str, user_id: str) -> Optional[Dict]:
        """الحصول على مستوى العضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM levels WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            bot_logger.database_error('get_level', str(e))
            return None

    async def get_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict]:
        """لوحة الصدارة"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?',
                (guild_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_leaderboard', str(e))
            return []

    # ==================== الردود التلقائية ====================

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
        """إضافة رد تلقائي. يعيد الـ id (0 إن فشل)."""
        try:
            cursor = await self.conn.execute(
                'INSERT INTO autoresponses '
                '(guild_id, trigger, response, trigger_type, enabled, chance, cooldown, channels) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (guild_id, trigger, response, trigger_type, enabled, chance, cooldown, channels)
            )
            await self.conn.commit()
            bot_logger.database_query('INSERT', 'autoresponses', True)
            return cursor.lastrowid or 0
        except Exception as e:
            bot_logger.database_error('add_autoresponse', str(e))
            return 0

    async def get_autoresponses(self, guild_id: str) -> List[Dict[str, Any]]:
        """جلب كل الردود التلقائية للسيرفر (قائمة قواميس)."""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM autoresponses WHERE guild_id = ? ORDER BY id ASC',
                (guild_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            bot_logger.database_error('get_autoresponses', str(e))
            return []

    async def remove_autoresponse(self, ar_id: int) -> bool:
        """حذف رد تلقائي حسب الـ id."""
        try:
            cursor = await self.conn.execute(
                'DELETE FROM autoresponses WHERE id = ?',
                (ar_id,)
            )
            await self.conn.commit()
            return True
        except Exception as e:
            bot_logger.database_error('remove_autoresponse', str(e))
            return False

    async def toggle_autoresponse(self, ar_id: int) -> bool:
        """تبديل حالة (enabled) لرد تلقائي. يعيد الحالة الجديدة (True=enabled)."""
        try:
            cur = await self.conn.execute('SELECT enabled FROM autoresponses WHERE id = ?', (ar_id,))
            row = await cur.fetchone()
            if not row:
                return False
            current = row[0]
            new = 0 if (current == 1 or current == True) else 1
            await self.conn.execute('UPDATE autoresponses SET enabled = ? WHERE id = ?', (new, ar_id))
            await self.conn.commit()
            return bool(new)
        except Exception as e:
            bot_logger.database_error('toggle_autoresponse', str(e))
            return False

    async def update_autoresponse(self, ar_id: int, **fields) -> bool:
        """
        تعديل حقول الرد التلقائي.
        مقبول الحقول: trigger, response, trigger_type, enabled, chance, cooldown, channels, last_used
        """
        allowed = {'trigger', 'response', 'trigger_type', 'enabled', 'chance', 'cooldown', 'channels', 'last_used'}
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return False
        params.append(ar_id)
        sql = f"UPDATE autoresponses SET {', '.join(updates)} WHERE id = ?"
        try:
            await self.conn.execute(sql, tuple(params))
            await self.conn.commit()
            return True
        except Exception as e:
            bot_logger.database_error('update_autoresponse', str(e))
            return False

    async def search_autoresponses(self, guild_id: str, query: str) -> List[Dict[str, Any]]:
        """بحث في المحفز أو الرد بواسطة LIKE."""
        try:
            q = f"%{query}%"
            cursor = await self.conn.execute(
                'SELECT * FROM autoresponses WHERE guild_id = ? AND (trigger LIKE ? OR response LIKE ?) ORDER BY id ASC',
                (guild_id, q, q)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            bot_logger.database_error('search_autoresponses', str(e))
            return []

    async def get_autoresponse_stats(self, guild_id: str) -> Dict[str, Any]:
        """إحصائيات بسيطة: total, enabled, disabled, by_type dict."""
        try:
            cur = await self.conn.execute('SELECT COUNT(*) FROM autoresponses WHERE guild_id = ?', (guild_id,))
            total_row = await cur.fetchone()
            total = total_row[0] if total_row else 0

            cur = await self.conn.execute('SELECT COUNT(*) FROM autoresponses WHERE guild_id = ? AND enabled = 1', (guild_id,))
            enabled_row = await cur.fetchone()
            enabled = enabled_row[0] if enabled_row else 0

            disabled = total - enabled

            cur = await self.conn.execute(
                'SELECT trigger_type, COUNT(*) as cnt FROM autoresponses WHERE guild_id = ? GROUP BY trigger_type',
                (guild_id,)
            )
            rows = await cur.fetchall()
            by_type = {r[0]: r[1] for r in rows} if rows else {}

            return {'total': total, 'enabled': enabled, 'disabled': disabled, 'by_type': by_type}
        except Exception as e:
            bot_logger.database_error('get_autoresponse_stats', str(e))
            return {'total': 0, 'enabled': 0, 'disabled': 0, 'by_type': {}}

    # ==================== الإحصائيات اليومية (stats) ====================
    async def increment_stat(self, guild_id: str, stat_name: str, amount: int = 1):
        """
        زيادة إحصائية معينة

        Args:
            guild_id: معرف السيرفر
            stat_name: اسم الإحصائية (messages, joins, leaves, voice_minutes)
            amount: المقدار (افتراضي: 1)
        """
        try:
            # الحصول على التاريخ الحالي
            today = datetime.now().strftime('%Y-%m-%d')

            # التحقق من وجود سجل لليوم
            cursor = await self.conn.execute(
                'SELECT * FROM stats WHERE guild_id = ? AND date = ?',
                (guild_id, today)
            )
            row = await cursor.fetchone()

            if row:
                # تحديث السجل الموجود
                await self.conn.execute(
                    f'UPDATE stats SET {stat_name} = {stat_name} + ? WHERE guild_id = ? AND date = ?',
                    (amount, guild_id, today)
                )
            else:
                # إنشاء سجل جديد
                await self.conn.execute(
                    f'INSERT INTO stats (guild_id, date, {stat_name}) VALUES (?, ?, ?)',
                    (guild_id, today, amount)
                )

            await self.conn.commit()
            bot_logger.database_query('UPDATE', 'stats', True)

        except Exception as e:
            bot_logger.database_error(f'increment_stat: {stat_name}', str(e))

    async def get_stats(self, guild_id: str, days: int = 7) -> List[Dict]:
        """
        الحصول على إحصائيات السيرفر لعدة أيام

        Args:
            guild_id: معرف السيرفر
            days: عدد الأيام (افتراضي: 7)

        Returns:
            قائمة الإحصائيات
        """
        try:
            cursor = await self.conn.execute('''
            SELECT date, messages, joins, leaves, voice_minutes
            FROM stats
            WHERE guild_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (guild_id, days))

            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]  # ترتيب تصاعدي

        except Exception as e:
            bot_logger.database_error('get_stats', str(e))
            return []

# إنشاء نسخة عامة
db = Database()
```0