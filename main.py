"""
البوت الرئيسي - نظام إدارة وترحيب متطور
✅ تم إصلاح جميع المشاكل
✅ تم تحسين الأداء
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import signal
import sys

# تحميل المتغيرات
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

# التحقق من التوكن
if not TOKEN:
    print('❌ خطأ: ضع DISCORD_TOKEN في ملف .env')
    sys.exit(1)

# الـ Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = False

# البوت
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==================== الاستيرادات ====================

from logger import bot_logger

from database import db
from config_manager import config
from system_tickets import ticket_system, TicketControlView, TicketPanelView
from system_autoresponse import autoresponse_system
from system_leveling import leveling_system
from system_warnings import warning_system
from system_protection import protection_system

from event_welcome import handle_member_join, handle_member_remove
from event_logs import log_message_delete, log_message_edit, log_member_join, log_member_remove
from event_messages import process_message
from event_voice import handle_voice_state_update
from cmd_aliases import process_aliases

from cmd_moderation import setup_moderation_commands
from cmd_config import setup_config_commands
from cmd_utility import setup_utility_commands
from cmd_fun import setup_fun_commands
from cmd_info import setup_info_commands

# ==================== Global State ====================

commands_registered = False
shutdown_initiated = False

# ==================== الأحداث الأساسية ====================

@bot.event
async def on_ready():
    global commands_registered

    try:
        bot_logger.info(f'البوت متصل: {bot.user.name} (ID: {bot.user.id})')
        bot_logger.info(f'Discord.py Version: {discord.__version__}')
        bot_logger.info(f'Python Version: {sys.version}')

        await db.connect()

        if not commands_registered:
            bot_logger.info('بدء تسجيل الأوامر...')

            setup_moderation_commands(bot)
            setup_config_commands(bot)
            setup_utility_commands(bot)
            setup_fun_commands(bot)
            setup_info_commands(bot)

            commands_registered = True

        bot.add_view(TicketControlView())
        bot.add_view(TicketPanelView())

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'{len(bot.guilds)} سيرفر'
            )
        )

        bot_logger.success('🚀 البوت جاهز للعمل!')

    except Exception as e:
        bot_logger.exception('خطأ حرج في on_ready', e)
        raise

# ==================== أحداث ====================

@bot.event
async def on_member_join(member):
    await handle_member_join(member)

@bot.event
async def on_member_remove(member):
    await handle_member_remove(member)

@bot.event
async def on_message(message):
    if not message.guild:
        return
    await process_aliases(bot, message)
    await process_message(message)
    await bot.process_commands(message)

# ==================== Shutdown ====================

async def shutdown(bot):
    global shutdown_initiated
    if shutdown_initiated:
        return
    shutdown_initiated = True
    await db.close()
    await bot.close()
    bot_logger.success('تم إيقاف البوت')

def handle_signal(sig):
    asyncio.create_task(shutdown(bot))

# ==================== التشغيل ====================

async def main():
    try:
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

        async with bot:
            await bot.start(TOKEN)

    except Exception as e:
        bot_logger.exception('خطأ في main', e)
        await shutdown(bot)
        raise


if __name__ == '__main__':
    try:
        bot_logger.info('=' * 50)
        bot_logger.info('بدء تشغيل البوت...')
        bot_logger.info('=' * 50)

        from keep_alive import keep_alive
        keep_alive()

        asyncio.run(main())

    except KeyboardInterrupt:
        bot_logger.info('تم إيقاف البوت')

    except Exception as e:
        bot_logger.critical('فشل تشغيل البوت', exc_info=True)
        sys.exit(1)