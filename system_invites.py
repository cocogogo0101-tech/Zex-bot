"""
نظام تتبع الدعوات المتقدم
يتتبع من دعا من + مكافآت تلقائية
"""

import discord
from typing import Optional, Dict, List
from datetime import datetime
from database import db
from config_manager import config
import embeds

class InviteTracker:
    """تتبع الدعوات"""

    def __init__(self):
        self.invites_cache = {}  # {guild_id: {code: Invite}}

    async def cache_invites(self, guild: discord.Guild):
        """تخزين جميع الدعوات الحالية"""
        try:
            invites = await guild.invites()
            self.invites_cache[guild.id] = {inv.code: inv for inv in invites}
        except discord.Forbidden:
            print(f"⚠️ لا يمكن الوصول لدعوات {guild.name} - تحقق من الصلاحيات!")

    async def find_inviter(self, member: discord.Member) -> Optional[discord.Member]:
        """
        اكتشاف من دعا العضو

        Returns:
            المستخدم الذي دعا أو None
        """
        guild = member.guild

        # جلب الدعوات الجديدة
        try:
            new_invites = await guild.invites()
        except discord.Forbidden:
            return None

        # المقارنة مع الكاش
        old_invites = self.invites_cache.get(guild.id, {})

        for invite in new_invites:
            old_invite = old_invites.get(invite.code)

            # إذا زاد الاستخدام
            if old_invite and invite.uses > old_invite.uses:
                # تحديث الكاش
                await self.cache_invites(guild)

                # حفظ في DB
                await self.record_invite(guild.id, member.id, invite.inviter.id if invite.inviter else None)

                return invite.inviter

        # تحديث الكاش في كل الأحوال
        await self.cache_invites(guild)
        return None

    async def record_invite(self, guild_id: int, user_id: int, inviter_id: Optional[int]):
        """تسجيل دعوة في قاعدة البيانات"""
        await db.conn.execute('''
            INSERT INTO invites (guild_id, user_id, inviter_id, created_at)
            VALUES (?, ?, ?, ?)
        ''', (str(guild_id), str(user_id), str(inviter_id) if inviter_id else None, datetime.now().isoformat()))
        await db.conn.commit()

    async def get_user_invites(self, guild_id: str, user_id: str) -> int:
        """عدد الدعوات الناجحة للمستخدم"""
        cursor = await db.conn.execute('''
            SELECT COUNT(*) FROM invites 
            WHERE guild_id = ? AND inviter_id = ?
        ''', (guild_id, user_id))
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_invite_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict]:
        """لوحة صدارة الدعوات"""
        cursor = await db.conn.execute('''
            SELECT inviter_id, COUNT(*) as count
            FROM invites
            WHERE guild_id = ? AND inviter_id IS NOT NULL
            GROUP BY inviter_id
            ORDER BY count DESC
            LIMIT ?
        ''', (guild_id, limit))
        rows = await cursor.fetchall()
        return [{'user_id': row[0], 'invites': row[1]} for row in rows]

    async def get_invited_by(self, guild_id: str, user_id: str) -> Optional[str]:
        """من دعا هذا المستخدم؟"""
        cursor = await db.conn.execute('''
            SELECT inviter_id FROM invites
            WHERE guild_id = ? AND user_id = ?
            LIMIT 1
        ''', (guild_id, user_id))
        row = await cursor.fetchone()
        return row[0] if row else None

class InviteRewards:
    """نظام مكافآت الدعوات"""

    async def check_rewards(self, guild: discord.Guild, inviter: discord.Member, invite_count: int):
        """
        التحقق من المكافآت وإعطائها

        Args:
            guild: السيرفر
            inviter: المستخدم الذي دعا
            invite_count: عدد دعواته الحالي
        """
        # جلب المكافآت المعدّة
        rewards = await self.get_rewards(str(guild.id))

        for reward in rewards:
            required = reward['required_invites']
            role_id = reward['role_id']

            # إذا وصل العدد المطلوب
            if invite_count == required:
                role = guild.get_role(int(role_id))
                if role:
                    try:
                        # إعطاء الدور
                        await inviter.add_roles(role)

                        # إرسال DM
                        await self.send_reward_dm(inviter, role, invite_count)

                        # تسجيل
                        await db.add_log(
                            str(guild.id),
                            'invite_reward',
                            str(inviter.id),
                            details=f'Role: {role.name}, Invites: {invite_count}'
                        )
                    except discord.Forbidden:
                        pass

    async def send_reward_dm(self, user: discord.Member, role: discord.Role, invite_count: int):
        """إرسال رسالة خاصة بالمكافأة"""
        try:
            embed = discord.Embed(
                title='🎉 مكافأة الدعوات!',
                description=f'تهانينا! لقد حصلت على دور **{role.name}**',
                color=discord.Color.gold()
            )
            embed.add_field(name='عدد الدعوات', value=f'`{invite_count}`', inline=True)
            embed.add_field(name='السيرفر', value=user.guild.name, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)

            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    async def add_reward(self, guild_id: str, required_invites: int, role_id: str):
        """إضافة مكافأة جديدة"""
        await db.conn.execute('''
            INSERT INTO invite_rewards (guild_id, required_invites, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, required_invites) 
            DO UPDATE SET role_id = excluded.role_id
        ''', (guild_id, required_invites, role_id))
        await db.conn.commit()

    async def remove_reward(self, guild_id: str, required_invites: int):
        """حذف مكافأة"""
        await db.conn.execute('''
            DELETE FROM invite_rewards
            WHERE guild_id = ? AND required_invites = ?
        ''', (guild_id, required_invites))
        await db.conn.commit()

    async def get_rewards(self, guild_id: str) -> List[Dict]:
        """جلب جميع المكافآت"""
        cursor = await db.conn.execute('''
            SELECT required_invites, role_id
            FROM invite_rewards
            WHERE guild_id = ?
            ORDER BY required_invites ASC
        ''', (guild_id,))
        rows = await cursor.fetchall()
        return [{'required_invites': row[0], 'role_id': row[1]} for row in rows]

    async def get_next_reward(self, guild_id: str, current_invites: int) -> Optional[Dict]:
        """المكافأة التالية للمستخدم"""
        cursor = await db.conn.execute('''
            SELECT required_invites, role_id
            FROM invite_rewards
            WHERE guild_id = ? AND required_invites > ?
            ORDER BY required_invites ASC
            LIMIT 1
        ''', (guild_id, current_invites))
        row = await cursor.fetchone()
        if row:
            return {'required_invites': row[0], 'role_id': row[1]}
        return None

# النسخ العامة
invite_tracker = InviteTracker()
invite_rewards = InviteRewards()