"""
نظام الردود التلقائية الذكي
يدعم أنواع متعددة من المطابقة والشروط
"""

import discord
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from database import db
import helpers

class AutoResponseSystem:
    """نظام الردود التلقائية"""
    
    def __init__(self):
        self.cooldowns = {}  # تخزين أوقات الاستخدام الأخيرة
    
    async def check_and_respond(self, message: discord.Message) -> bool:
        """
        التحقق من الرسالة والرد إذا كانت مطابقة
        
        Returns:
            bool: True إذا تم الرد
        """
        if message.author.bot:
            return False
        
        guild_id = str(message.guild.id)
        
        # جلب جميع الردود التلقائية
        responses = await db.get_autoresponses(guild_id)
        
        if not responses:
            return False
        
        # البحث عن رد مطابق
        for response in responses:
            if await self._check_response(message, response):
                await self._send_response(message, response)
                return True
        
        return False
    
    async def _check_response(self, message: discord.Message, response: Dict) -> bool:
        """
        التحقق من مطابقة الرسالة للرد
        
        Returns:
            bool: True إذا كانت مطابقة
        """
        trigger = response['trigger'].lower()
        content = message.content.lower()
        trigger_type = response.get('trigger_type', 'contains')
        
        # التحقق من نوع المطابقة
        matches = False
        
        if trigger_type == 'exact':
            # مطابقة تامة
            matches = content == trigger
        
        elif trigger_type == 'contains':
            # يحتوي على
            matches = trigger in content
        
        elif trigger_type == 'startswith':
            # يبدأ بـ
            matches = content.startswith(trigger)
        
        elif trigger_type == 'endswith':
            # ينتهي بـ
            matches = content.endswith(trigger)
        
        elif trigger_type == 'regex':
            # تعبير نمطي
            try:
                matches = bool(re.search(trigger, content))
            except re.error:
                matches = False
        
        if not matches:
            return False
        
        # التحقق من القنوات المحددة
        if response.get('channels'):
            allowed_channels = response['channels']
            if str(message.channel.id) not in allowed_channels:
                return False
        
        # التحقق من الـ cooldown
        cooldown = response.get('cooldown', 0)
        if cooldown > 0:
            response_id = response['id']
            last_used = response.get('last_used')
            
            if last_used:
                last_time = datetime.fromisoformat(last_used)
                time_passed = (datetime.now() - last_time).total_seconds()
                
                if time_passed < cooldown:
                    return False
        
        # التحقق من الاحتمالية
        chance = response.get('chance', 100)
        if not helpers.roll_chance(chance):
            return False
        
        return True
    
    async def _send_response(self, message: discord.Message, response: Dict):
        """إرسال الرد"""
        response_text = response['response']
        
        # استبدال المتغيرات
        response_text = helpers.replace_variables(
            response_text,
            user=message.author.name,
            mention=message.author.mention,
            server=message.guild.name,
            channel=message.channel.name,
            membercount=message.guild.member_count
        )
        
        try:
            await message.channel.send(response_text)
            
            # تحديث وقت آخر استخدام
            await db.conn.execute(
                'UPDATE autoresponses SET last_used = ? WHERE id = ?',
                (datetime.now().isoformat(), response['id'])
            )
            await db.conn.commit()
        
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
    
    # ==================== إدارة الردود ====================
    
    async def add_response(
        self,
        guild_id: str,
        trigger: str,
        response: str,
        trigger_type: str = 'contains',
        chance: int = 100,
        cooldown: int = 0,
        channels: List[str] = None
    ) -> int:
        """
        إضافة رد تلقائي جديد
        
        Args:
            guild_id: معرف السيرفر
            trigger: المحفز (الكلمة/النص)
            response: الرد
            trigger_type: نوع المطابقة (exact, contains, startswith, endswith, regex)
            chance: احتمالية الرد (0-100)
            cooldown: فترة الانتظار بالثواني
            channels: قائمة معرفات القنوات المسموحة
        
        Returns:
            int: معرف الرد
        """
        return await db.add_autoresponse(
            guild_id,
            trigger,
            response,
            trigger_type,
            channels
        )
    
    async def remove_response(self, response_id: int) -> bool:
        """
        حذف رد تلقائي
        
        Args:
            response_id: معرف الرد
        
        Returns:
            bool: True إذا نجح الحذف
        """
        return await db.remove_autoresponse(response_id)
    
    async def toggle_response(self, response_id: int) -> bool:
        """
        تفعيل/تعطيل رد تلقائي
        
        Args:
            response_id: معرف الرد
        
        Returns:
            bool: True إذا نجحت العملية
        """
        return await db.toggle_autoresponse(response_id)
    
    async def get_responses(self, guild_id: str) -> List[Dict]:
        """
        الحصول على جميع الردود التلقائية
        
        Args:
            guild_id: معرف السيرفر
        
        Returns:
            list: قائمة الردود
        """
        return await db.get_autoresponses(guild_id)
    
    async def update_response(
        self,
        response_id: int,
        trigger: str = None,
        response: str = None,
        trigger_type: str = None,
        chance: int = None,
        cooldown: int = None
    ):
        """
        تحديث رد تلقائي
        
        Args:
            response_id: معرف الرد
            trigger: المحفز الجديد
            response: الرد الجديد
            trigger_type: نوع المطابقة الجديد
            chance: الاحتمالية الجديدة
            cooldown: الانتظار الجديد
        """
        updates = []
        values = []
        
        if trigger is not None:
            updates.append('trigger = ?')
            values.append(trigger)
        
        if response is not None:
            updates.append('response = ?')
            values.append(response)
        
        if trigger_type is not None:
            updates.append('trigger_type = ?')
            values.append(trigger_type)
        
        if chance is not None:
            updates.append('chance = ?')
            values.append(chance)
        
        if cooldown is not None:
            updates.append('cooldown = ?')
            values.append(cooldown)
        
        if updates:
            values.append(response_id)
            query = f"UPDATE autoresponses SET {', '.join(updates)} WHERE id = ?"
            await db.conn.execute(query, tuple(values))
            await db.conn.commit()
    
    # ==================== قوالب جاهزة ====================
    
    def get_template_responses(self) -> List[Dict]:
        """
        الحصول على قوالب ردود جاهزة
        
        Returns:
            list: قائمة القوالب
        """
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
        """
        إضافة قالب جاهز
        
        Args:
            guild_id: معرف السيرفر
            template_index: رقم القالب
        
        Returns:
            int: معرف الرد أو None
        """
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
    
    # ==================== التحليل والإحصائيات ====================
    
    async def get_response_stats(self, guild_id: str) -> Dict:
        """
        الحصول على إحصائيات الردود
        
        Returns:
            dict: الإحصائيات
        """
        responses = await self.get_responses(guild_id)
        
        total = len(responses)
        enabled = sum(1 for r in responses if r.get('enabled', 1))
        disabled = total - enabled
        
        types = {}
        for r in responses:
            t = r.get('trigger_type', 'contains')
            types[t] = types.get(t, 0) + 1
        
        return {
            'total': total,
            'enabled': enabled,
            'disabled': disabled,
            'by_type': types
        }
    
    async def search_responses(
        self,
        guild_id: str,
        query: str = None,
        trigger_type: str = None,
        enabled: bool = None
    ) -> List[Dict]:
        """
        البحث في الردود التلقائية
        
        Args:
            guild_id: معرف السيرفر
            query: نص البحث
            trigger_type: نوع المطابقة للتصفية
            enabled: الحالة للتصفية
        
        Returns:
            list: قائمة الردود المطابقة
        """
        responses = await self.get_responses(guild_id)
        
        results = []
        for response in responses:
            # تطبيق التصفية
            if enabled is not None and bool(response.get('enabled', 1)) != enabled:
                continue
            
            if trigger_type and response.get('trigger_type') != trigger_type:
                continue
            
            if query:
                query_lower = query.lower()
                trigger_lower = response['trigger'].lower()
                response_lower = response['response'].lower()
                
                if query_lower not in trigger_lower and query_lower not in response_lower:
                    continue
            
            results.append(response)
        
        return results
    
    # ==================== التنسيق ====================
    
    def format_response_list(self, responses: List[Dict], page: int = 1, per_page: int = 10) -> str:
        """
        تنسيق قائمة الردود
        
        Args:
            responses: قائمة الردود
            page: رقم الصفحة
            per_page: عدد العناصر في الصفحة
        
        Returns:
            str: نص منسق
        """
        if not responses:
            return 'لا توجد ردود تلقائية.'
        
        start = (page - 1) * per_page
        end = start + per_page
        page_responses = responses[start:end]
        
        lines = [f'📝 **الردود التلقائية** (الصفحة {page}/{(len(responses)-1)//per_page + 1})\n']
        
        for i, response in enumerate(page_responses, start=start + 1):
            status = '✅' if response.get('enabled', 1) else '❌'
            trigger = response['trigger']
            trigger_type = response.get('trigger_type', 'contains')
            response_text = helpers.truncate_text(response['response'], 50)
            
            lines.append(
                f'**{i}.** {status} `ID:{response["id"]}`\n'
                f'└─ المحفز: `{trigger}` ({trigger_type})\n'
                f'└─ الرد: {response_text}\n'
            )
        
        return '\n'.join(lines)
    
    def format_response_detail(self, response: Dict) -> str:
        """
        تنسيق تفاصيل رد واحد
        
        Args:
            response: بيانات الرد
        
        Returns:
            str: نص منسق
        """
        status = '✅ مفعل' if response.get('enabled', 1) else '❌ معطل'
        
        lines = [
            f'📝 **تفاصيل الرد #{response["id"]}**\n',
            f'**الحالة:** {status}',
            f'**المحفز:** `{response["trigger"]}`',
            f'**نوع المطابقة:** {response.get("trigger_type", "contains")}',
            f'**الرد:** {response["response"]}',
            f'**الاحتمالية:** {response.get("chance", 100)}%',
            f'**الانتظار:** {response.get("cooldown", 0)} ثانية'
        ]
        
        if response.get('channels'):
            channels = ', '.join([f'<#{ch}>' for ch in response['channels']])
            lines.append(f'**القنوات المحددة:** {channels}')
        else:
            lines.append('**القنوات المحددة:** جميع القنوات')
        
        if response.get('last_used'):
            last_used = helpers.format_datetime(response['last_used'])
            lines.append(f'**آخر استخدام:** {last_used}')
        
        return '\n'.join(lines)

# إنشاء نسخة عامة
autoresponse_system = AutoResponseSystem()