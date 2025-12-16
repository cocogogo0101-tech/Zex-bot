# ==================== permissions.py - Ultimate ====================
"""
permissions.py - Ultimate Version
==================================
نظام الصلاحيات الشامل والمتقدم

Features:
✅ Decorators متقدمة
✅ Hierarchy checks
✅ Context managers
✅ Bot permissions checks
✅ Role-based permissions
✅ Custom error messages
"""

import discord
from discord import app_commands
from typing import Optional, Callable
from functools import wraps
from database import db
from logger import bot_logger


# ==================== Permission Decorators ====================

def is_owner():
    """التحقق من صاحب البوت"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)


def is_admin():
    """التحقق من Administrator"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
        return False
    return app_commands.check(predicate)


def is_moderator():
    """التحقق من المشرف"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member):
            perms = interaction.user.guild_permissions
            return (
                perms.administrator or
                perms.kick_members or
                perms.ban_members or
                perms.manage_messages or
                perms.manage_guild
            )
        return False
    return app_commands.check(predicate)


def has_permissions(**perms):
    """التحقق من صلاحيات محددة"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member):
            permissions = interaction.user.guild_permissions
            return all(getattr(permissions, perm, False) for perm in perms)
        return False
    return app_commands.check(predicate)


def has_role(*role_ids: int):
    """التحقق من دور محدد"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member):
            return any(role.id in role_ids for role in interaction.user.roles)
        return False
    return app_commands.check(predicate)


def has_support_role():
    """التحقق من دور الدعم"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False

        settings = await db.get_settings(str(interaction.guild.id))
        if not settings or not settings.get('support_role_id'):
            return False

        support_role_id = int(settings['support_role_id'])
        return any(role.id == support_role_id for role in interaction.user.roles)

    return app_commands.check(predicate)


def not_blacklisted():
    """التحقق من عدم الحظر"""
    async def predicate(interaction: discord.Interaction) -> bool:
        is_blacklisted = await db.is_in_list(
            str(interaction.guild.id),
            str(interaction.user.id),
            'blacklist'
        )
        return not is_blacklisted

    return app_commands.check(predicate)


# ==================== Helper Functions ====================

async def check_permissions(member: discord.Member, **perms) -> bool:
    """التحقق من صلاحيات العضو"""
    if not member:
        return False

    permissions = member.guild_permissions
    return all(getattr(permissions, perm, False) for perm in perms)


async def check_hierarchy(
    moderator: discord.Member,
    target: discord.Member
) -> tuple[bool, Optional[str]]:
    """
    التحقق من التسلسل الهرمي

    Returns:
        (نجح؟, رسالة الخطأ)
    """
    # نفس المستخدم
    if moderator.id == target.id:
        return False, '❌ لا يمكنك تنفيذ هذا الإجراء على نفسك!'

    # صاحب السيرفر
    if target.id == moderator.guild.owner_id:
        return False, '❌ لا يمكنك تنفيذ هذا الإجراء على صاحب السيرفر!'

    # رتبة المشرف
    if moderator.top_role <= target.top_role:
        return False, '❌ رتبة الهدف أعلى أو مساوية لرتبتك!'

    # رتبة البوت
    bot_member = moderator.guild.me
    if bot_member.top_role <= target.top_role:
        return False, '❌ رتبة الهدف أعلى أو مساوية لرتبة البوت!'

    return True, None


async def can_execute_action(
    moderator: discord.Member,
    target: discord.Member,
    action: str
) -> tuple[bool, Optional[str]]:
    """
    التحقق من إمكانية تنفيذ إجراء

    Args:
        moderator: المشرف
        target: الهدف
        action: نوع الإجراء

    Returns:
        (يمكن؟, رسالة الخطأ)
    """
    # التحقق من التسلسل الهرمي
    can_do, error = await check_hierarchy(moderator, target)
    if not can_do:
        return False, error

    # التحقق من الصلاحيات
    required_perms = {
        'kick': {'kick_members': True},
        'ban': {'ban_members': True},
        'timeout': {'moderate_members': True},
        'warn': {'kick_members': True},
    }

    perms = required_perms.get(action, {})
    if perms:
        has_perms = await check_permissions(moderator, **perms)
        if not has_perms:
            return False, f'❌ ليس لديك صلاحية {action}!'

    return True, None


async def check_bot_permissions(guild: discord.Guild, **perms) -> tuple[bool, Optional[str]]:
    """
    التحقق من صلاحيات البوت

    Returns:
        (لديه الصلاحيات؟, رسالة الخطأ)
    """
    bot_member = guild.me
    permissions = bot_member.guild_permissions

    missing_perms = []
    for perm, required in perms.items():
        if required and not getattr(permissions, perm, False):
            missing_perms.append(perm)

    if missing_perms:
        perms_text = ', '.join(missing_perms)
        return False, f'❌ البوت يحتاج الصلاحيات: {perms_text}'

    return True, None


# ==================== Context Manager ====================

class PermissionChecker:
    """مدير السياق للتحقق من الصلاحيات"""

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.errors = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.errors and not exc_type:
            await self.interaction.response.send_message(
                '\n'.join(self.errors),
                ephemeral=True
            )
            return True
        return False

    async def check_target(self, target: discord.Member, action: str) -> bool:
        """التحقق من الهدف"""
        if not isinstance(self.interaction.user, discord.Member):
            self.errors.append('❌ لا يمكن استخدام هذا الأمر في DM!')
            return False

        can_do, error = await can_execute_action(
            self.interaction.user,
            target,
            action
        )

        if not can_do:
            self.errors.append(error)
            return False

        return True

    async def check_bot_perms(self, **perms) -> bool:
        """التحقق من صلاحيات البوت"""
        can_do, error = await check_bot_permissions(
            self.interaction.guild,
            **perms
        )

        if not can_do:
            self.errors.append(error)
            return False

        return True

