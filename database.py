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

    async def add_autoresponse(self, guild_id: str, trigger: str, response: str, 
                               trigger_type: str = 'contains', channels: List[str] = None) -> int:
        """إضافة رد تلقائي"""
        try:
            channels_json = json.dumps(channels) if channels else None
            cursor = await self.conn.execute(
                'INSERT INTO autoresponses (guild_id, trigger, response, trigger_type, channels) VALUES (?, ?, ?, ?, ?)',
                (guild_id, trigger, response, trigger_type, channels_json)
            )
            await self.conn.commit()
            bot_logger.database_query('INSERT', 'autoresponses', True)
            return cursor.lastrowid
        except Exception as e:
            bot_logger.database_error('add_autoresponse', str(e))
            return 0

    async def get_autoresponses(self, guild_id: str) -> List[Dict]:
        """الحصول على جميع الردود التلقائية"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM autoresponses WHERE guild_id = ? AND enabled = 1',
                (guild_id,)
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                data = dict(row)
                if data['channels']:
                    try:
                        data['channels'] = json.loads(data['channels'])
                    except:
                        data['channels'] = None
                results.append(data)
            return results
        except Exception as e:
            bot_logger.database_error('get_autoresponses', str(e))
            return []

    async def remove_autoresponse(self, response_id: int) -> bool:
        """حذف رد تلقائي"""
        try:
            cursor = await self.conn.execute(
                'DELETE FROM autoresponses WHERE id = ?',
                (response_id,)
            )
            await self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            bot_logger.database_error('remove_autoresponse', str(e))
            return False

    async def toggle_autoresponse(self, response_id: int) -> bool:
        """تفعيل/تعطيل رد تلقائي"""
        try:
            cursor = await self.conn.execute(
                'SELECT enabled FROM autoresponses WHERE id = ?',
                (response_id,)
            )
            row = await cursor.fetchone()
            if row:
                new_state = 0 if row[0] == 1 else 1
                await self.conn.execute(
                    'UPDATE autoresponses SET enabled = ? WHERE id = ?',
                    (new_state, response_id)
                )
                await self.conn.commit()
                return True
            return False
        except Exception as e:
            bot_logger.database_error('toggle_autoresponse', str(e))
            return False

    # ==================== الكلمات المحظورة ====================

    async def add_blacklist_word(self, guild_id: str, word: str, action: str = 'delete'):
        """إضافة كلمة محظورة"""
        try:
            await self.conn.execute(
                'INSERT INTO blacklist_words (guild_id, word, action) VALUES (?, ?, ?)',
                (guild_id, word.lower(), action)
            )
            await self.conn.commit()
            bot_logger.database_query('INSERT', 'blacklist_words', True)
        except Exception as e:
            bot_logger.database_error('add_blacklist_word', str(e))

    async def get_blacklist_words(self, guild_id: str) -> List[Dict]:
        """الحصول على الكلمات المحظورة"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM blacklist_words WHERE guild_id = ? AND enabled = 1',
                (guild_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_blacklist_words', str(e))
            return []

    async def remove_blacklist_word(self, word_id: int):
        """حذف كلمة محظورة"""
        try:
            await self.conn.execute(
                'DELETE FROM blacklist_words WHERE id = ?',
                (word_id,)
            )
            await self.conn.commit()
            bot_logger.database_query('DELETE', 'blacklist_words', True)
        except Exception as e:
            bot_logger.database_error('remove_blacklist_word', str(e))

    # ==================== السجلات ====================

    async def add_log(self, guild_id: str, action_type: str, user_id: str = None,
                     moderator_id: str = None, target_id: str = None, 
                     reason: str = None, details: str = None):
        """إضافة سجل"""
        try:
            await self.conn.execute(
                'INSERT INTO logs (guild_id, action_type, user_id, moderator_id, target_id, reason, details) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (guild_id, action_type, user_id, moderator_id, target_id, reason, details)
            )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('add_log', str(e))

    async def get_logs(self, guild_id: str, limit: int = 50, action_type: str = None) -> List[Dict]:
        """الحصول على السجلات"""
        try:
            if action_type:
                cursor = await self.conn.execute(
                    'SELECT * FROM logs WHERE guild_id = ? AND action_type = ? ORDER BY created_at DESC LIMIT ?',
                    (guild_id, action_type, limit)
                )
            else:
                cursor = await self.conn.execute(
                    'SELECT * FROM logs WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?',
                    (guild_id, limit)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_logs', str(e))
            return []

    # ==================== الملاحظات ====================

    async def add_note(self, guild_id: str, user_id: str, moderator_id: str, note: str) -> int:
        """إضافة ملاحظة"""
        try:
            cursor = await self.conn.execute(
                'INSERT INTO notes (guild_id, user_id, moderator_id, note) VALUES (?, ?, ?, ?)',
                (guild_id, user_id, moderator_id, note)
            )
            await self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            bot_logger.database_error('add_note', str(e))
            return 0

    async def get_notes(self, guild_id: str, user_id: str) -> List[Dict]:
        """الحصول على ملاحظات العضو"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM notes WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC',
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_notes', str(e))
            return []

    async def remove_note(self, note_id: int):
        """حذف ملاحظة"""
        try:
            await self.conn.execute(
                'DELETE FROM notes WHERE id = ?',
                (note_id,)
            )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('remove_note', str(e))

    # ==================== القوائم ====================

    async def add_to_list(self, guild_id: str, user_id: str, list_type: str, reason: str = None):
        """إضافة عضو لقائمة"""
        try:
            await self.conn.execute(
                'INSERT OR REPLACE INTO lists (guild_id, user_id, list_type, reason) VALUES (?, ?, ?, ?)',
                (guild_id, user_id, list_type, reason)
            )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('add_to_list', str(e))

    async def remove_from_list(self, guild_id: str, user_id: str, list_type: str):
        """إزالة عضو من قائمة"""
        try:
            await self.conn.execute(
                'DELETE FROM lists WHERE guild_id = ? AND user_id = ? AND list_type = ?',
                (guild_id, user_id, list_type)
            )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('remove_from_list', str(e))

    async def is_in_list(self, guild_id: str, user_id: str, list_type: str) -> bool:
        """التحقق إذا كان العضو في قائمة"""
        try:
            cursor = await self.conn.execute(
                'SELECT 1 FROM lists WHERE guild_id = ? AND user_id = ? AND list_type = ?',
                (guild_id, user_id, list_type)
            )
            return await cursor.fetchone() is not None
        except Exception as e:
            bot_logger.database_error('is_in_list', str(e))
            return False

    # ==================== الإحصائيات ====================

    async def increment_stat(self, guild_id: str, stat_type: str, amount: int = 1):
        """زيادة إحصائية"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')

            cursor = await self.conn.execute(
                'SELECT * FROM stats WHERE guild_id = ? AND date = ?',
                (guild_id, today)
            )
            row = await cursor.fetchone()

            if row:
                await self.conn.execute(
                    f'UPDATE stats SET {stat_type} = {stat_type} + ? WHERE guild_id = ? AND date = ?',
                    (amount, guild_id, today)
                )
            else:
                await self.conn.execute(
                    f'INSERT INTO stats (guild_id, date, {stat_type}) VALUES (?, ?, ?)',
                    (guild_id, today, amount)
                )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('increment_stat', str(e))

    async def get_stats(self, guild_id: str, days: int = 7) -> List[Dict]:
        """الحصول على الإحصائيات"""
        try:
            cursor = await self.conn.execute(
                'SELECT * FROM stats WHERE guild_id = ? ORDER BY date DESC LIMIT ?',
                (guild_id, days)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_stats', str(e))
            return []

    # ==================== التذكيرات ====================

    async def add_reminder(self, guild_id: str, user_id: str, channel_id: str, message: str, remind_at: datetime) -> int:
        """إضافة تذكير"""
        try:
            cursor = await self.conn.execute(
                'INSERT INTO reminders (guild_id, user_id, channel_id, message, remind_at) VALUES (?, ?, ?, ?, ?)',
                (guild_id, user_id, channel_id, message, remind_at.isoformat())
            )
            await self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            bot_logger.database_error('add_reminder', str(e))
            return 0

    async def get_due_reminders(self) -> List[Dict]:
        """الحصول على التذكيرات المستحقة"""
        try:
            now = datetime.now().isoformat()
            cursor = await self.conn.execute(
                'SELECT * FROM reminders WHERE remind_at <= ?',
                (now,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            bot_logger.database_error('get_due_reminders', str(e))
            return []

    async def delete_reminder(self, reminder_id: int):
        """حذف تذكير"""
        try:
            await self.conn.execute(
                'DELETE FROM reminders WHERE id = ?',
                (reminder_id,)
            )
            await self.conn.commit()
        except Exception as e:
            bot_logger.database_error('delete_reminder', str(e))

# إنشاء نسخة عامة
db = Database()