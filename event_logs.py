# ==================== event_logs.py ====================
"""
تسجيل الأحداث
✅ تم إضافة Guards للحماية
✅ تم تحسين error handling
"""
import discord
from config_manager import config
from database import db
import embeds
from logger import bot_logger

async def send_log(guild: discord.Guild, embed: discord.Embed):
    """إرسال سجل"""
    try:
        if not guild:
            return

        logs_channel_id = await config.get_logs_channel(str(guild.id))
        if not logs_channel_id:
            return

        channel = await config.validate_channel(guild, logs_channel_id)
        if not channel:
            bot_logger.debug(f'قناة السجلات غير موجودة في {guild.name}')
            return

        # التحقق من الصلاحيات
        bot_perms = channel.permissions_for(guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في قناة السجلات')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال السجل: {e}')

    except Exception as e:
        bot_logger.error(f'خطأ في send_log: {e}')


async def log_message_delete(message: discord.Message):
    """تسجيل حذف رسالة"""
    try:
        if not message or message.author.bot or not message.guild:
            return

        embed = embeds.message_delete_log_embed(message)
        await send_log(message.guild, embed)
        await db.add_log(str(message.guild.id), 'message_delete', str(message.author.id))

    except Exception as e:
        bot_logger.error(f'خطأ في log_message_delete: {e}')


async def log_message_edit(before: discord.Message, after: discord.Message):
    """تسجيل تعديل رسالة"""
    try:
        if not before or not after or before.author.bot or not before.guild:
            return

        if before.content == after.content:
            return

        embed = embeds.message_edit_log_embed(before, after)
        await send_log(before.guild, embed)
        await db.add_log(str(before.guild.id), 'message_edit', str(before.author.id))

    except Exception as e:
        bot_logger.error(f'خطأ في log_message_edit: {e}')


async def log_member_join(member: discord.Member):
    """تسجيل انضمام عضو"""
    try:
        if not member or not member.guild:
            return

        embed = embeds.log_embed(
            '📥 عضو جديد',
            f'{member.mention} انضم للسيرفر\nID: `{member.id}`',
            embeds.Colors.SUCCESS
        )
        await send_log(member.guild, embed)
        await db.add_log(str(member.guild.id), 'member_join', str(member.id))
        await db.increment_stat(str(member.guild.id), 'joins')

    except Exception as e:
        bot_logger.error(f'خطأ في log_member_join: {e}')


async def log_member_remove(member: discord.Member):
    """تسجيل مغادرة عضو"""
    try:
        if not member or not member.guild:
            return

        embed = embeds.log_embed(
            '📤 عضو غادر',
            f'**{member.name}** غادر السيرفر\nID: `{member.id}`',
            embeds.Colors.ERROR
        )
        await send_log(member.guild, embed)
        await db.add_log(str(member.guild.id), 'member_leave', str(member.id))
        await db.increment_stat(str(member.guild.id), 'leaves')

    except Exception as e:
        bot_logger.error(f'خطأ في log_member_remove: {e}')
