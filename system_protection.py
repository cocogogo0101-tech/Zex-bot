# ==================== system_protection.py ====================
"""
system_protection.py - Ultimate Version
========================================
نظام الحماية الشامل

Features:
✅ Anti-Spam متقدم
✅ Anti-Link مع whitelist
✅ Auto-Mod مع كلمات محظورة
✅ Raid Protection
✅ Mass Mention Protection
✅ Duplicate Message Detection
✅ Caps Lock Detection
✅ Auto-actions (warn, timeout, kick, ban)
"""

import discord
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from database import db
from config_manager import config
import helpers
from logger import bot_logger
import re


class ProtectionSystem:
    """نظام الحماية الشامل والمتقدم"""

    def __init__(self):
        # Spam tracking: {user_id: [messages]}
        self.message_cache = defaultdict(list)

        # Duplicate tracking: {user_id: {content_hash: count}}
        self.duplicate_cache = defaultdict(lambda: defaultdict(int))

        # Raid tracking: {guild_id: [join_times]}
        self.raid_tracker = defaultdict(list)

        # Violation tracking: {user_id: violation_count}
        self.violations = defaultdict(int)

    # ==================== Main Check ====================

    async def check_message(self, message: discord.Message) -> Tuple[bool, Optional[str]]:
        """
        فحص رسالة شامل

        Returns:
            (يجب الحذف؟, السبب)
        """
        if not message or not message.guild or message.author.bot:
            return False, None

        # تجاهل المشرفين
        if helpers.is_mod(message.author):
            return False, None

        guild_id = str(message.guild.id)
        protection_config = await config.get_protection_config(guild_id)

        # Anti-Spam
        if protection_config.antispam_enabled:
            is_spam, reason = await self._check_spam(message, protection_config)
            if is_spam:
                return True, reason

        # Anti-Link
        if protection_config.antilink_enabled:
            has_link = await self._check_links(message, protection_config)
            if has_link:
                return True, 'رابط غير مسموح'

        # Auto-Mod (Blacklisted Words)
        if protection_config.automod_enabled:
            has_bad_word = await self._check_blacklist(message)
            if has_bad_word:
                return True, 'كلمة محظورة'

        # Mass Mention
        if len(message.mentions) >= protection_config.mass_mention_threshold:
            return True, f'منشن جماعي ({len(message.mentions)} منشنات)'

        # Caps Lock (اختياري)
        if self._check_caps(message.content):
            return True, 'كلام بحروف كبيرة فقط'

        # Duplicate Messages
        if await self._check_duplicate(message):
            return True, 'رسائل مكررة'

        return False, None

    # ==================== Spam Detection ====================

    async def _check_spam(
        self,
        message: discord.Message,
        protection_config
    ) -> Tuple[bool, Optional[str]]:
        """فحص السبام"""
        user_id = message.author.id

        # إضافة الرسالة للكاش
        self.message_cache[user_id].append(message)

        # تنظيف الرسائل القديمة
        now = datetime.now()
        timewindow = protection_config.antispam_timewindow

        self.message_cache[user_id] = [
            msg for msg in self.message_cache[user_id]
            if (now - msg.created_at).total_seconds() < timewindow
        ]

        # التحقق
        threshold = protection_config.antispam_threshold
        message_count = len(self.message_cache[user_id])

        if message_count >= threshold:
            return True, f'سبام ({message_count} رسائل في {timewindow} ثوانٍ)'

        return False, None

    # ==================== Link Detection ====================

    async def _check_links(
        self,
        message: discord.Message,
        protection_config
    ) -> bool:
        """فحص الروابط"""
        if not helpers.contains_link(message.content):
            return False

        # التحقق من Whitelist
        if protection_config.antilink_whitelist:
            links = helpers.extract_links(message.content)
            for link in links:
                # التحقق إذا كان الرابط في whitelist
                is_whitelisted = any(
                    domain in link.lower()
                    for domain in protection_config.antilink_whitelist
                )
                if not is_whitelisted:
                    return True
            return False

        # لا whitelist = حذف جميع الروابط
        return True

    # ==================== Blacklist Words ====================

    async def _check_blacklist(self, message: discord.Message) -> bool:
        """فحص الكلمات المحظورة"""
        guild_id = str(message.guild.id)
        blacklist = await db.get_blacklist_words(guild_id)

        if not blacklist:
            return False

        content_lower = message.content.lower()

        for entry in blacklist:
            word = entry['word'].lower()

            # مطابقة بسيطة
            if word in content_lower:
                bot_logger.security_alert(
                    'blacklist_word',
                    f'{message.author.name} استخدم: {word}'
                )
                return True

        return False

    # ==================== Caps Detection ====================

    def _check_caps(self, text: str, threshold: float = 0.7) -> bool:
        """
        فحص الحروف الكبيرة الزائدة

        Args:
            text: النص
            threshold: النسبة المئوية للحروف الكبيرة

        Returns:
            True إذا تجاوز الحد
        """
        if not text or len(text) < 10:  # رسائل قصيرة مسموحة
            return False

        # حساب نسبة الحروف الكبيرة
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return False

        caps_count = sum(1 for c in letters if c.isupper())
        caps_ratio = caps_count / len(letters)

        return caps_ratio > threshold

    # ==================== Duplicate Detection ====================

    async def _check_duplicate(self, message: discord.Message) -> bool:
        """فحص الرسائل المكررة"""
        user_id = message.author.id
        content_hash = helpers.generate_hash(message.content[:100])

        # زيادة العداد
        self.duplicate_cache[user_id][content_hash] += 1

        # تنظيف بعد دقيقة
        # (في تطبيق حقيقي: استخدم task scheduler)

        # إذا أرسل نفس الرسالة 3 مرات
        if self.duplicate_cache[user_id][content_hash] >= 3:
            return True

        return False

    # ==================== Action Taking ====================

    async def take_action(self, message: discord.Message, reason: str):
        """اتخاذ إجراء ضد المخالفة"""
        try:
            # حذف الرسالة
            await message.delete()

            # زيادة عداد المخالفات
            user_id = message.author.id
            self.violations[user_id] += 1
            violation_count = self.violations[user_id]

            # إجراءات تلقائية حسب عدد المخالفات
            if violation_count >= 5:
                # حظر مؤقت لساعة
                try:
                    await message.author.timeout(
                        discord.utils.utcnow() + timedelta(hours=1),
                        reason=f'مخالفات متكررة ({violation_count}): {reason}'
                    )
                    await message.channel.send(
                        f'⚠️ {message.author.mention} تم إسكاتك لساعة واحدة بسبب المخالفات المتكررة.',
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass

            elif violation_count >= 3:
                # تحذير
                await message.channel.send(
                    f'⚠️ {message.author.mention} تحذير أخير! المخالفة التالية ستؤدي لإسكاتك.',
                    delete_after=5
                )

            else:
                # رسالة بسيطة
                await message.channel.send(
                    f'⚠️ {message.author.mention} تم حذف رسالتك: {reason}',
                    delete_after=5
                )

            # تسجيل
            await db.add_log(
                str(message.guild.id),
                'message_delete_auto',
                str(message.author.id),
                reason=reason,
                details=f'Violations: {violation_count}'
            )

            bot_logger.security_alert(
                'auto_moderation',
                f'{message.author.name} - {reason} (#{violation_count})'
            )

        except discord.NotFound:
            pass  # الرسالة محذوفة بالفعل
        except discord.Forbidden:
            bot_logger.error(f'لا يمكن حذف رسالة {message.author.name}')
        except Exception as e:
            bot_logger.exception('خطأ في take_action', e)

    # ==================== Raid Protection ====================

    async def check_raid(self, guild: discord.Guild, member: discord.Member) -> bool:
        """
        فحص الـ raid (انضمام جماعي سريع)

        Returns:
            True إذا كان raid
        """
        guild_id = str(guild.id)
        protection_config = await config.get_protection_config(guild_id)

        if not protection_config.raid_protection:
            return False

        # إضافة وقت الانضمام
        self.raid_tracker[guild_id].append(datetime.now())

        # تنظيف القديم
        timewindow = protection_config.raid_timewindow
        now = datetime.now()

        self.raid_tracker[guild_id] = [
            t for t in self.raid_tracker[guild_id]
            if (now - t).total_seconds() < timewindow
        ]

        # التحقق
        threshold = protection_config.raid_threshold
        join_count = len(self.raid_tracker[guild_id])

        if join_count >= threshold:
            bot_logger.security_alert(
                'RAID_DETECTED',
                f'{guild.name}: {join_count} انضمامات في {timewindow} ثوانٍ'
            )
            return True

        return False

    # ==================== Cleanup ====================

    async def cleanup(self):
        """تنظيف دوري للكاش"""
        # تنظيف message_cache
        now = datetime.now()
        for user_id in list(self.message_cache.keys()):
            self.message_cache[user_id] = [
                msg for msg in self.message_cache[user_id]
                if (now - msg.created_at).total_seconds() < 60
            ]

            if not self.message_cache[user_id]:
                del self.message_cache[user_id]

        # تنظيف duplicate_cache
        self.duplicate_cache.clear()

        # تنظيف violations (بعد 10 دقائق)
        for user_id in list(self.violations.keys()):
            if self.violations[user_id] > 0:
                self.violations[user_id] -= 1
            if self.violations[user_id] == 0:
                del self.violations[user_id]


# ==================== system_tickets.py ====================
"""
system_tickets.py - Ultimate Version (نفس الكود السابق مع تحسينات بسيطة)
"""

import discord
import asyncio
from datetime import datetime
from typing import Optional
from database import db
from config_manager import config
import embeds
import helpers
from logger import bot_logger


class TicketSystem:
    """نظام التكتات المتقدم"""

    async def create_ticket(
        self,
        guild: discord.Guild,
        user: discord.User,
        reason: Optional[str] = None
    ) -> Optional[discord.TextChannel]:
        """إنشاء تكت جديد"""
        try:
            # الحصول على دور الدعم
            support_role_id = await config.get_support_role(str(guild.id))

            # إنشاء اسم فريد
            timestamp = datetime.now().strftime('%m%d%H%M%S')
            channel_name = f'ticket-{user.name}-{timestamp}'[:100]  # Discord limit

            # الصلاحيات
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }

            # إضافة دور الدعم
            if support_role_id:
                role = guild.get_role(int(support_role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )

            # إنشاء القناة
            channel = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                reason=f'تكت بواسطة {user}',
                topic=f'تكت من {user.name} | السبب: {reason or "غير محدد"}'
            )

            # حفظ في DB
            await db.create_ticket(str(channel.id), str(guild.id), str(user.id), reason)

            # رسالة الترحيب
            embed = embeds.ticket_created_embed(user, reason)
            view = TicketControlView()
            await channel.send(content=f'{user.mention}', embed=embed, view=view)

            # تسجيل
            await db.add_log(
                str(guild.id),
                'ticket_open',
                str(user.id),
                reason=reason,
                details=f'Channel: {channel.id}'
            )

            bot_logger.info(f'تكت جديد: {channel.name} في {guild.name}')
            return channel

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن إنشاء تكت في {guild.name}')
            return None
        except Exception as e:
            bot_logger.exception(f'خطأ في create_ticket: {guild.name}', e)
            return None

    async def close_ticket(
        self,
        channel: discord.TextChannel,
        closer: discord.User
    ) -> bool:
        """إغلاق تكت"""
        try:
            # التحقق من أنها قناة تكت
            ticket = await db.get_ticket(str(channel.id))
            if not ticket:
                return False

            # التحقق من الصلاحيات
            if not await self._can_close_ticket(channel, closer, ticket):
                return False

            # تحديث DB
            await db.close_ticket(str(channel.id), str(closer.id))

            # رسالة الإغلاق
            embed = embeds.ticket_closed_embed(closer)
            await channel.send(embed=embed)

            # تسجيل
            await db.add_log(
                str(channel.guild.id),
                'ticket_close',
                ticket['opener_id'],
                str(closer.id),
                details=f'Channel: {channel.id}'
            )

            bot_logger.info(f'تم إغلاق تكت: {channel.name}')

            # الانتظار ثم الحذف
            await asyncio.sleep(3)
            await channel.delete(reason=f'تكت مغلق بواسطة {closer}')

            return True

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن إغلاق {channel.name}')
            return False
        except Exception as e:
            bot_logger.exception(f'خطأ في close_ticket: {channel.name}', e)
            return False

    async def _can_close_ticket(
        self,
        channel: discord.TextChannel,
        closer: discord.User,
        ticket: dict
    ) -> bool:
        """التحقق من صلاحية الإغلاق"""
        # صاحب التكت
        if str(closer.id) == ticket['opener_id']:
            return True

        # المشرفين
        if isinstance(closer, discord.Member):
            if helpers.is_mod(closer):
                return True

            # دور الدعم
            support_role_id = await config.get_support_role(str(channel.guild.id))
            if support_role_id:
                if any(r.id == int(support_role_id) for r in closer.roles):
                    return True

        return False


