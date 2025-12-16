"""
event_messages.py - Clean & Enhanced
=====================================
معالجة الرسائل مع جميع الأنظمة

Features:
✅ معالجة الرسائل بشكل آمن
✅ نظام الحماية (Anti-spam, Anti-link, Auto-mod)
✅ الردود التلقائية
✅ نظام المستويات (XP)
✅ إحصائيات الرسائل
✅ Guards شاملة
"""

import discord
from system_autoresponse import autoresponse_system
from system_leveling import leveling_system
from system_protection import protection_system
from database import db
from logger import bot_logger
from config_manager import config


async def process_message(message: discord.Message):
    """معالجة رسالة واردة"""
    try:
        # ==================== Guards ====================

        # تجاهل البوتات
        if not message or message.author.bot:
            return

        # تجاهل الرسائل الخاصة
        if not message.guild:
            return

        # تجاهل الرسائل الفارغة
        if not message.content and not message.attachments:
            return

        guild_id = str(message.guild.id)

        # ==================== نظام الحماية ====================

        try:
            should_delete, reason = await protection_system.check_message(message)

            if should_delete:
                await protection_system.take_action(message, reason)
                bot_logger.security_alert(
                    'message_deleted',
                    f'{message.author.name} في {message.guild.name}: {reason}'
                )
                return  # توقف هنا - الرسالة محذوفة

        except Exception as e:
            bot_logger.error(f'خطأ في protection_system: {e}')
            # نكمل - الحماية فشلت لكن لا نوقف المعالجة

        # ==================== الردود التلقائية ====================

        try:
            # التحقق من الردود التلقائية
            responded = await autoresponse_system.check_and_respond(message)

            if responded:
                bot_logger.debug(f'رد تلقائي لـ {message.author.name} في {message.guild.name}')

        except Exception as e:
            bot_logger.error(f'خطأ في autoresponse_system: {e}')

        # ==================== نظام المستويات ====================

        try:
            # معالجة XP
            leveling_enabled = await config.get_leveling_enabled(guild_id)

            if leveling_enabled:
                result = await leveling_system.process_message(message)

                if result and result.get('leveled_up'):
                    bot_logger.info(
                        f'ترقية مستوى: {message.author.name} '
                        f'المستوى {result["old_level"]} → {result["level"]}'
                    )

        except Exception as e:
            bot_logger.error(f'خطأ في leveling_system: {e}')

        # ==================== إحصائيات ====================

        try:
            # زيادة عداد الرسائل في الإحصائيات
            await db.increment_stat(guild_id, 'messages', 1)

        except Exception as e:
            bot_logger.error(f'خطأ في increment_stat: {e}')

        # ملاحظة: تم معالجة الرسالة بنجاح
        # bot_logger.debug(f'تمت معالجة رسالة من {message.author.name}')

    except Exception as e:
        bot_logger.exception(
            f'خطأ غير متوقع في process_message '
            f'(المستخدم: {message.author.name}, السيرفر: {message.guild.name})',
            e
        )