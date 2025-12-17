"""
system_autoresponse.py - ENHANCED VERSION
==========================================
نظام الردود التلقائية المحسّن مع Logging مفصل

التحديثات:
✅ Logging مفصل لكل خطوة
✅ معالجة أخطاء أفضل
✅ تحسينات الأداء
✅ دعم متغيرات محسّن
"""

import discord
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from database import db
import helpers
from logger import bot_logger


class AutoResponseSystem:
    """نظام الردود التلقائية الذكي"""
    
    def __init__(self):
        self.cooldowns = {}  # {user_id: {response_id: last_time}}
        bot_logger.info('✅ تم تهيئة نظام الردود التلقائية')
    
    async def check_and_respond(self, message: discord.Message) -> bool:
        """
        التحقق من الرسالة والرد إذا كانت مطابقة
        
        Returns:
            bool: True إذا تم الرد
        """
        try:
            # Guard: تجاهل البوتات
            if message.author.bot:
                return False
            
            # Guard: تجاهل الرسائل بدون محتوى
            if not message.content:
                return False
            
            guild_id = str(message.guild.id)
            
            bot_logger.debug(
                f'🔍 فحص ردود تلقائية: {message.author.name} - "{message.content[:30]}..."'
            )
            
            # جلب جميع الردود التلقائية
            responses = await db.get_autoresponses(guild_id)
            
            if not responses:
                bot_logger.debug(f'📝 لا توجد ردود تلقائية في {message.guild.name}')
                return False
            
            bot_logger.debug(f'📝 تم جلب {len(responses)} رد تلقائي')
            
            # البحث عن رد مطابق
            for response in responses:
                # تخطي الردود المعطلة
                if not response.get('enabled', 1):
                    continue
                
                bot_logger.debug(
                    f'  🔎 فحص: {response["trigger"]} '
                    f'({response.get("trigger_type", "contains")})'
                )
                
                if await self._check_response(message, response):
                    # وجدنا مطابقة!
                    await self._send_response(message, response)
                    return True
            
            bot_logger.debug('❌ لا توجد ردود مطابقة')
            return False
        
        except Exception as e:
            bot_logger.exception('خطأ في check_and_respond', e)
            return False
    
    async def _check_response(self, message: discord.Message, response: Dict) -> bool:
        """
        التحقق من مطابقة الرسالة للرد
        
        Returns:
            bool: True إذا كانت مطابقة
        """
        try:
            trigger = response['trigger'].lower()
            content = message.content.lower()
            trigger_type = response.get('trigger_type', 'contains')
            
            # 1️⃣ التحقق من نوع المطابقة
            matches = False
            
            if trigger_type == 'exact':
                matches = content == trigger
                bot_logger.debug(f'    exact: {content} == {trigger} -> {matches}')
            
            elif trigger_type == 'contains':
                matches = trigger in content
                bot_logger.debug(f'    contains: {trigger} in {content} -> {matches}')
            
            elif trigger_type == 'startswith':
                matches = content.startswith(trigger)
                bot_logger.debug(f'    startswith: {content}.startswith({trigger}) -> {matches}')
            
            elif trigger_type == 'endswith':
                matches = content.endswith(trigger)
                bot_logger.debug(f'    endswith: {content}.endswith({trigger}) -> {matches}')
            
            elif trigger_type == 'regex':
                try:
                    matches = bool(re.search(trigger, content, re.IGNORECASE))
                    bot_logger.debug(f'    regex: {trigger} -> {matches}')
                except re.error as e:
                    bot_logger.error(f'Regex خاطئ: {trigger} - {e}')
                    matches = False
            
            if not matches:
                return False
            
            bot_logger.debug(f'    ✅ مطابقة نجحت!')
            
            # 2️⃣ التحقق من القنوات المحددة
            if response.get('channels'):
                allowed_channels = response['channels'].split(',') if isinstance(response['channels'], str) else response['channels']
                if str(message.channel.id) not in allowed_channels:
                    bot_logger.debug(f'    ❌ القناة {message.channel.id} غير مسموحة')
                    return False
            
            # 3️⃣ التحقق من الـ cooldown
            cooldown = response.get('cooldown', 0)
            if cooldown > 0:
                response_id = response['id']
                user_id = str(message.author.id)
                
                # التحقق من آخر استخدام
                if user_id in self.cooldowns and response_id in self.cooldowns[user_id]:
                    last_time = self.cooldowns[user_id][response_id]
                    time_passed = (datetime.now() - last_time).total_seconds()
                    
                    if time_passed < cooldown:
                        remaining = cooldown - time_passed
                        bot_logger.debug(
                            f'    ⏰ Cooldown: باقي {remaining:.1f} ثانية'
                        )
                        return False
            
            # 4️⃣ التحقق من الاحتمالية (chance)
            chance = response.get('chance', 100)
            if chance < 100:
                if not helpers.roll_chance(chance):
                    bot_logger.debug(f'    🎲 فشل احتمال {chance}%')
                    return False
                bot_logger.debug(f'    🎲 نجح احتمال {chance}%')
            
            bot_logger.debug(f'    ✅ جميع الشروط مستوفاة!')
            return True
        
        except Exception as e:
            bot_logger.exception(f'خطأ في _check_response', e)
            return False
    
    async def _send_response(self, message: discord.Message, response: Dict):
        """إرسال الرد"""
        try:
            response_text = response['response']
            response_id = response['id']
            user_id = str(message.author.id)
            
            bot_logger.info(
                f'📤 إرسال رد تلقائي #{response_id}: '
                f'{response["trigger"]} -> {message.author.name}'
            )
            
            # استبدال المتغيرات
            response_text = helpers.replace_variables(
                response_text,
                user=message.author.name,
                mention=message.author.mention,
                server=message.guild.name,
                channel=message.channel.name,
                membercount=message.guild.member_count
            )
            
            # إرسال الرد
            try:
                await message.channel.send(response_text)
                bot_logger.success(f'✅ تم إرسال الرد بنجاح')
            except discord.Forbidden:
                bot_logger.error(f'❌ Forbidden: لا يمكن الإرسال في {message.channel.name}')
                return
            except discord.HTTPException as e:
                bot_logger.error(f'❌ HTTPException: {e}')
                return
            
            # تحديث وقت آخر استخدام
            try:
                await db.update_autoresponse(
                    response_id,
                    last_used=datetime.now().isoformat()
                )
                
                # تحديث cooldown في الذاكرة
                if user_id not in self.cooldowns:
                    self.cooldowns[user_id] = {}
                self.cooldowns[user_id][response_id] = datetime.now()
                
                bot_logger.debug('✅ تم تحديث last_used و cooldown')
            
            except Exception as e:
                bot_logger.error(f'خطأ في تحديث last_used: {e}')
        
        except Exception as e:
            bot_logger.exception('خطأ في _send_response', e)
    
    # ==================== إدارة الردود ====================
    
    async def add_response(
        self,
        guild_id: str,
        trigger: str,
        response: str,
        trigger_type: str = 'contains',
        chance: int = 100,
        cooldown: int = 0,
        channels: Optional[str] = None
    ) -> int:
        """
        إضافة رد تلقائي جديد
        
        Returns:
            int: معرف الرد (0 إن فشل)
        """
        try:
            response_id = await db.add_autoresponse(
                guild_id,
                trigger,
                response,
                trigger_type,
                chance,
                cooldown,
                1,  # enabled
                channels
            )
            
            if response_id:
                bot_logger.success(
                    f'✅ تم إضافة رد تلقائي #{response_id}: '
                    f'{trigger} -> {response[:30]}...'
                )
            else:
                bot_logger.error('❌ فشل إضافة الرد التلقائي')
            
            return response_id
        
        except Exception as e:
            bot_logger.exception('خطأ في add_response', e)
            return 0
    
    async def remove_response(self, response_id: int) -> bool:
        """حذف رد تلقائي"""
        try:
            success = await db.remove_autoresponse(response_id)
            
            if success:
                bot_logger.success(f'✅ تم حذف رد تلقائي #{response_id}')
            else:
                bot_logger.error(f'❌ فشل حذف رد تلقائي #{response_id}')
            
            return success
        
        except Exception as e:
            bot_logger.exception(f'خطأ في remove_response: {response_id}', e)
            return False
    
    async def toggle_response(self, response_id: int) -> bool:
        """تفعيل/تعطيل رد تلقائي"""
        try:
            new_state = await db.toggle_autoresponse(response_id)
            
            status = 'مفعل' if new_state else 'معطل'
            bot_logger.success(f'✅ الرد #{response_id} الآن {status}')
            
            return True
        
        except Exception as e:
            bot_logger.exception(f'خطأ في toggle_response: {response_id}', e)
            return False
    
    async def get_responses(self, guild_id: str) -> List[Dict]:
        """الحصول على جميع الردود التلقائية"""
        try:
            responses = await db.get_autoresponses(guild_id)
            bot_logger.debug(f'📝 تم جلب {len(responses)} رد من DB')
            return responses
        
        except Exception as e:
            bot_logger.exception(f'خطأ في get_responses: {guild_id}', e)
            return []
    
    async def update_response(
        self,
        response_id: int,
        trigger: str = None,
        response: str = None,
        trigger_type: str = None,
        chance: int = None,
        cooldown: int = None
    ) -> bool:
        """تحديث رد تلقائي"""
        try:
            success = await db.update_autoresponse(
                response_id,
                trigger=trigger,
                response=response,
                trigger_type=trigger_type,
                chance=chance,
                cooldown=cooldown
            )
            
            if success:
                bot_logger.success(f'✅ تم تحديث رد تلقائي #{response_id}')
            
            return success
        
        except Exception as e:
            bot_logger.exception(f'خطأ في update_response: {response_id}', e)
            return False
    
    # ==================== القوالب الجاهزة ====================
    
    def get_template_responses(self) -> List[Dict]:
        """الحصول على قوالب ردود جاهزة"""
        return [
            {
                'trigger': 'السلام عليكم',
                'response': 'وعليكم السلام ورحمة الله وبركاته 🌹',
                'trigger_type': 'contains',
                'description': 'رد على السلام'
            },
            {
                'trigger': 'صباح الخير',
                'response': 'صباح النور والسرور ☀️',
                'trigger_type': 'contains',
                'description': 'رد على صباح الخير'
            },
            {
                'trigger': 'مساء الخير',
                'response': 'مساء النور والسرور 🌙',
                'trigger_type': 'contains',
                'description': 'رد على مساء الخير'
            },
            {
                'trigger': 'شكرا',
                'response': 'العفو! ❤️',
                'trigger_type': 'contains',
                'description': 'رد على الشكر'
            },
            {
                'trigger': 'كيف حالك',
                'response': 'الحمد لله، أنا بوت ولا أحتاج أن أكون بخير 😅',
                'trigger_type': 'contains',
                'description': 'رد على السؤال عن الحال'
            },
            {
                'trigger': 'من أنت',
                'response': 'أنا بوت إدارة وترحيب في خدمتكم! 🤖',
                'trigger_type': 'contains',
                'description': 'رد على من أنت'
            },
            {
                'trigger': 'هلا',
                'response': 'هلا والله! 👋',
                'trigger_type': 'exact',
                'description': 'رد على هلا'
            },
            {
                'trigger': 'أهلين',
                'response': 'أهلين وسهلين! 😊',
                'trigger_type': 'exact',
                'description': 'رد على أهلين'
            }
        ]
    
    async def add_template(self, guild_id: str, template_index: int) -> Optional[int]:
        """إضافة قالب جاهز"""
        templates = self.get_template_responses()
        
        if 0 <= template_index < len(templates):
            template = templates[template_index]
            return await self.add_response(
                guild_id,
                template['trigger'],
                template['response'],
                template['trigger_type']
            )
        
        return None
    
    # ==================== الإحصائيات ====================
    
    async def get_response_stats(self, guild_id: str) -> Dict:
        """الحصول على إحصائيات الردود"""
        try:
            return await db.get_autoresponse_stats(guild_id)
        except Exception as e:
            bot_logger.exception(f'خطأ في get_response_stats: {guild_id}', e)
            return {'total': 0, 'enabled': 0, 'disabled': 0, 'by_type': {}}
    
    async def search_responses(
        self,
        guild_id: str,
        query: str = None,
        trigger_type: str = None,
        enabled: bool = None
    ) -> List[Dict]:
        """البحث في الردود التلقائية"""
        try:
            if query:
                return await db.search_autoresponses(guild_id, query)
            else:
                responses = await self.get_responses(guild_id)
                
                # تطبيق الفلاتر
                if trigger_type:
                    responses = [r for r in responses if r.get('trigger_type') == trigger_type]
                
                if enabled is not None:
                    responses = [r for r in responses if bool(r.get('enabled', 1)) == enabled]
                
                return responses
        
        except Exception as e:
            bot_logger.exception(f'خطأ في search_responses: {guild_id}', e)
            return []


# إنشاء نسخة عامة
autoresponse_system = AutoResponseSystem()

bot_logger.success('✅ تم تحميل نظام الردود التلقائية المحسّن')