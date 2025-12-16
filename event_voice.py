# ==================== event_voice.py ====================
"""
أحداث القنوات الصوتية
✅ تم إضافة Guards للحماية
✅ تم تحسين error handling
"""
import discord
from datetime import datetime
from collections import defaultdict
from database import db
from event_logs import send_log
import embeds
from logger import bot_logger

# تخزين أوقات الانضمام
voice_times = defaultdict(dict)  # {guild_id: {user_id: join_time}}

async def handle_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """معالجة تحديثات الحالة الصوتية"""
    try:
        # Guards
        if not member or not member.guild:
            return

        guild_id = str(member.guild.id)
        user_id = str(member.id)

        # انضمام لقناة صوتية
        if before.channel is None and after.channel is not None:
            voice_times[guild_id][user_id] = datetime.now()
            await log_voice_join(member, after.channel)

        # مغادرة قناة صوتية
        elif before.channel is not None and after.channel is None:
            if user_id in voice_times[guild_id]:
                join_time = voice_times[guild_id].pop(user_id)
                duration = (datetime.now() - join_time).total_seconds()
                minutes = int(duration / 60)

                # تحديث الإحصائيات
                try:
                    await db.increment_stat(guild_id, 'voice_minutes', minutes)
                except Exception as e:
                    bot_logger.error(f'خطأ في تحديث إحصائيات الصوت: {e}')

                await log_voice_leave(member, before.channel, minutes)

        # الانتقال بين القنوات
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            await log_voice_move(member, before.channel, after.channel)

    except Exception as e:
        bot_logger.exception('خطأ غير متوقع في handle_voice_state_update', e)


async def log_voice_join(member: discord.Member, channel: discord.VoiceChannel):
    """تسجيل الانضمام لقناة صوتية"""
    try:
        embed = embeds.log_embed(
            '🔊 انضمام صوتي',
            f'{member.mention} انضم إلى {channel.mention}',
            embeds.Colors.SUCCESS
        )
        await send_log(member.guild, embed)
    except Exception as e:
        bot_logger.error(f'خطأ في log_voice_join: {e}')


async def log_voice_leave(member: discord.Member, channel: discord.VoiceChannel, minutes: int):
    """تسجيل مغادرة قناة صوتية"""
    try:
        embed = embeds.log_embed(
            '🔇 مغادرة صوتية',
            f'{member.mention} غادر {channel.mention}\nالمدة: {minutes} دقيقة',
            embeds.Colors.WARNING
        )
        await send_log(member.guild, embed)
    except Exception as e:
        bot_logger.error(f'خطأ في log_voice_leave: {e}')


async def log_voice_move(member: discord.Member, before: discord.VoiceChannel, after: discord.VoiceChannel):
    """تسجيل الانتقال بين القنوات"""
    try:
        embed = embeds.log_embed(
            '🔄 انتقال صوتي',
            f'{member.mention} انتقل من {before.mention} إلى {after.mention}',
            embeds.Colors.INFO
        )
        await send_log(member.guild, embed)
    except Exception as e:
        bot_logger.error(f'خطأ في log_voice_move: {e}')