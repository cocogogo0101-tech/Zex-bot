# ==================== embeds.py - Ultimate ====================
"""
embeds.py - Ultimate Version
=============================
قوالب Embeds احترافية وشاملة
"""

import discord
from datetime import datetime
from typing import Optional, List
import helpers


class Colors:
    """ألوان محددة"""
    SUCCESS = discord.Color.green()
    ERROR = discord.Color.red()
    WARNING = discord.Color.orange()
    INFO = discord.Color.blue()
    PURPLE = discord.Color.purple()
    GOLD = discord.Color.gold()
    DEFAULT = discord.Color.blurple()


# ==================== Basic Embeds ====================

def success_embed(title: str, description: str = None) -> discord.Embed:
    """Embed نجاح"""
    embed = discord.Embed(
        title=f'✅ {title}',
        description=description,
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    )
    return embed


def error_embed(title: str, description: str = None) -> discord.Embed:
    """Embed خطأ"""
    embed = discord.Embed(
        title=f'❌ {title}',
        description=description,
        color=Colors.ERROR,
        timestamp=datetime.now()
    )
    return embed


def warning_embed(title: str, description: str = None) -> discord.Embed:
    """Embed تحذير"""
    embed = discord.Embed(
        title=f'⚠️ {title}',
        description=description,
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    return embed


def info_embed(title: str, description: str = None) -> discord.Embed:
    """Embed معلومات"""
    embed = discord.Embed(
        title=f'ℹ️ {title}',
        description=description,
        color=Colors.INFO,
        timestamp=datetime.now()
    )
    return embed


# ==================== Moderation Embeds ====================

def kick_embed(user: discord.User, moderator: discord.User, reason: str = None) -> discord.Embed:
    """Embed طرد"""
    embed = discord.Embed(
        title='👢 طرد عضو',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    embed.add_field(name='العضو', value=f'{user.mention}\n`{user.id}`', inline=True)
    embed.add_field(name='المشرف', value=f'{moderator.mention}', inline=True)
    embed.add_field(name='السبب', value=reason or 'لا يوجد سبب', inline=False)
    embed.set_thumbnail(url=helpers.get_user_avatar(user))
    return embed


def ban_embed(user: discord.User, moderator: discord.User, reason: str = None) -> discord.Embed:
    """Embed حظر"""
    embed = discord.Embed(
        title='🔨 حظر عضو',
        color=Colors.ERROR,
        timestamp=datetime.now()
    )
    embed.add_field(name='العضو', value=f'{user.mention}\n`{user.id}`', inline=True)
    embed.add_field(name='المشرف', value=f'{moderator.mention}', inline=True)
    embed.add_field(name='السبب', value=reason or 'لا يوجد سبب', inline=False)
    embed.set_thumbnail(url=helpers.get_user_avatar(user))
    return embed


def timeout_embed(user: discord.User, moderator: discord.User, duration: str, reason: str = None) -> discord.Embed:
    """Embed إسكات"""
    embed = discord.Embed(
        title='🔇 إسكات عضو',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    embed.add_field(name='العضو', value=f'{user.mention}\n`{user.id}`', inline=True)
    embed.add_field(name='المشرف', value=f'{moderator.mention}', inline=True)
    embed.add_field(name='المدة', value=duration, inline=True)
    embed.add_field(name='السبب', value=reason or 'لا يوجد سبب', inline=False)
    embed.set_thumbnail(url=helpers.get_user_avatar(user))
    return embed


def warn_embed(user: discord.User, moderator: discord.User, reason: str, warn_count: int) -> discord.Embed:
    """Embed تحذير"""
    embed = discord.Embed(
        title='⚠️ تحذير عضو',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    embed.add_field(name='العضو', value=f'{user.mention}\n`{user.id}`', inline=True)
    embed.add_field(name='المشرف', value=f'{moderator.mention}', inline=True)
    embed.add_field(name='عدد التحذيرات', value=f'`{warn_count}`', inline=True)
    embed.add_field(name='السبب', value=reason, inline=False)
    embed.set_thumbnail(url=helpers.get_user_avatar(user))
    return embed


def warnings_list_embed(user: discord.User, warnings: List) -> discord.Embed:
    """Embed قائمة التحذيرات"""
    embed = discord.Embed(
        title=f'⚠️ تحذيرات {helpers.format_user(user)}',
        description=f'إجمالي التحذيرات: **{len(warnings)}**',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )

    if warnings:
        for i, warn in enumerate(warnings[:10], 1):
            moderator_id = warn.get('moderator_id', 'غير معروف')
            reason = warn.get('reason', 'لا يوجد سبب')
            created = warn.get('created_at', 'غير معروف')

            embed.add_field(
                name=f'التحذير #{i} • ID: {warn["id"]}',
                value=f'**المشرف:** <@{moderator_id}>\n**السبب:** {reason}\n**التاريخ:** {helpers.format_datetime(created)}',
                inline=False
            )
    else:
        embed.description = 'لا توجد تحذيرات'

    embed.set_thumbnail(url=helpers.get_user_avatar(user))
    return embed


# ==================== Info Embeds ====================

def user_info_embed(member: discord.Member) -> discord.Embed:
    """Embed معلومات العضو"""
    embed = discord.Embed(
        title=f'معلومات {helpers.format_user(member)}',
        color=helpers.get_member_color(member),
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=helpers.get_user_avatar(member))

    embed.add_field(name='الاسم', value=member.name, inline=True)
    embed.add_field(name='الـ ID', value=f'`{member.id}`', inline=True)
    embed.add_field(name='بوت؟', value='✅ نعم' if member.bot else '❌ لا', inline=True)

    embed.add_field(
        name='تاريخ الإنشاء',
        value=f'<t:{int(member.created_at.timestamp())}:F>\n<t:{int(member.created_at.timestamp())}:R>',
        inline=True
    )
    embed.add_field(
        name='تاريخ الانضمام',
        value=f'<t:{int(member.joined_at.timestamp())}:F>\n<t:{int(member.joined_at.timestamp())}:R>',
        inline=True
    )

    roles = [role.mention for role in member.roles[1:]] if len(member.roles) > 1 else ['لا يوجد']
    roles_text = ', '.join(roles[:10]) if len(roles) <= 10 else ', '.join(roles[:10]) + f' +{len(roles) - 10}'
    embed.add_field(name=f'الأدوار [{len(member.roles) - 1}]', value=roles_text, inline=False)

    return embed


def server_info_embed(guild: discord.Guild) -> discord.Embed:
    """Embed معلومات السيرفر"""
    embed = discord.Embed(
        title=f'معلومات {guild.name}',
        color=Colors.INFO,
        timestamp=datetime.now()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name='الـ ID', value=f'`{guild.id}`', inline=True)
    embed.add_field(name='المالك', value=guild.owner.mention if guild.owner else 'غير معروف', inline=True)

    total_members = guild.member_count
    humans = sum(1 for m in guild.members if not m.bot)
    bots = sum(1 for m in guild.members if m.bot)

    embed.add_field(name='الأعضاء', value=f'👥 {total_members}\n👤 {humans}\n🤖 {bots}', inline=True)

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)

    embed.add_field(name='القنوات', value=f'💬 {text_channels}\n🔊 {voice_channels}', inline=True)
    embed.add_field(name='الأدوار', value=str(len(guild.roles)), inline=True)

    embed.add_field(
        name='تاريخ الإنشاء',
        value=f'<t:{int(guild.created_at.timestamp())}:F>\n<t:{int(guild.created_at.timestamp())}:R>',
        inline=False
    )

    return embed


# ==================== Leveling Embeds ====================

def level_up_embed(member: discord.Member, level: int) -> discord.Embed:
    """Embed ترقية مستوى"""
    embed = discord.Embed(
        title='🎉 ترقية!',
        description=f'{member.mention} وصل إلى المستوى **{level}**!',
        color=Colors.GOLD,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=helpers.get_user_avatar(member))
    return embed


def rank_embed(member: discord.Member, data: dict, rank: int) -> discord.Embed:
    """Embed رتبة العضو"""
    embed = discord.Embed(
        title=f'📊 رتبة {helpers.format_user(member)}',
        color=helpers.get_member_color(member),
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=helpers.get_user_avatar(member))

    level = data.get('level', 0)
    xp = data.get('xp', 0)
    messages = data.get('messages', 0)

    embed.add_field(name='المستوى', value=f'`{level}`', inline=True)
    embed.add_field(name='الترتيب', value=f'`#{rank}`', inline=True)
    embed.add_field(name='الرسائل', value=f'`{messages}`', inline=True)

    # شريط التقدم (تقريبي)
    next_level_xp = ((level + 1) * 10) ** 2
    current_level_xp = (level * 10) ** 2
    xp_progress = xp - current_level_xp
    xp_total = next_level_xp - current_level_xp
    xp_needed = xp_total - xp_progress

    progress_bar_length = 10
    filled = int((xp_progress / xp_total) * progress_bar_length) if xp_total > 0 else 0
    bar = '█' * filled + '░' * (progress_bar_length - filled)

    embed.add_field(
        name='التقدم',
        value=f'```{bar}```\n{xp_progress}/{xp_total} XP\nيتبقى {xp_needed} XP',
        inline=False
    )

    return embed


def leaderboard_embed(guild: discord.Guild, leaderboard: List, page: int = 1) -> discord.Embed:
    """Embed لوحة الصدارة"""
    embed = discord.Embed(
        title=f'🏆 لوحة صدارة {guild.name}',
        description='أعلى الأعضاء نشاطاً',
        color=Colors.GOLD,
        timestamp=datetime.now()
    )

    medals = ['🥇', '🥈', '🥉']

    for i, entry in enumerate(leaderboard, start=(page - 1) * 10 + 1):
        user_id = entry.get('user_id')
        level = entry.get('level', 0)
        xp = entry.get('xp', 0)
        messages = entry.get('messages', 0)

        medal = medals[i - 1] if i <= 3 else f'`#{i}`'

        embed.add_field(
            name=f'{medal} <@{user_id}>',
            value=f'المستوى: {level} • XP: {xp} • الرسائل: {messages}',
            inline=False
        )

    embed.set_footer(text=f'الصفحة {page}')
    return embed


# ==================== Ticket Embeds ====================

def ticket_created_embed(user: discord.User, reason: str = None) -> discord.Embed:
    """Embed إنشاء تكت"""
    embed = discord.Embed(
        title='🎫 تكت جديد',
        description=f'تم إنشاء تكت بواسطة {user.mention}',
        color=Colors.INFO,
        timestamp=datetime.now()
    )
    embed.add_field(name='السبب', value=reason or 'لا يوجد سبب', inline=False)
    embed.set_footer(text='استخدم الزر بالأسفل لإغلاق التكت')
    return embed


def ticket_closed_embed(closer: discord.User) -> discord.Embed:
    """Embed إغلاق تكت"""
    embed = discord.Embed(
        title='🔒 إغلاق التكت',
        description=f'تم إغلاق التكت بواسطة {closer.mention}',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    return embed


# ==================== Log Embeds ====================

def log_embed(action: str, description: str, color: discord.Color = Colors.INFO) -> discord.Embed:
    """Embed سجل عام"""
    embed = discord.Embed(
        title=action,
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    return embed


def message_delete_log_embed(message: discord.Message) -> discord.Embed:
    """Embed حذف رسالة"""
    embed = discord.Embed(
        title='🗑️ رسالة محذوفة',
        color=Colors.ERROR,
        timestamp=datetime.now()
    )
    embed.add_field(name='الكاتب', value=message.author.mention, inline=True)
    embed.add_field(name='القناة', value=message.channel.mention, inline=True)

    content = message.content[:1024] if message.content else '[بدون محتوى نصي]'
    embed.add_field(name='المحتوى', value=content, inline=False)

    if message.attachments:
        embed.add_field(name='المرفقات', value=str(len(message.attachments)), inline=True)

    embed.set_footer(text=f'ID: {message.id}')
    return embed


def message_edit_log_embed(before: discord.Message, after: discord.Message) -> discord.Embed:
    """Embed تعديل رسالة"""
    embed = discord.Embed(
        title='✏️ رسالة معدلة',
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    embed.add_field(name='الكاتب', value=before.author.mention, inline=True)
    embed.add_field(name='القناة', value=before.channel.mention, inline=True)

    before_content = before.content[:512] if before.content else '[بدون محتوى]'
    after_content = after.content[:512] if after.content else '[بدون محتوى]'

    embed.add_field(name='قبل', value=before_content, inline=False)
    embed.add_field(name='بعد', value=after_content, inline=False)

    embed.add_field(name='الرابط', value=f'[اذهب للرسالة]({after.jump_url})', inline=False)
    embed.set_footer(text=f'ID: {before.id}')
    return embed


# ==================== Config Embed ====================

def config_embed(guild: discord.Guild, settings: dict) -> discord.Embed:
    """Embed عرض الإعدادات"""
    embed = discord.Embed(
        title=f'⚙️ إعدادات {guild.name}',
        color=Colors.INFO,
        timestamp=datetime.now()
    )

    # الترحيب
    welcome_status = '✅ مفعل' if settings.get('welcome_enabled') else '❌ معطل'
    welcome_channel = f"<#{settings.get('welcome_channel_id')}>" if settings.get('welcome_channel_id') else 'غير محدد'
    embed.add_field(
        name='🎉 الترحيب',
        value=f'الحالة: {welcome_status}\nالقناة: {welcome_channel}',
        inline=True
    )

    # الوداع
    goodbye_status = '✅ مفعل' if settings.get('goodbye_enabled') else '❌ معطل'
    goodbye_channel = f"<#{settings.get('goodbye_channel_id')}>" if settings.get('goodbye_channel_id') else 'غير محدد'
    embed.add_field(
        name='👋 الوداع',
        value=f'الحالة: {goodbye_status}\nالقناة: {goodbye_channel}',
        inline=True
    )

    # السجلات
    logs_channel = f"<#{settings.get('logs_channel_id')}>" if settings.get('logs_channel_id') else 'غير محدد'
    embed.add_field(
        name='📝 السجلات',
        value=f'القناة: {logs_channel}',
        inline=True
    )

    # الحماية
    antispam = '✅ مفعل' if settings.get('antispam_enabled') else '❌ معطل'
    antilink = '✅ مفعل' if settings.get('antilink_enabled') else '❌ معطل'
    automod = '✅ مفعل' if settings.get('automod_enabled') else '❌ معطل'

    embed.add_field(
        name='🛡️ الحماية',
        value=f'Anti-Spam: {antispam}\nAnti-Link: {antilink}\nAuto-Mod: {automod}',
        inline=True
    )

    # المستويات
    leveling = '✅ مفعل' if settings.get('leveling_enabled') else '❌ معطل'
    embed.add_field(
        name='📊 المستويات',
        value=f'الحالة: {leveling}',
        inline=True
    )

    return embed


# ==================== Welcome/Goodbye Embeds ====================

def welcome_embed(member: discord.Member, member_count: int) -> discord.Embed:
    """Embed ترحيب"""
    embed = discord.Embed(
        title=f'👋 مرحباً بك في {member.guild.name}!',
        description=f'{member.mention} انضم إلى السيرفر',
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    )
    embed.add_field(name='العضو', value=f'{helpers.format_user(member)}', inline=True)
    embed.add_field(name='رقم العضو', value=f'#{member_count}', inline=True)
    embed.set_thumbnail(url=helpers.get_user_avatar(member))
    embed.set_footer(text=f'ID: {member.id}')
    return embed


def goodbye_embed(member: discord.Member) -> discord.Embed:
    """Embed وداع"""
    embed = discord.Embed(
        title=f'👋 وداعاً!',
        description=f'{member.mention} غادر السيرفر',
        color=Colors.ERROR,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=helpers.get_user_avatar(member))
    embed.set_footer(text=f'ID: {member.id}')
    return embed