class TicketControlView(discord.ui.View):
    """أزرار التحكم بالتكت"""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='إغلاق التكت', style=discord.ButtonStyle.red, emoji='🔒', custom_id='close_ticket')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        success = await ticket_system.close_ticket(interaction.channel, interaction.user)

        if not success:
            await interaction.followup.send('❌ لا يمكنك إغلاق هذا التكت.', ephemeral=True)


class TicketPanelView(discord.ui.View):
    """لوحة إنشاء التكتات"""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='فتح تكت', style=discord.ButtonStyle.green, emoji='🎫', custom_id='open_ticket')
    async def open_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())


class TicketModal(discord.ui.Modal, title='فتح تكت جديد'):
    """نموذج إنشاء تكت"""

    reason = discord.ui.TextInput(
        label='السبب',
        placeholder='اشرح سبب فتح التكت...',
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = await ticket_system.create_ticket(
            interaction.guild,
            interaction.user,
            self.reason.value
        )

        if channel:
            await interaction.followup.send(f'✅ تم إنشاء تكتك: {channel.mention}', ephemeral=True)
        else:
            await interaction.followup.send('❌ فشل إنشاء التكت', ephemeral=True)


# ==================== system_warnings.py ====================
"""
system_warnings.py - Ultimate Version
"""

import discord
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from database import db
import embeds
from logger import bot_logger


class WarningSystem:
    """نظام التحذيرات الذكي"""

    # الإجراءات التلقائية
    AUTO_ACTIONS = {
        3: ('timeout', 10),  # 10 دقائق
        5: ('timeout', 60),  # ساعة
        7: 'kick',
        10: 'ban'
    }

    async def warn_user(
        self,
        guild: discord.Guild,
        user: discord.User,
        moderator: discord.User,
        reason: str
    ) -> Dict:
        """
        تحذير مستخدم

        Returns:
            معلومات التحذير
        """
        try:
            # إضافة التحذير
            warn_id = await db.add_warning(
                str(guild.id),
                str(user.id),
                str(moderator.id),
                reason
            )

            # عدد التحذيرات
            warn_count = await db.get_warning_count(str(guild.id), str(user.id))

            # تسجيل
            await db.add_log(
                str(guild.id),
                'warn',
                str(user.id),
                str(moderator.id),
                reason=reason
            )

            # الإجراءات التلقائية
            auto_action = None
            if warn_count in self.AUTO_ACTIONS:
                action_result = await self._execute_auto_action(
                    guild,
                    user,
                    moderator,
                    warn_count
                )
                auto_action = action_result

            bot_logger.moderation_action(
                'WARN',
                f'{user.name} ({user.id})',
                f'{moderator.name} ({moderator.id})',
                f'{reason} (#{warn_count})'
            )

            return {
                'warn_id': warn_id,
                'warn_count': warn_count,
                'auto_action': auto_action
            }

        except Exception as e:
            bot_logger.exception('خطأ في warn_user', e)
            return {
                'warn_id': 0,
                'warn_count': 0,
                'auto_action': None
            }

    async def _execute_auto_action(
        self,
        guild: discord.Guild,
        user: discord.User,
        moderator: discord.User,
        warn_count: int
    ) -> Optional[str]:
        """تنفيذ الإجراء التلقائي"""
        member = guild.get_member(user.id)
        if not member:
            return None

        action_config = self.AUTO_ACTIONS[warn_count]
        reason = f'إجراء تلقائي - {warn_count} تحذيرات'

        try:
            if isinstance(action_config, tuple):
                action, duration = action_config

                if action == 'timeout':
                    await member.timeout(
                        discord.utils.utcnow() + timedelta(minutes=duration),
                        reason=reason
                    )
                    return f'إسكات لـ {duration} دقيقة'

            elif action_config == 'kick':
                await member.kick(reason=reason)
                return 'طرد من السيرفر'

            elif action_config == 'ban':
                await member.ban(reason=reason, delete_message_days=1)
                return 'حظر من السيرفر'

        except discord.Forbidden:
            bot_logger.error(f'لا يمكن تنفيذ الإجراء التلقائي على {member.name}')
        except Exception as e:
            bot_logger.exception('خطأ في _execute_auto_action', e)

        return None

    async def remove_warning(self, warn_id: int) -> bool:
        """حذف تحذير"""
        try:
            return await db.remove_warning(warn_id)
        except Exception as e:
            bot_logger.exception(f'خطأ في remove_warning: {warn_id}', e)
            return False

    async def clear_warnings(self, guild_id: str, user_id: str):
        """مسح جميع تحذيرات مستخدم"""
        try:
            await db.clear_warnings(guild_id, user_id)
            bot_logger.info(f'تم مسح تحذيرات {user_id} في {guild_id}')
        except Exception as e:
            bot_logger.exception(f'خطأ في clear_warnings: {guild_id}:{user_id}', e)

    async def get_warnings(self, guild_id: str, user_id: str) -> List[Dict]:
        """الحصول على تحذيرات مستخدم"""
        try:
            return await db.get_warnings(guild_id, user_id)
        except Exception as e:
            bot_logger.exception(f'خطأ في get_warnings: {guild_id}:{user_id}', e)
            return []

    async def get_warning_count(self, guild_id: str, user_id: str) -> int:
        """عدد تحذيرات مستخدم"""
        try:
            return await db.get_warning_count(guild_id, user_id)
        except Exception as e:
            bot_logger.exception(f'خطأ في get_warning_count: {guild_id}:{user_id}', e)
            return 0


# ==================== النسخ العامة ====================

protection_system = ProtectionSystem()
ticket_system = TicketSystem()
warning_system = WarningSystem()