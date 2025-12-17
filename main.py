"""
main.py - FIXED VERSION
========================
البوت الرئيسي مع الترتيب الصحيح للمعالجة

التحديثات:
✅ ترتيب on_message محسّن
✅ الردود التلقائية لها الأولوية
✅ Error handling محسّن
✅ Logging مفصل
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

from system_polls import poll_system
from system_invites import invite_tracker
from system_analytics import analytics_system

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

from cmd_autoresponse import setup_autoresponse_commands
from cmd_polls import setup_poll_commands
from cmd_invites import setup_invite_commands
from cmd_analytics import setup_analytics_commands

# ==================== Global State ====================

commands_registered = False
shutdown_initiated = False

# ==================== الأحداث الأساسية ====================

@bot.event
async def on_ready():
    global commands_registered

    try:
        bot_logger.info('='*50)
        bot_logger.info(f'البوت متصل: {bot.user.name} (ID: {bot.user.id})')
        bot_logger.info(f'Discord.py Version: {discord.__version__}')
        bot_logger.info(f'Python Version: {sys.version}')
        bot_logger.info('='*50)

        # الاتصال بقاعدة البيانات
        await db.connect()

        # تسجيل الأوامر
        if not commands_registered:
            bot_logger.info('بدء تسجيل الأوامر...')

            setup_moderation_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الإدارة')
            
            setup_config_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الإعدادات')
            
            setup_utility_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر المنفعة')
            
            setup_fun_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر المرح')
            
            setup_info_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر المعلومات')
            
            setup_autoresponse_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الردود التلقائية')
            
            setup_poll_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الاستطلاعات')
            
            setup_invite_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الدعوات')
            
            setup_analytics_commands(bot)
            bot_logger.success('✅ تم تسجيل أوامر الإحصائيات')

            commands_registered = True

        # بدء الأنظمة
        poll_system.start(bot)
        bot_logger.success('✅ نظام الاستطلاعات جاهز')

        # تخزين الدعوات
        for guild in bot.guilds:
            try:
                await invite_tracker.cache_invites(guild)
                bot_logger.debug(f'✅ تم تخزين دعوات {guild.name}')
            except Exception as e:
                bot_logger.warning(f'⚠️ فشل تخزين دعوات {guild.name}: {e}')

        # Views الدائمة
        bot.add_view(TicketControlView())
        bot.add_view(TicketPanelView())
        bot_logger.success('✅ تم إضافة Views الدائمة')

        # Sync الأوامر
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            bot_logger.success(f'✅ تم مزامنة {len(synced)} أمر على Guild: {GUILD_ID}')
        else:
            synced = await bot.tree.sync()
            bot_logger.success(f'✅ تم مزامنة {len(synced)} أمر عالمياً')

        # تحديث الحالة
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'{len(bot.guilds)} سيرفر | /help'
            )
        )

        # رسالة النجاح
        bot_logger.info('='*50)
        bot_logger.success(f'✅ البوت جاهز: {bot.user.name}')
        bot_logger.success(f'✅ السيرفرات: {len(bot.guilds)}')
        bot_logger.success(f'✅ الأعضاء: {sum(g.member_count for g in bot.guilds)}')
        bot_logger.info('='*50)
        bot_logger.success('🚀 البوت يعمل الآن!')
        bot_logger.info('='*50)

    except Exception as e:
        bot_logger.exception('💥 خطأ حرج في on_ready', e)
        raise

# ==================== أحداث الأعضاء ====================

@bot.event
async def on_member_join(member):
    """عند انضمام عضو"""
    try:
        await handle_member_join(member)
    except Exception as e:
        bot_logger.exception(f'خطأ في on_member_join: {member.name}', e)

@bot.event
async def on_member_remove(member):
    """عند مغادرة عضو"""
    try:
        await handle_member_remove(member)
    except Exception as e:
        bot_logger.exception(f'خطأ في on_member_remove: {member.name}', e)

# ==================== معالجة الرسائل (الأهم!) ====================

@bot.event
async def on_message(message):
    """
    معالجة الرسائل - الترتيب مهم جداً!
    
    الترتيب الجديد:
    1. ✅ معالجة الرسالة (تشمل الردود التلقائية)
    2. الاختصارات العربية
    3. أوامر البوت
    """
    try:
        # تجاهل الرسائل الخاصة
        if not message.guild:
            return
        
        # ✅ 1. معالجة الرسالة (الردود التلقائية + الحماية + المستويات)
        await process_message(message)
        
        # ✅ 2. الاختصارات العربية
        await process_aliases(bot, message)
        
        # ✅ 3. أوامر البوت العادية
        await bot.process_commands(message)
    
    except Exception as e:
        bot_logger.exception(
            f'خطأ في on_message: {message.author.name if message else "Unknown"}',
            e
        )

# ==================== أحداث السجلات ====================

@bot.event
async def on_message_delete(message):
    """عند حذف رسالة"""
    try:
        await log_message_delete(message)
    except Exception as e:
        bot_logger.error(f'خطأ في on_message_delete: {e}')

@bot.event
async def on_message_edit(before, after):
    """عند تعديل رسالة"""
    try:
        await log_message_edit(before, after)
    except Exception as e:
        bot_logger.error(f'خطأ في on_message_edit: {e}')

@bot.event
async def on_voice_state_update(member, before, after):
    """عند تحديث حالة صوتية"""
    try:
        await handle_voice_state_update(member, before, after)
    except Exception as e:
        bot_logger.error(f'خطأ في on_voice_state_update: {e}')

# ==================== معالجة الأخطاء ====================

@bot.event
async def on_command_error(ctx, error):
    """معالجة أخطاء الأوامر"""
    if isinstance(error, commands.CommandNotFound):
        return  # تجاهل الأوامر غير الموجودة
    
    bot_logger.error(f'خطأ في أمر {ctx.command}: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    """معالجة الأخطاء العامة"""
    bot_logger.exception(f'خطأ في حدث {event}', sys.exc_info()[1])

# ==================== Shutdown ====================

async def shutdown(bot):
    """إيقاف آمن للبوت"""
    global shutdown_initiated
    if shutdown_initiated:
        return
    shutdown_initiated = True
    
    bot_logger.info('⏸️ بدء إيقاف البوت...')
    
    try:
        await db.close()
        bot_logger.success('✅ تم إغلاق قاعدة البيانات')
    except:
        pass
    
    try:
        await bot.close()
        bot_logger.success('✅ تم إغلاق اتصال البوت')
    except:
        pass
    
    bot_logger.info('👋 تم إيقاف البوت بنجاح')

def handle_signal(sig):
    """معالجة إشارات الإيقاف"""
    asyncio.create_task(shutdown(bot))

# ==================== التشغيل ====================

async def main():
    """الدالة الرئيسية"""
    try:
        # إضافة معالجات الإشارات (Linux/Mac فقط)
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))
        
        async with bot:
            await bot.start(TOKEN)
    
    except Exception as e:
        bot_logger.exception('💥 خطأ حرج في main', e)
        await shutdown(bot)
        raise

if __name__ == '__main__':
    try:
        bot_logger.info('='*50)
        bot_logger.info('🚀 بدء تشغيل البوت...')
        bot_logger.info('='*50)
        
        # Keep-alive (Replit فقط)
        try:
            from keep_alive import keep_alive
            keep_alive()
            bot_logger.info('✅ Keep-alive مفعل')
        except ImportError:
            bot_logger.debug('Keep-alive غير متوفر (طبيعي)')
        
        # تشغيل البوت
        asyncio.run(main())
    
    except KeyboardInterrupt:
        bot_logger.info('⌨️ تم إيقاف البوت بـ Ctrl+C')
    
    except Exception:
        bot_logger.critical('💥 فشل تشغيل البوت', exc_info=True)
        sys.exit(1)