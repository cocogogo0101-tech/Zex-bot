"""
مدير الإعدادات - يدير جميع إعدادات السيرفرات
"""

import discord
from database import db
from typing import Optional, Dict, Any
import helpers

class ConfigManager:
    """مدير الإعدادات الشامل"""

    def __init__(self):
        self.cache = {}  # تخزين مؤقت للإعدادات

    # ==================== الحصول على الإعدادات ====================

    async def get_settings(self, guild_id: str, use_cache: bool = True) -> Dict:
        """
        الحصول على إعدادات السيرفر

        Args:
            guild_id: معرف السيرفر
            use_cache: استخدام التخزين المؤقت؟

        Returns:
            dict: الإعدادات
        """
        # التحقق من التخزين المؤقت
        if use_cache and guild_id in self.cache:
            return self.cache[guild_id]

        # جلب من قاعدة البيانات
        settings = await db.get_settings(guild_id)

        # إنشاء إعدادات افتراضية إذا لم توجد
        if not settings:
            await db.init_guild(guild_id)
            settings = await db.get_settings(guild_id)

        # تخزين في الكاش
        if settings:
            self.cache[guild_id] = settings

        return settings or {}

    async def update_setting(self, guild_id: str, key: str, value: Any):
        """
        تحديث إعداد معين

        Args:
            guild_id: معرف السيرفر
            key: مفتاح الإعداد
            value: القيمة الجديدة
        """
        await db.update_setting(guild_id, key, value)

        # تحديث الكاش
        if guild_id in self.cache:
            self.cache[guild_id][key] = value
        else:
            # إعادة تحميل الإعدادات
            await self.get_settings(guild_id, use_cache=False)

    async def clear_cache(self, guild_id: str = None):
        """
        مسح التخزين المؤقت

        Args:
            guild_id: معرف السيرفر (None لمسح الكل)
        """
        if guild_id:
            self.cache.pop(guild_id, None)
        else:
            self.cache.clear()

    # ==================== إعدادات الترحيب ====================

    async def setup_welcome(
        self,
        guild_id: str,
        enabled: bool = None,
        channel_id: str = None,
        message: str = None,
        type: str = None
    ):
        """تكوين نظام الترحيب"""
        if enabled is not None:
            await self.update_setting(guild_id, 'welcome_enabled', 1 if enabled else 0)

        if channel_id is not None:
            await self.update_setting(guild_id, 'welcome_channel_id', channel_id)

        if message is not None:
            await self.update_setting(guild_id, 'welcome_message', message)

        if type is not None:
            await self.update_setting(guild_id, 'welcome_type', type)

    async def get_welcome_config(self, guild_id: str) -> Dict:
        """الحصول على إعدادات الترحيب"""
        settings = await self.get_settings(guild_id)
        return {
            'enabled': bool(settings.get('welcome_enabled', 1)),
            'channel_id': settings.get('welcome_channel_id'),
            'message': settings.get('welcome_message'),
            'type': settings.get('welcome_type', 'text')
        }

    # ==================== إعدادات الوداع ====================

    async def setup_goodbye(
        self,
        guild_id: str,
        enabled: bool = None,
        channel_id: str = None,
        message: str = None
    ):
        """تكوين نظام الوداع"""
        if enabled is not None:
            await self.update_setting(guild_id, 'goodbye_enabled', 1 if enabled else 0)

        if channel_id is not None:
            await self.update_setting(guild_id, 'goodbye_channel_id', channel_id)

        if message is not None:
            await self.update_setting(guild_id, 'goodbye_message', message)

    async def get_goodbye_config(self, guild_id: str) -> Dict:
        """الحصول على إعدادات الوداع"""
        settings = await self.get_settings(guild_id)
        return {
            'enabled': bool(settings.get('goodbye_enabled', 0)),
            'channel_id': settings.get('goodbye_channel_id'),
            'message': settings.get('goodbye_message')
        }

    # ==================== إعدادات السجلات ====================

    async def setup_logs(self, guild_id: str, channel_id: str = None):
        """تكوين قناة السجلات"""
        if channel_id is not None:
            await self.update_setting(guild_id, 'logs_channel_id', channel_id)

    async def get_logs_channel(self, guild_id: str) -> Optional[str]:
        """الحصول على قناة السجلات"""
        settings = await self.get_settings(guild_id)
        return settings.get('logs_channel_id')

    # ==================== إعدادات الأدوار ====================

    async def setup_support_role(self, guild_id: str, role_id: str = None):
        """تكوين دور الدعم"""
        if role_id is not None:
            await self.update_setting(guild_id, 'support_role_id', role_id)

    async def get_support_role(self, guild_id: str) -> Optional[str]:
        """الحصول على دور الدعم"""
        settings = await self.get_settings(guild_id)
        return settings.get('support_role_id')

    async def setup_autorole(self, guild_id: str, role_id: str = None):
        """تكوين الدور التلقائي"""
        if role_id is not None:
            await self.update_setting(guild_id, 'autorole_id', role_id)

    async def get_autorole(self, guild_id: str) -> Optional[str]:
        """الحصول على الدور التلقائي"""
        settings = await self.get_settings(guild_id)
        return settings.get('autorole_id')

    # ==================== إعدادات الحماية ====================

    async def setup_antispam(
        self,
        guild_id: str,
        enabled: bool = None,
        threshold: int = None
    ):
        """تكوين نظام مكافحة السبام"""
        if enabled is not None:
            await self.update_setting(guild_id, 'antispam_enabled', 1 if enabled else 0)

        if threshold is not None:
            await self.update_setting(guild_id, 'antispam_threshold', threshold)

    async def get_antispam_config(self, guild_id: str) -> Dict:
        """الحصول على إعدادات مكافحة السبام"""
        settings = await self.get_settings(guild_id)
        return {
            'enabled': bool(settings.get('antispam_enabled', 0)),
            'threshold': settings.get('antispam_threshold', 5)
        }

    async def setup_antilink(self, guild_id: str, enabled: bool = None):
        """تكوين نظام مكافحة الروابط"""
        if enabled is not None:
            await self.update_setting(guild_id, 'antilink_enabled', 1 if enabled else 0)

    async def get_antilink_enabled(self, guild_id: str) -> bool:
        """التحقق من تفعيل مكافحة الروابط"""
        settings = await self.get_settings(guild_id)
        return bool(settings.get('antilink_enabled', 0))

    async def setup_automod(self, guild_id: str, enabled: bool = None):
        """تكوين نظام المودريشن التلقائي"""
        if enabled is not None:
            await self.update_setting(guild_id, 'automod_enabled', 1 if enabled else 0)

    async def get_automod_enabled(self, guild_id: str) -> bool:
        """التحقق من تفعيل المودريشن التلقائي"""
        settings = await self.get_settings(guild_id)
        return bool(settings.get('automod_enabled', 0))

    # ==================== إعدادات المستويات ====================

    async def setup_leveling(self, guild_id: str, enabled: bool = None):
        """تكوين نظام المستويات"""
        if enabled is not None:
            await self.update_setting(guild_id, 'leveling_enabled', 1 if enabled else 0)

    async def get_leveling_enabled(self, guild_id: str) -> bool:
        """التحقق من تفعيل نظام المستويات"""
        settings = await self.get_settings(guild_id)
        return bool(settings.get('leveling_enabled', 0))

    async def get_leveling_config(self, guild_id: str):
        """
        الحصول على إعدادات نظام المستويات

        Returns:
            object: كائن يحتوي على الإعدادات
        """
        from types import SimpleNamespace

        settings = await self.get_settings(guild_id)

        # الإعدادات الافتراضية
        config = SimpleNamespace(
            enabled=bool(settings.get('leveling_enabled', 0)),
            xp_min=15,
            xp_max=25,
            cooldown=60,  # ثانية
            announce_levelup=True,
            levelup_channel=settings.get('levelup_channel_id'),
            level_roles={}  # {level: role_id}
        )

        # جلب إعدادات إضافية من leveling_config table إن وجدت
        try:
            from database import db

            cursor = await db.conn.execute(
                'SELECT * FROM leveling_config WHERE guild_id = ?',
                (guild_id,)
            )
            row = await cursor.fetchone()

            if row:
                row_dict = dict(row)
                config.xp_min = row_dict.get('xp_per_message_min', config.xp_min)
                config.xp_max = row_dict.get('xp_per_message_max', config.xp_max)
                config.cooldown = row_dict.get('message_cooldown', config.cooldown)
        except Exception as e:
            # استخدم الافتراضية إذا فشل
            pass

        return config

    async def get_protection_config(self, guild_id: str):
        """
        الحصول على إعدادات نظام الحماية

        Returns:
            object: كائن يحتوي على إعدادات الحماية
        """
        from types import SimpleNamespace

        settings = await self.get_settings(guild_id)

        config = SimpleNamespace(
            # Anti-Spam
            antispam_enabled=bool(settings.get('antispam_enabled', 0)),
            antispam_threshold=settings.get('antispam_threshold', 5),
            antispam_timewindow=10,  # ثواني

            # Anti-Link
            antilink_enabled=bool(settings.get('antilink_enabled', 0)),
            antilink_whitelist=[],  # قائمة النطاقات المسموحة

            # Auto-Mod
            automod_enabled=bool(settings.get('automod_enabled', 0)),

            # Mass Mention
            mass_mention_threshold=5,  # عدد المنشنات المسموح

            # Raid Protection
            raid_protection=False,
            raid_threshold=10,  # عدد الانضمامات
            raid_timewindow=60  # ثواني
        )

        return config

    # ==================== إعدادات عامة ====================

    async def setup_prefix(self, guild_id: str, prefix: str):
        """تكوين بريفكس الأوامر"""
        await self.update_setting(guild_id, 'prefix', prefix)

    async def get_prefix(self, guild_id: str) -> str:
        """الحصول على البريفكس"""
        settings = await self.get_settings(guild_id)
        return settings.get('prefix', '!')

    async def setup_language(self, guild_id: str, language: str):
        """تكوين لغة البوت"""
        await self.update_setting(guild_id, 'language', language)

    async def get_language(self, guild_id: str) -> str:
        """الحصول على اللغة"""
        settings = await self.get_settings(guild_id)
        return settings.get('language', 'ar')

    # ==================== التحقق من الإعدادات ====================

    async def validate_channel(self, guild: discord.Guild, channel_id: str) -> Optional[discord.TextChannel]:
        """
        التحقق من صحة القناة

        Returns:
            القناة إذا كانت صحيحة، None إذا لم توجد
        """
        if not channel_id:
            return None

        try:
            channel = guild.get_channel(int(channel_id))
            if isinstance(channel, discord.TextChannel):
                return channel
        except (ValueError, AttributeError):
            pass

        return None

    async def validate_role(self, guild: discord.Guild, role_id: str) -> Optional[discord.Role]:
        """
        التحقق من صحة الدور

        Returns:
            الدور إذا كان صحيحاً، None إذا لم يوجد
        """
        if not role_id:
            return None

        try:
            role = guild.get_role(int(role_id))
            return role
        except (ValueError, AttributeError):
            pass

        return None

    # ==================== الإعدادات الافتراضية ====================

    async def reset_settings(self, guild_id: str):
        """إعادة تعيين الإعدادات إلى الافتراضية"""
        # حذف الإعدادات الحالية
        await db.conn.execute('DELETE FROM settings WHERE guild_id = ?', (guild_id,))
        await db.conn.commit()

        # إنشاء إعدادات جديدة
        await db.init_guild(guild_id)

        # مسح من الكاش
        await self.clear_cache(guild_id)

    def get_default_welcome_message(self) -> str:
        """الحصول على رسالة الترحيب الافتراضية"""
        return "👋 مرحباً {mention}!\n\nأهلاً بك في **{server}**\nأنت العضو رقم **{membercount}**\n\nاستمتع بوقتك معنا! 🎉"

    def get_default_goodbye_message(self) -> str:
        """الحصول على رسالة الوداع الافتراضية"""
        return "👋 وداعاً **{user}**!\nنتمنى أن نراك قريباً."

    # ==================== استيراد/تصدير الإعدادات ====================

    async def export_settings(self, guild_id: str) -> Dict:
        """تصدير الإعدادات إلى dict"""
        settings = await self.get_settings(guild_id)
        return settings.copy() if settings else {}

    async def import_settings(self, guild_id: str, settings: Dict):
        """استيراد الإعدادات من dict"""
        for key, value in settings.items():
            if key != 'guild_id' and key != 'created_at':
                await self.update_setting(guild_id, key, value)

    # ==================== التحقق من الصلاحيات ====================

    async def check_channel_permissions(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel
    ) -> tuple[bool, list[str]]:
        """
        التحقق من صلاحيات البوت في القناة

        Returns:
            tuple: (لديه الصلاحيات؟, قائمة الصلاحيات المفقودة)
        """
        bot_member = guild.me
        permissions = channel.permissions_for(bot_member)

        required_perms = {
            'send_messages': 'إرسال رسائل',
            'embed_links': 'إدراج روابط',
            'read_messages': 'قراءة الرسائل',
            'read_message_history': 'قراءة سجل الرسائل'
        }

        missing = []
        for perm, name in required_perms.items():
            if not getattr(permissions, perm, False):
                missing.append(name)

        return len(missing) == 0, missing

    # ==================== معاينة الإعدادات ====================

    async def format_settings_preview(self, guild: discord.Guild) -> str:
        """
        تنسيق معاينة الإعدادات

        Returns:
            str: نص منسق بالإعدادات
        """
        settings = await self.get_settings(str(guild.id))

        lines = [f"⚙️ **إعدادات {guild.name}**\n"]

        # الترحيب
        welcome_status = '✅' if settings.get('welcome_enabled') else '❌'
        welcome_channel = f"<#{settings.get('welcome_channel_id')}>" if settings.get('welcome_channel_id') else 'غير محدد'
        lines.append(f"**🎉 الترحيب:** {welcome_status}")
        lines.append(f"└─ القناة: {welcome_channel}")
        lines.append(f"└─ النوع: {settings.get('welcome_type', 'text')}\n")

        # الوداع
        goodbye_status = '✅' if settings.get('goodbye_enabled') else '❌'
        goodbye_channel = f"<#{settings.get('goodbye_channel_id')}>" if settings.get('goodbye_channel_id') else 'غير محدد'
        lines.append(f"**👋 الوداع:** {goodbye_status}")
        lines.append(f"└─ القناة: {goodbye_channel}\n")

        # السجلات
        logs_channel = f"<#{settings.get('logs_channel_id')}>" if settings.get('logs_channel_id') else 'غير محدد'
        lines.append(f"**📝 السجلات:** {logs_channel}\n")

        # الحماية
        antispam = '✅' if settings.get('antispam_enabled') else '❌'
        antilink = '✅' if settings.get('antilink_enabled') else '❌'
        automod = '✅' if settings.get('automod_enabled') else '❌'
        lines.append(f"**🛡️ الحماية:**")
        lines.append(f"└─ Anti-Spam: {antispam}")
        lines.append(f"└─ Anti-Link: {antilink}")
        lines.append(f"└─ Auto-Mod: {automod}\n")

        # المستويات
        leveling = '✅' if settings.get('leveling_enabled') else '❌'
        lines.append(f"**📊 المستويات:** {leveling}\n")

        # الأدوار
        support_role = f"<@&{settings.get('support_role_id')}>" if settings.get('support_role_id') else 'غير محدد'
        autorole = f"<@&{settings.get('autorole_id')}>" if settings.get('autorole_id') else 'غير محدد'
        lines.append(f"**🎭 الأدوار:**")
        lines.append(f"└─ الدعم: {support_role}")
        lines.append(f"└─ التلقائي: {autorole}")

        return '\n'.join(lines)

# إنشاء نسخة عامة
config = ConfigManager()