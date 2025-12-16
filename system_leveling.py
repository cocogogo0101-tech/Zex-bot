"""
system_leveling.py - Ultimate Version
======================================
نظام المستويات والخبرة المتقدم والشامل

Features:
✅ XP من الرسائل (قابل للتخصيص)
✅ XP من الصوت (Active vs AFK)
✅ Role Multipliers
✅ Level Rewards (أدوار تلقائية)
✅ Leaderboard متقدم
✅ Level curves قابلة للتخصيص
✅ Anti-spam للـ XP
✅ Cooldowns ذكية
✅ Boost multipliers
✅ Voice tracking دقيق
"""

import discord
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from collections import defaultdict
from database import db
from config_manager import config
import embeds
import json
from logger import bot_logger


# ==================== Constants ====================

DEFAULT_XP_RANGE = (15, 25)
DEFAULT_COOLDOWN = 60  # ثانية
DEFAULT_VOICE_XP = 1  # XP لكل دقيقة

# منحنى المستويات الافتراضي
def default_level_curve(level: int) -> int:
    """حساب XP المطلوب للمستوى"""
    return (level * 100) + ((level - 1) * 50 * level)


# ==================== Level Calculator ====================

class LevelCalculator:
    """آلة حاسبة المستويات المتقدمة"""

    def __init__(self):
        self.curve_cache: Dict[str, List[int]] = {}

    def generate_curve(self, max_level: int = 100, formula: str = 'default') -> List[int]:
        """
        توليد منحنى المستويات

        Args:
            max_level: أقصى مستوى
            formula: صيغة الحساب

        Returns:
            قائمة XP لكل مستوى
        """
        curve = [0]  # Level 0 = 0 XP

        if formula == 'linear':
            # منحنى خطي: كل مستوى يحتاج نفس الـ XP
            base = 100
            for level in range(1, max_level + 1):
                curve.append(curve[-1] + base)

        elif formula == 'exponential':
            # منحنى أسي: يصعب كلما ارتفع المستوى
            base = 100
            multiplier = 1.1
            for level in range(1, max_level + 1):
                xp_needed = int(base * (multiplier ** (level - 1)))
                curve.append(curve[-1] + xp_needed)

        elif formula == 'logarithmic':
            # منحنى لوغاريتمي: يسهل كلما ارتفع المستوى
            import math
            base = 500
            for level in range(1, max_level + 1):
                xp_needed = int(base * math.log(level + 1))
                curve.append(curve[-1] + xp_needed)

        else:  # default
            for level in range(1, max_level + 1):
                curve.append(default_level_curve(level))

        return curve

    def calculate_level(self, xp: int, curve: List[int]) -> int:
        """
        حساب المستوى من XP

        Args:
            xp: XP الحالي
            curve: منحنى المستويات

        Returns:
            المستوى
        """
        for level, required_xp in enumerate(curve):
            if xp < required_xp:
                return max(0, level - 1)

        return len(curve) - 1

    def xp_for_level(self, level: int, curve: List[int]) -> int:
        """XP المطلوب للوصول لمستوى"""
        if level < len(curve):
            return curve[level]
        return curve[-1]

    def xp_to_next_level(self, current_xp: int, current_level: int, curve: List[int]) -> Tuple[int, int, int]:
        """
        حساب XP المتبقي للمستوى التالي

        Returns:
            (xp_needed, xp_progress, xp_total)
        """
        if current_level >= len(curve) - 1:
            return 0, 0, 0

        current_level_xp = curve[current_level]
        next_level_xp = curve[current_level + 1]

        xp_progress = current_xp - current_level_xp
        xp_total = next_level_xp - current_level_xp
        xp_needed = xp_total - xp_progress

        return xp_needed, xp_progress, xp_total


# ==================== Voice Tracker ====================

