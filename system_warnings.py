"""
نظام التحذيرات الذكي مع الإجراءات التلقائية
"""

import discord
from typing import Optional, Dict, List
from datetime import datetime
from database import db
import embeds

class WarningSystem:
    """نظام التحذيرات"""
    
    # الإجراءات التلقائية حسب عدد التحذيرات
    AUTO_ACTIONS = {
        3: 'timeout_10m',
        5: 'timeout_1h',
        7: 'kick',
        10: 'ban'
    }
    
    async def warn_user(
        self,
        guild: discord.Guild,
        user: discord.User,
        moderator: discord.User,
        reason: str
    ) -> Dict:
        """
        تحذير مستخدم
        
        Returns:
            dict: معلومات التحذير
        """
        # إضافة التحذير
        warn_id = await db.add_warning(
            str(guild.id),
            str(user.id),
            str(moderator.id),
            reason
        )
        
        # الحصول على عدد التحذيرات
        warn_count = await db.get_warning_count(str(guild.id), str(user.id))
        
        # تسجيل في السجل
        await db.add_log(
            str(guild.id),
            'warn',
            str(user.id),
            str(moderator.id),
            reason=reason
        )
        
        # التحقق من الإجراءات التلقائية
        auto_action = None
        if warn_count in self.AUTO_ACTIONS:
            auto_action = self.AUTO_ACTIONS[warn_count]
            await self._execute_auto_action(guild, user, moderator, auto_action, warn_count)
        
        return {
            'warn_id': warn_id,
            'warn_count': warn_count,
            'auto_action': auto_action
        }
    
    async def _execute_auto_action(
        self,
        guild: discord.Guild,
        user: discord.User,
        moderator: discord.User,
        action: str,
        warn_count: int
    ):
        """تنفيذ الإجراء التلقائي"""
        member = guild.get_member(user.id)
        if not member:
            return
        
        reason = f'إجراء تلقائي - {warn_count} تحذيرات'
        
        try:
            if action == 'timeout_10m':
                await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10), reason=reason)
            elif action == 'timeout_1h':
                await member.timeout(discord.utils.utcnow() + discord.timedelta(hours=1), reason=reason)
            elif action == 'kick':
                await member.kick(reason=reason)
            elif action == 'ban':
                await member.ban(reason=reason, delete_message_days=1)
        except (discord.Forbidden, discord.HTTPException):
            pass
    
    async def remove_warning(self, warn_id: int) -> bool:
        """حذف تحذير"""
        return await db.remove_warning(warn_id)
    
    async def clear_warnings(self, guild_id: str, user_id: str):
        """مسح جميع تحذيرات مستخدم"""
        await db.clear_warnings(guild_id, user_id)
    
    async def get_warnings(self, guild_id: str, user_id: str) -> List[Dict]:
        """الحصول على تحذيرات مستخدم"""
        return await db.get_warnings(guild_id, user_id)
    
    async def get_warning_count(self, guild_id: str, user_id: str) -> int:
        """عدد تحذيرات مستخدم"""
        return await db.get_warning_count(guild_id, user_id)

warning_system = WarningSystem()