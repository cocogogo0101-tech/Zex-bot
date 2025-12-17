"""
event_messages.py - FIXED VERSION
==================================
معالجة الرسائل مع الترتيب الصحيح للأنظمة

الترتيب الجديد:
1. ✅ الردود التلقائية (أولاً!)
2. نظام الحماية
3. نظام المستويات
4. الإحصائيات

Features:
✅ الردود التلقائية تعمل قبل أي شيء
✅ Guards شاملة
✅ Error handling محسّن
✅ Logging مفصل
"""

import discord
from system_autoresponse import autoresponse_system
from system_leveling import leveling_system
from system_protection import protection_system
from database import db
from logger import bot_logger
from config_manager import config


async def process_message(message: discord.Message):
    """
    معالجة رسالة واردة
    
    الترتيب مهم جداً!
    """
    try:
        # ==================== Guards الأساسية ====================
        
        # تجاهل الرسائل الفارغة أو None
        if not message:
            return
        
        # تجاهل البوتات (مهم!)
        if message.author.bot:
            return
        
        # تجاهل الرسائل الخاصة
        if not message.guild:
            return
        
        # تجاهل الرسائل بدون محتوى
        if not message.content and not message.attachments:
            return
        
        guild_id = str(message.guild.id)
        
        bot_logger.debug(
            f'📨 رسالة من {message.author.name}: {message.content[:50]}'
        )
        
        # ==================== 1️⃣ الردود التلقائية (أولاً!) ====================
        
        try:
            # ✅ هنا السحر! الردود التلقائية قبل أي شيء
            responded = await autoresponse_system.check_and_respond(message)
            
            if responded:
                bot_logger.info(
                    f'✅ رد تلقائي ناجح: {message.author.name} في {message.guild.name}'
                )
                # لا نوقف المعالجة - نكمل للأنظمة الأخرى
        
        except Exception as e:
            bot_logger.error(f'❌ خطأ في الردود التلقائية: {e}')
            # نكمل حتى لو فشلت الردود التلقائية
        
        # ==================== 2️⃣ نظام الحماية ====================
        
        try:
            # فحص الرسالة
            should_delete, reason = await protection_system.check_message(message)
            
            if should_delete:
                # اتخاذ الإجراء
                await protection_system.take_action(message, reason)
                
                bot_logger.security_alert(
                    'message_blocked',
                    f'{message.author.name} - {reason}'
                )
                
                # توقف هنا - الرسالة محذوفة
                return
        
        except Exception as e:
            bot_logger.error(f'❌ خطأ في نظام الحماية: {e}')
            # نكمل حتى لو فشلت الحماية
        
        # ==================== 3️⃣ نظام المستويات ====================
        
        try:
            # التحقق من التفعيل
            leveling_enabled = await config.get_leveling_enabled(guild_id)
            
            if leveling_enabled:
                # معالجة XP
                result = await leveling_system.process_message(message)
                
                if result and result.get('leveled_up'):
                    bot_logger.info(
                        f'🎉 ترقية مستوى: {message.author.name} '
                        f'المستوى {result["old_level"]} → {result["level"]}'
                    )
        
        except Exception as e:
            bot_logger.error(f'❌ خطأ في نظام المستويات: {e}')
            # نكمل حتى لو فشل نظام المستويات
        
        # ==================== 4️⃣ الإحصائيات ====================
        
        try:
            # زيادة عداد الرسائل
            await db.increment_stat(guild_id, 'messages', 1)
        
        except Exception as e:
            bot_logger.error(f'❌ خطأ في الإحصائيات: {e}')
        
        # ==================== انتهت المعالجة ====================
        
        bot_logger.debug(f'✅ تمت معالجة رسالة {message.author.name} بنجاح')
    
    except Exception as e:
        bot_logger.exception(
            f'💥 خطأ حرج في process_message '
            f'(المستخدم: {message.author.name}, السيرفر: {message.guild.name})',
            e
        )


# ==================== دالة مساعدة للتصحيح ====================

async def debug_message(message: discord.Message):
    """
    دالة تصحيح لمعرفة ما يحدث بالضبط
    
    استخدمها إذا كانت الردود لا تزال لا تعمل
    """
    print('='*50)
    print('🔍 DEBUG MESSAGE')
    print(f'المرسل: {message.author.name}')
    print(f'بوت؟ {message.author.bot}')
    print(f'السيرفر: {message.guild.name if message.guild else "DM"}')
    print(f'المحتوى: {message.content}')
    print(f'القناة: {message.channel.name if hasattr(message.channel, "name") else "Unknown"}')
    print('='*50)
    
    # جلب الردود التلقائية
    if message.guild:
        guild_id = str(message.guild.id)
        responses = await autoresponse_system.get_responses(guild_id)
        print(f'📝 عدد الردود المتاحة: {len(responses)}')
        
        for resp in responses:
            print(f'  - المحفز: {resp["trigger"]}')
            print(f'    النوع: {resp.get("trigger_type", "contains")}')
            print(f'    مفعل؟ {bool(resp.get("enabled", 1))}')
        print('='*50)