class VoiceTracker:
    """تتبع الوقت في القنوات الصوتية"""

    def __init__(self):
        # {guild_id: {user_id: {'join_time': datetime, 'speaking': bool}}}
        self.sessions: Dict[str, Dict[str, Dict]] = defaultdict(dict)

    def start_session(self, guild_id: str, user_id: str):
        """بدء جلسة صوتية"""
        self.sessions[guild_id][user_id] = {
            'join_time': datetime.now(),
            'speaking': False,
            'total_xp': 0
        }
        bot_logger.debug(f'بدء جلسة صوتية: {user_id} في {guild_id}')

    def end_session(self, guild_id: str, user_id: str) -> Tuple[int, int]:
        """
        إنهاء جلسة صوتية

        Returns:
            (duration_minutes, xp_earned)
        """
        if guild_id not in self.sessions or user_id not in self.sessions[guild_id]:
            return 0, 0

        session = self.sessions[guild_id][user_id]
        duration = (datetime.now() - session['join_time']).total_seconds()
        minutes = int(duration / 60)

        # حساب XP
        # إذا كان يتحدث: 2 XP/دقيقة
        # إذا كان AFK: 1 XP/دقيقة
        xp_per_minute = 2 if session['speaking'] else 1
        xp = minutes * xp_per_minute + session['total_xp']

        del self.sessions[guild_id][user_id]

        bot_logger.debug(f'انتهاء جلسة صوتية: {user_id} - {minutes} دقيقة - {xp} XP')
        return minutes, xp

    def update_speaking(self, guild_id: str, user_id: str, speaking: bool):
        """تحديث حالة التحدث"""
        if guild_id in self.sessions and user_id in self.sessions[guild_id]:
            self.sessions[guild_id][user_id]['speaking'] = speaking

    def add_xp(self, guild_id: str, user_id: str, xp: int):
        """إضافة XP للجلسة الحالية"""
        if guild_id in self.sessions and user_id in self.sessions[guild_id]:
            self.sessions[guild_id][user_id]['total_xp'] += xp

    def is_in_voice(self, guild_id: str, user_id: str) -> bool:
        """التحقق إذا كان في صوت"""
        return guild_id in self.sessions and user_id in self.sessions[guild_id]


# ==================== Leveling System ====================

class LevelingSystem:
    """نظام المستويات الشامل والمتقدم"""

    def __init__(self):
        self.calculator = LevelCalculator()
        self.voice_tracker = VoiceTracker()
        self.message_cooldowns: Dict[str, datetime] = {}  # {user_id: last_xp_time}
        self.role_multipliers_cache: Dict[str, Dict[int, float]] = {}  # {guild_id: {role_id: multiplier}}

    # ==================== Message XP ====================

    async def process_message(self, message: discord.Message) -> Optional[Dict]:
        """
        معالجة رسالة وإضافة XP

        Returns:
            معلومات الترقية إن حدثت أو None
        """
        if message.author.bot or not message.guild:
            return None

        # التحقق من تفعيل النظام
        leveling_config = await config.get_leveling_config(str(message.guild.id))
        if not leveling_config.enabled:
            return None

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        # التحقق من Cooldown
        cooldown_key = f'{guild_id}:{user_id}'
        if cooldown_key in self.message_cooldowns:
            last_time = self.message_cooldowns[cooldown_key]
            if (datetime.now() - last_time).total_seconds() < leveling_config.cooldown:
                return None

        # حساب XP
        base_xp = random.randint(leveling_config.xp_min, leveling_config.xp_max)

        # مضاعف الأدوار
        multiplier = await self.get_role_multiplier(message.author)

        # مضاعف Boost
        if message.guild.premium_subscriber_role in message.author.roles:
            multiplier *= 1.5

        xp_gained = int(base_xp * multiplier)

        # تحديث Cooldown
        self.message_cooldowns[cooldown_key] = datetime.now()

        # إضافة XP
        result = await self.add_xp(guild_id, user_id, xp_gained)

        # إذا حصلت ترقية
        if result['leveled_up']:
            await self._handle_level_up(message, result)

            # منح أدوار المستوى
            await self._grant_level_roles(message.author, result['level'])

            return result

        return None

    async def _handle_level_up(self, message: discord.Message, result: Dict):
        """معالجة ترقية المستوى"""
        leveling_config = await config.get_leveling_config(str(message.guild.id))

        if not leveling_config.announce_levelup:
            return

        # تحديد القناة
        if leveling_config.levelup_channel:
            channel = message.guild.get_channel(int(leveling_config.levelup_channel))
            if not channel:
                channel = message.channel
        else:
            channel = message.channel

        # إرسال رسالة الترقية
        try:
            embed = embeds.level_up_embed(message.author, result['level'])
            await channel.send(embed=embed, delete_after=10)

            bot_logger.info(f'ترقية مستوى: {message.author.name} -> المستوى {result["level"]}')
        except discord.Forbidden:
            pass
        except discord.HTTPException as e:
            bot_logger.error(f'خطأ في إرسال رسالة الترقية: {e}')

    async def _grant_level_roles(self, member: discord.Member, level: int):
        """منح أدوار المستوى التلقائية"""
        leveling_config = await config.get_leveling_config(str(member.guild.id))

        if not leveling_config.level_roles:
            return

        # التحقق من الأدوار المطلوبة
        for req_level, role_id in leveling_config.level_roles.items():
            if level >= req_level:
                role = member.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f'وصل للمستوى {level}')
                        bot_logger.info(f'منح دور المستوى: {member.name} -> {role.name}')
                    except discord.Forbidden:
                        bot_logger.warning(f'لا يمكن منح دور المستوى لـ {member.name}')

    # ==================== Voice XP ====================

    async def handle_voice_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """معالجة انضمام لقناة صوتية"""
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        # التحقق من تفعيل النظام
        leveling_config = await config.get_leveling_config(guild_id)
        if not leveling_config.enabled:
            return

        self.voice_tracker.start_session(guild_id, user_id)

    async def handle_voice_leave(self, member: discord.Member):
        """معالجة مغادرة قناة صوتية"""
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        # التحقق من تفعيل النظام
        leveling_config = await config.get_leveling_config(guild_id)
        if not leveling_config.enabled:
            return

        # إنهاء الجلسة وحساب XP
        minutes, xp = self.voice_tracker.end_session(guild_id, user_id)

        if xp > 0:
            result = await self.add_xp(guild_id, user_id, xp)

            if result['leveled_up']:
                # إرسال DM بالترقية
                try:
                    embed = embeds.level_up_embed(member, result['level'])
                    await member.send(embed=embed)
                except:
                    pass

    async def update_speaking_status(self, member: discord.Member, is_speaking: bool):
        """تحديث حالة التحدث"""
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        self.voice_tracker.update_speaking(guild_id, user_id, is_speaking)

    # ==================== Core XP Management ====================

    async def add_xp(self, guild_id: str, user_id: str, xp: int) -> Dict:
        """
        إضافة XP للعضو

        Returns:
            {'xp': int, 'level': int, 'old_level': int, 'leveled_up': bool}
        """
        try:
            # جلب البيانات الحالية
            data = await db.get_level(guild_id, user_id)

            if data:
                old_xp = data['xp']
                old_level = data['level']
                new_xp = old_xp + xp
            else:
                old_xp = 0
                old_level = 0
                new_xp = xp

            # حساب المستوى الجديد
            curve = await self.get_level_curve(guild_id)
            new_level = self.calculator.calculate_level(new_xp, curve)

            # حفظ في قاعدة البيانات
            await db.conn.execute('''
                INSERT INTO levels (guild_id, user_id, xp, level, messages, last_xp_time)
                VALUES (?, ?, ?, ?, COALESCE((SELECT messages FROM levels WHERE guild_id = ? AND user_id = ?), 0) + 1, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    xp = xp + ?,
                    level = ?,
                    messages = messages + 1,
                    last_xp_time = ?
            ''', (guild_id, user_id, xp, new_level, guild_id, user_id, datetime.now().isoformat(),
                  xp, new_level, datetime.now().isoformat()))
            await db.conn.commit()

            return {
                'xp': new_xp,
                'level': new_level,
                'old_level': old_level,
                'leveled_up': new_level > old_level
            }

        except Exception as e:
            bot_logger.exception(f'خطأ في add_xp: {guild_id}:{user_id}', e)
            return {'xp': 0, 'level': 0, 'old_level': 0, 'leveled_up': False}

    async def set_xp(self, guild_id: str, user_id: str, xp: int) -> bool:
        """تعيين XP مباشرة"""
        try:
            curve = await self.get_level_curve(guild_id)
            level = self.calculator.calculate_level(xp, curve)

            await db.conn.execute('''
                INSERT OR REPLACE INTO levels (guild_id, user_id, xp, level, messages, last_xp_time)
                VALUES (?, ?, ?, ?, COALESCE((SELECT messages FROM levels WHERE guild_id = ? AND user_id = ?), 0), ?)
            ''', (guild_id, user_id, xp, level, guild_id, user_id, datetime.now().isoformat()))
            await db.conn.commit()

            return True
        except Exception as e:
            bot_logger.exception(f'خطأ في set_xp: {guild_id}:{user_id}', e)
            return False

    async def remove_xp(self, guild_id: str, user_id: str, xp: int) -> Dict:
        """إزالة XP"""
        try:
            data = await db.get_level(guild_id, user_id)
            if not data:
                return {'xp': 0, 'level': 0}

            new_xp = max(0, data['xp'] - xp)
            curve = await self.get_level_curve(guild_id)
            new_level = self.calculator.calculate_level(new_xp, curve)

            await db.conn.execute('''
                UPDATE levels SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?
            ''', (new_xp, new_level, guild_id, user_id))
            await db.conn.commit()

            return {'xp': new_xp, 'level': new_level}

        except Exception as e:
            bot_logger.exception(f'خطأ في remove_xp: {guild_id}:{user_id}', e)
            return {'xp': 0, 'level': 0}

    # ==================== Queries ====================

    async def get_user_level(self, guild_id: str, user_id: str) -> Optional[Dict]:
        """الحصول على بيانات مستوى العضو"""
        return await db.get_level(guild_id, user_id)

    async def get_user_rank(self, guild_id: str, user_id: str) -> int:
        """الحصول على ترتيب العضو"""
        try:
            leaderboard = await self.get_leaderboard(guild_id, limit=1000)
            for i, entry in enumerate(leaderboard, 1):
                if entry['user_id'] == user_id:
                    return i
            return 0
        except Exception as e:
            bot_logger.error(f'خطأ في get_user_rank: {e}')
            return 0

    async def get_leaderboard(
        self,
        guild_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        الحصول على لوحة الصدارة

        Args:
            guild_id: معرف السيرفر
            limit: عدد النتائج
            offset: البداية

        Returns:
            قائمة الأعضاء
        """
        try:
            cursor = await db.conn.execute('''
                SELECT user_id, xp, level, messages
                FROM levels
                WHERE guild_id = ?
                ORDER BY xp DESC
                LIMIT ? OFFSET ?
            ''', (guild_id, limit, offset))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            bot_logger.exception(f'خطأ في get_leaderboard: {guild_id}', e)
            return []

    # ==================== Level Curve ====================

    async def get_level_curve(self, guild_id: str) -> List[int]:
        """الحصول على منحنى المستويات للسيرفر"""
        try:
            cursor = await db.conn.execute('''
                SELECT level_curve FROM leveling_config WHERE guild_id = ?
            ''', (guild_id,))

            row = await cursor.fetchone()

            if row and row[0]:
                return json.loads(row[0])
            else:
                # توليد منحنى افتراضي
                return self.calculator.generate_curve(max_level=100, formula='default')

        except Exception as e:
            bot_logger.error(f'خطأ في get_level_curve: {e}')
            return self.calculator.generate_curve(max_level=100, formula='default')

    async def set_level_curve(self, guild_id: str, curve: List[int]) -> bool:
        """تعيين منحنى المستويات"""
        try:
            curve_json = json.dumps(curve)

            await db.conn.execute('''
                INSERT INTO leveling_config (guild_id, level_curve)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET level_curve = excluded.level_curve
            ''', (guild_id, curve_json))
            await db.conn.commit()

            return True
        except Exception as e:
            bot_logger.exception(f'خطأ في set_level_curve: {guild_id}', e)
            return False

    # ==================== Role Multipliers ====================

    async def get_role_multiplier(self, member: discord.Member) -> float:
        """الحصول على مضاعف الأدوار للعضو"""
        guild_id = str(member.guild.id)

        # التحقق من Cache
        if guild_id not in self.role_multipliers_cache:
            await self._load_role_multipliers(guild_id)

        multipliers = self.role_multipliers_cache.get(guild_id, {})

        # إيجاد أعلى مضاعف
        max_multiplier = 1.0
        for role in member.roles:
            if role.id in multipliers:
                max_multiplier = max(max_multiplier, multipliers[role.id])

        return max_multiplier

    async def _load_role_multipliers(self, guild_id: str):
        """تحميل مضاعفات الأدوار من DB"""
        try:
            cursor = await db.conn.execute('''
                SELECT role_id, multiplier FROM leveling_role_multipliers WHERE guild_id = ?
            ''', (guild_id,))

            rows = await cursor.fetchall()

            self.role_multipliers_cache[guild_id] = {
                int(row[0]): row[1] for row in rows
            }

        except Exception as e:
            bot_logger.error(f'خطأ في _load_role_multipliers: {e}')
            self.role_multipliers_cache[guild_id] = {}

    async def set_role_multiplier(self, guild_id: str, role_id: int, multiplier: float) -> bool:
        """تعيين مضاعف لدور"""
        try:
            await db.conn.execute('''
                INSERT INTO leveling_role_multipliers (guild_id, role_id, multiplier)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, role_id) DO UPDATE SET multiplier = excluded.multiplier
            ''', (guild_id, str(role_id), multiplier))
            await db.conn.commit()

            # تحديث Cache
            if guild_id in self.role_multipliers_cache:
                self.role_multipliers_cache[guild_id][role_id] = multiplier

            bot_logger.info(f'تم تعيين مضاعف {multiplier}x لدور {role_id} في {guild_id}')
            return True

        except Exception as e:
            bot_logger.exception(f'خطأ في set_role_multiplier: {guild_id}:{role_id}', e)
            return False

    async def remove_role_multiplier(self, guild_id: str, role_id: int) -> bool:
        """إزالة مضاعف دور"""
        try:
            await db.conn.execute('''
                DELETE FROM leveling_role_multipliers WHERE guild_id = ? AND role_id = ?
            ''', (guild_id, str(role_id)))
            await db.conn.commit()

            # تحديث Cache
            if guild_id in self.role_multipliers_cache:
                self.role_multipliers_cache[guild_id].pop(role_id, None)

            return True
        except Exception as e:
            bot_logger.exception(f'خطأ في remove_role_multiplier: {guild_id}:{role_id}', e)
            return False

    # ==================== Admin Commands ====================

    async def reset_user(self, guild_id: str, user_id: str) -> bool:
        """إعادة تعيين بيانات عضو"""
        try:
            await db.conn.execute('''
                DELETE FROM levels WHERE guild_id = ? AND user_id = ?
            ''', (guild_id, user_id))
            await db.conn.commit()

            bot_logger.info(f'تم إعادة تعيين بيانات {user_id} في {guild_id}')
            return True
        except Exception as e:
            bot_logger.exception(f'خطأ في reset_user: {guild_id}:{user_id}', e)
            return False

    async def reset_guild(self, guild_id: str) -> bool:
        """إعادة تعيين بيانات السيرفر بالكامل"""
        try:
            await db.conn.execute('''
                DELETE FROM levels WHERE guild_id = ?
            ''', (guild_id,))
            await db.conn.commit()

            bot_logger.warning(f'تم إعادة تعيين جميع البيانات في {guild_id}')
            return True
        except Exception as e:
            bot_logger.exception(f'خطأ في reset_guild: {guild_id}', e)
            return False

    # ==================== Statistics ====================

    async def get_guild_stats(self, guild_id: str) -> Dict:
        """إحصائيات السيرفر"""
        try:
            cursor = await db.conn.execute('''
                SELECT 
                    COUNT(*) as total_users,
                    SUM(xp) as total_xp,
                    SUM(messages) as total_messages,
                    AVG(level) as avg_level,
                    MAX(level) as max_level
                FROM levels
                WHERE guild_id = ?
            ''', (guild_id,))

            row = await cursor.fetchone()

            if row:
                return {
                    'total_users': row[0] or 0,
                    'total_xp': row[1] or 0,
                    'total_messages': row[2] or 0,
                    'avg_level': round(row[3] or 0, 2),
                    'max_level': row[4] or 0
                }

            return {
                'total_users': 0,
                'total_xp': 0,
                'total_messages': 0,
                'avg_level': 0,
                'max_level': 0
            }

        except Exception as e:
            bot_logger.exception(f'خطأ في get_guild_stats: {guild_id}', e)
            return {}


# ==================== النسخة العامة ====================

leveling_system = LevelingSystem()