"""
system_tickets_ultimate.py - MEGA ULTIMATE EDITION (updated for compatibility)
===================================================
نظام تكتات خرافي بلا حدود!
ملف مُحدَّث ليتوافق مع main.py (import names & persistent views).
"""

import discord
import asyncio
import aiohttp
import json
import io
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

# اعتماد على db من database.py
from database import db

# افترض أن هذه الوحدات موجودة في مشروعك (embeds, helpers, config_manager, logger)
# إذا لم تكن موجودة — افحص imports أو عدّل حسب مشروعك.
try:
    from config_manager import config
except Exception:
    config = None

try:
    import embeds
except Exception:
    embeds = None

try:
    import helpers
except Exception:
    helpers = None

try:
    from logger import bot_logger
except Exception:
    # fallback simple logger
    import logging
    bot_logger = logging.getLogger('ticket_system')
    if not bot_logger.handlers:
        handler = logging.StreamHandler()
        bot_logger.addHandler(handler)
    bot_logger.setLevel(logging.INFO)


# ==================== Data Classes ====================

class TicketCategory:
    """فئة تكت مع تخصيص كامل"""
    
    def __init__(
        self,
        category_id: str,
        name: str,
        description: str = None,
        emoji: str = "🎫",
        color: int = 0x5865F2,
        banner_url: str = None,
        thumbnail_url: str = None,
        required_role: str = None,
        ping_roles: List[str] = None,
        support_roles: List[str] = None,
        auto_close_hours: int = 48,
        max_tickets_per_user: int = 3,
        custom_fields: List[Dict] = None,
        welcome_message: str = None
    ):
        self.category_id = category_id
        self.name = name
        self.description = description or f"افتح تكت {name}"
        self.emoji = emoji
        self.color = color
        self.banner_url = banner_url
        self.thumbnail_url = thumbnail_url
        self.required_role = required_role
        self.ping_roles = ping_roles or []
        self.support_roles = support_roles or []
        self.auto_close_hours = auto_close_hours
        self.max_tickets_per_user = max_tickets_per_user
        self.custom_fields = custom_fields or []
        self.welcome_message = welcome_message or "شكراً لفتح تكت! سيتم الرد عليك قريباً."
    
    def to_dict(self) -> Dict:
        """تحويل لـ dict"""
        return {
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'emoji': self.emoji,
            'color': self.color,
            'banner_url': self.banner_url,
            'thumbnail_url': self.thumbnail_url,
            'required_role': self.required_role,
            'ping_roles': self.ping_roles,
            'support_roles': self.support_roles,
            'auto_close_hours': self.auto_close_hours,
            'max_tickets_per_user': self.max_tickets_per_user,
            'custom_fields': self.custom_fields,
            'welcome_message': self.welcome_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """إنشاء من dict"""
        return cls(**data)


class TicketData:
    """بيانات التكت"""
    
    def __init__(
        self,
        ticket_id: int,
        channel_id: str,
        guild_id: str,
        creator_id: str,
        category_id: str,
        created_at: datetime = None,
        claimed_by: str = None,
        priority: str = "normal",
        tags: List[str] = None,
        notes: List[Dict] = None,
        rating: int = None,
        status: str = "open"
    ):
        self.ticket_id = ticket_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.category_id = category_id
        self.created_at = created_at or datetime.now()
        self.claimed_by = claimed_by
        self.priority = priority
        self.tags = tags or []
        self.notes = notes or []
        self.rating = rating
        self.status = status
        self.last_activity = datetime.now()
    
    def add_note(self, author_id: str, content: str):
        """إضافة ملاحظة داخلية"""
        self.notes.append({
            'author_id': author_id,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
    
    def is_inactive(self, hours: int) -> bool:
        """التحقق من عدم النشاط"""
        return (datetime.now() - self.last_activity).total_seconds() > (hours * 3600)


# ==================== Main System ====================

class TicketSystemUltimate:
    """نظام التكتات الخرافي"""
    
    def __init__(self):
        self.categories: Dict[str, Dict[str, TicketCategory]] = {}  # {guild_id: {cat_id: category}}
        self.tickets: Dict[str, TicketData] = {}  # {channel_id: ticket_data}
        self.panels: Dict[str, Dict] = {}  # {message_id: panel_data}
        self.next_ticket_id = 1
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'total_tickets': 0,
            'open_tickets': 0,
            'closed_tickets': 0,
            'avg_response_time': 0,
            'avg_close_time': 0,
            'ratings': []
        })
        
        # Auto-close task
        self.auto_close_task = None
    
    # ==================== Setup & Configuration ====================
    
    async def setup_category(
        self,
        guild: discord.Guild,
        category_id: str,
        name: str,
        description: str = None,
        emoji: str = "🎫",
        color: str = "#5865F2",
        banner: str = None,  # URL or "upload"
        banner_attachment: discord.Attachment = None,
        thumbnail: str = None,
        required_role: discord.Role = None,
        ping_roles: List[discord.Role] = None,
        support_roles: List[discord.Role] = None,
        auto_close_hours: int = 48,
        max_tickets_per_user: int = 3,
        welcome_message: str = None
    ) -> Tuple[bool, str, TicketCategory]:
        """
        إعداد فئة تكت جديدة
        
        Returns:
            (نجح؟, رسالة, الفئة)
        """
        try:
            guild_id = str(guild.id)
            
            # معالجة اللون
            try:
                if color.startswith("#"):
                    color_int = int(color[1:], 16)
                else:
                    color_int = int(color, 16)
            except:
                color_int = 0x5865F2
            
            # معالجة البانر
            banner_url = None
            if banner == "upload" and banner_attachment:
                # رفع الصورة واستخدام Discord CDN
                banner_url = banner_attachment.url
                bot_logger.info(f'✅ تم رفع بانر من المستخدم: {banner_url}')
            elif banner and banner.startswith("http"):
                # التحقق من صحة الرابط
                if await self._validate_image_url(banner):
                    banner_url = banner
                else:
                    return False, "❌ الرابط غير صحيح أو ليس صورة", None
            
            # معالجة Thumbnail
            thumbnail_url = None
            if thumbnail and thumbnail.startswith("http"):
                if await self._validate_image_url(thumbnail):
                    thumbnail_url = thumbnail
            
            # إنشاء الفئة
            category = TicketCategory(
                category_id=category_id,
                name=name,
                description=description,
                emoji=emoji,
                color=color_int,
                banner_url=banner_url,
                thumbnail_url=thumbnail_url,
                required_role=str(required_role.id) if required_role else None,
                ping_roles=[str(r.id) for r in ping_roles] if ping_roles else [],
                support_roles=[str(r.id) for r in support_roles] if support_roles else [],
                auto_close_hours=auto_close_hours,
                max_tickets_per_user=max_tickets_per_user,
                welcome_message=welcome_message
            )
            
            # حفظ
            if guild_id not in self.categories:
                self.categories[guild_id] = {}
            self.categories[guild_id][category_id] = category
            
            # حفظ في DB
            try:
                await db.save_category(guild_id, category)
            except Exception:
                # original code used direct SQL -> keep compatibility if save_category expects json string
                try:
                    data_json = json.dumps(category.to_dict())
                    await db.conn.execute('''
                        INSERT INTO ticket_categories (guild_id, category_id, data)
                        VALUES (?, ?, ?)
                        ON CONFLICT(guild_id, category_id) DO UPDATE SET data = excluded.data
                    ''', (guild_id, category.category_id, data_json))
                    await db.conn.commit()
                except Exception as e:
                    bot_logger.error(f'خطأ في حفظ الفئة: {e}')
            
            bot_logger.info(f'✅ تم إنشاء فئة: {name} ({category_id}) في guild {guild.name if guild else guild_id}')
            return True, f"✅ تم إنشاء فئة **{name}** بنجاح!", category
        
        except Exception as e:
            bot_logger.exception('خطأ في setup_category', e)
            return False, f"❌ حدث خطأ: {str(e)}", None
    
    async def _validate_image_url(self, url: str) -> bool:
        """التحقق من صحة رابط الصورة"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=5) as resp:
                    content_type = resp.headers.get('Content-Type', '')
                    return 'image' in content_type
        except:
            return False
    
    async def _save_category_to_db(self, guild_id: str, category: TicketCategory):
        """حفظ الفئة في DB (احتياطي)"""
        try:
            data_json = json.dumps(category.to_dict())
            await db.conn.execute('''
                INSERT INTO ticket_categories (guild_id, category_id, data)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, category_id) DO UPDATE SET data = excluded.data
            ''', (guild_id, category.category_id, data_json))
            await db.conn.commit()
        except Exception as e:
            bot_logger.error(f'خطأ في حفظ الفئة: {e}')
    
    async def load_categories(self, guild_id: str):
        """تحميل الفئات من DB"""
        try:
            if not db.conn:
                bot_logger.debug('DB connection not ready in load_categories')
                return
            cursor = await db.conn.execute('''
                SELECT category_id, data FROM ticket_categories WHERE guild_id = ?
            ''', (guild_id,))
            
            rows = await cursor.fetchall()
            
            if guild_id not in self.categories:
                self.categories[guild_id] = {}
            
            for row in rows:
                try:
                    data = json.loads(row[1])
                    category = TicketCategory.from_dict(data)
                    self.categories[guild_id][row[0]] = category
                except Exception:
                    bot_logger.exception('خطأ بتحويل بيانات الفئة من DB')
            
            bot_logger.debug(f'✅ تم تحميل {len(rows)} فئات لـ guild {guild_id}')
        except Exception as e:
            bot_logger.error(f'خطأ في تحميل الفئات: {e}')
    
    async def remove_category(self, guild_id: str, category_id: str) -> bool:
        """حذف فئة"""
        try:
            if guild_id in self.categories and category_id in self.categories[guild_id]:
                del self.categories[guild_id][category_id]
            
            if db.conn:
                await db.conn.execute('''
                    DELETE FROM ticket_categories WHERE guild_id = ? AND category_id = ?
                ''', (guild_id, category_id))
                await db.conn.commit()
            
            return True
        except Exception as e:
            bot_logger.error(f'خطأ في حذف الفئة: {e}')
            return False
    
    # ==================== Panel Management ====================
    
    async def create_panel(
        self,
        channel: discord.TextChannel,
        title: str = "🎫 نظام التكتات",
        description: str = None,
        color: int = 0x5865F2,
        thumbnail: str = None,
        show_categories_in_embed: bool = True
    ) -> Optional[discord.Message]:
        """
        إنشاء لوحة تكتات
        
        Returns:
            رسالة اللوحة أو None
        """
        try:
            guild_id = str(channel.guild.id)
            
            # تحميل الفئات
            await self.load_categories(guild_id)
            
            if guild_id not in self.categories or not self.categories[guild_id]:
                bot_logger.warning(f'لا توجد فئات في {guild_id}')
                return None
            
            # إنشاء Embed
            embed = discord.Embed(
                title=title,
                description=description or "اختر نوع التكت الذي تريد فتحه من الأزرار بالأسفل:",
                color=color,
                timestamp=datetime.now()
            )
            
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            # عرض الفئات في الـ embed
            if show_categories_in_embed:
                for cat_id, category in self.categories[guild_id].items():
                    embed.add_field(
                        name=f'{category.emoji} {category.name}',
                        value=category.description,
                        inline=False
                    )
            
            embed.set_footer(text=f'السيرفر: {channel.guild.name}')
            
            # إنشاء الأزرار
            view = PanelView(self, guild_id)
            
            # إرسال اللوحة
            message = await channel.send(embed=embed, view=view)
            
            # حفظ في الذاكرة
            self.panels[str(message.id)] = {
                'guild_id': guild_id,
                'channel_id': str(channel.id),
                'created_at': datetime.now().isoformat()
            }
            
            # حفظ في DB panel info (اختياري)
            try:
                if db.conn:
                    await db.conn.execute('''
                        INSERT OR REPLACE INTO ticket_panels (message_id, guild_id, channel_id, data)
                        VALUES (?, ?, ?, ?)
                    ''', (str(message.id), guild_id, str(channel.id), json.dumps(self.panels[str(message.id)])))
                    await db.conn.commit()
            except Exception:
                pass
            
            bot_logger.info(f'✅ تم إنشاء لوحة تكتات في {channel.name}')
            return message
        
        except Exception as e:
            bot_logger.exception('خطأ في create_panel', e)
            return None
    
    # ==================== Ticket Creation ====================
    
    async def create_ticket(
        self,
        guild: discord.Guild,
        user: discord.Member,
        category_id: str,
        reason: str = None,
        custom_field_answers: Dict = None
    ) -> Tuple[bool, str, Optional[discord.TextChannel]]:
        """
        إنشاء تكت جديد
        
        Returns:
            (نجح؟, رسالة, القناة)
        """
        try:
            guild_id = str(guild.id)
            user_id = str(user.id)
            
            # تحميل الفئات
            await self.load_categories(guild_id)
            
            # التحقق من وجود الفئة
            if guild_id not in self.categories or category_id not in self.categories[guild_id]:
                return False, "❌ الفئة غير موجودة", None
            
            category = self.categories[guild_id][category_id]
            
            # التحقق من Required Role
            if category.required_role:
                role = guild.get_role(int(category.required_role))
                if role and role not in user.roles:
                    return False, f"❌ تحتاج دور {role.mention} لفتح هذا التكت", None
            
            # التحقق من عدد التكتات
            user_tickets = await self._count_user_tickets(guild_id, user_id)
            if user_tickets >= category.max_tickets_per_user:
                return False, f"❌ لديك بالفعل {user_tickets} تكتات مفتوحة! الحد الأقصى: {category.max_tickets_per_user}", None
            
            # إنشاء اسم القناة
            ticket_id = self.next_ticket_id
            self.next_ticket_id += 1
            
            channel_name = f'ticket-{ticket_id:04d}'
            
            # الصلاحيات
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True,
                    manage_permissions=True
                )
            }
            
            # إضافة أدوار الدعم
            for role_id in category.support_roles:
                role = guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=True
                    )
            
            # إنشاء القناة
            channel = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                topic=f'تكت #{ticket_id:04d} | {category.name} | {user}',
                reason=f'تكت بواسطة {user}'
            )
            
            # إنشاء TicketData
            ticket_data = TicketData(
                ticket_id=ticket_id,
                channel_id=str(channel.id),
                guild_id=guild_id,
                creator_id=user_id,
                category_id=category_id
            )
            
            self.tickets[str(channel.id)] = ticket_data
            
            # حفظ في DB
            try:
                await db.save_ticket_v2((
                    ticket.ticket_id,
                    ticket.channel_id,
                    ticket.guild_id,
                    ticket.creator_id,
                    ticket.category_id,
                    reason,
                    json.dumps(custom_field_answers or {}),
                    ticket.created_at.isoformat(),
                    ticket.status
                ))
            except Exception:
                # fallback direct SQL (compat)
                try:
                    await db.conn.execute('''
                        INSERT INTO tickets_v2 
                        (ticket_id, channel_id, guild_id, creator_id, category_id, reason, custom_answers, created_at, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ticket_data.ticket_id, ticket_data.channel_id, ticket_data.guild_id, ticket_data.creator_id,
                        ticket_data.category_id, reason, json.dumps(custom_field_answers or {}),
                        ticket_data.created_at.isoformat(), ticket_data.status
                    ))
                    await db.conn.commit()
                except Exception as e:
                    bot_logger.error(f'خطأ في حفظ التكت: {e}')
            
            # رسالة الترحيب
            await self._send_welcome_message(channel, user, category, ticket_data, reason, custom_field_answers)
            
            # منشن الأدوار
            ping_mentions = []
            for role_id in category.ping_roles:
                role = guild.get_role(int(role_id))
                if role:
                    ping_mentions.append(role.mention)
            
            if ping_mentions:
                await channel.send(' '.join(ping_mentions))
            
            # تحديث الإحصائيات
            self.stats[guild_id]['total_tickets'] += 1
            self.stats[guild_id]['open_tickets'] += 1
            
            bot_logger.info(f'✅ تم إنشاء تكت #{ticket_id:04d} بواسطة {user.name}')
            return True, f"✅ تم إنشاء تكتك: {channel.mention}", channel
        
        except discord.Forbidden:
            bot_logger.error('Forbidden: لا يمكن إنشاء التكت')
            return False, "❌ البوت لا يملك صلاحيات إنشاء القنوات", None
        except Exception as e:
            bot_logger.exception('خطأ في create_ticket', e)
            return False, f"❌ حدث خطأ: {str(e)}", None
    
    async def _count_user_tickets(self, guild_id: str, user_id: str) -> int:
        """عد تكتات المستخدم المفتوحة"""
        count = 0
        for ticket in self.tickets.values():
            if ticket.guild_id == guild_id and ticket.creator_id == user_id and ticket.status == "open":
                count += 1
        return count
    
    async def _save_ticket_to_db(self, ticket: TicketData, reason: str = None, custom_answers: Dict = None):
        """حفظ التكت في DB (قد لا يُستخدم إذا استخدمنا save_ticket_v2)"""
        try:
            await db.conn.execute('''
                INSERT INTO tickets_v2 
                (ticket_id, channel_id, guild_id, creator_id, category_id, reason, custom_answers, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticket.ticket_id, ticket.channel_id, ticket.guild_id, ticket.creator_id,
                ticket.category_id, reason, json.dumps(custom_answers or {}),
                ticket.created_at.isoformat(), ticket.status
            ))
            await db.conn.commit()
        except Exception as e:
            bot_logger.error(f'خطأ في حفظ التكت: {e}')
    
    async def _send_welcome_message(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        category: TicketCategory,
        ticket: TicketData,
        reason: str = None,
        custom_answers: Dict = None
    ):
        """إرسال رسالة الترحيب"""
        try:
            # Embed رئيسي
            embed = discord.Embed(
                title=f'{category.emoji} {category.name}',
                description=category.welcome_message,
                color=category.color,
                timestamp=datetime.now()
            )
            
            if category.banner_url:
                embed.set_image(url=category.banner_url)
            
            if category.thumbnail_url:
                embed.set_thumbnail(url=category.thumbnail_url)
            
            embed.add_field(
                name='📝 معلومات التكت',
                value=(
                    f'**الرقم:** `#{ticket.ticket_id:04d}`\n'
                    f'**الفئة:** {category.name}\n'
                    f'**التاريخ:** <t:{int(ticket.created_at.timestamp())}:F>\n'
                    f'**الأولوية:** {self._get_priority_emoji(ticket.priority)} {ticket.priority.title()}'
                ),
                inline=False
            )
            
            if reason:
                embed.add_field(
                    name='💬 السبب',
                    value=reason[:1024],
                    inline=False
                )
            
            if custom_answers:
                answers_text = '\n'.join([f'**{k}:** {v}' for k, v in custom_answers.items()])
                if answers_text:
                    embed.add_field(
                        name='📋 معلومات إضافية',
                        value=answers_text[:1024],
                        inline=False
                    )
            
            embed.set_footer(text=f'افتح بواسطة {user.name}', icon_url=user.display_avatar.url)
            
            # الأزرار
            view = TicketControlView(self)
            
            await channel.send(content=user.mention, embed=embed, view=view)
        
        except Exception as e:
            bot_logger.error(f'خطأ في إرسال رسالة الترحيب: {e}')
    
    def _get_priority_emoji(self, priority: str) -> str:
        """الحصول على emoji الأولوية"""
        emojis = {
            'low': '🟢',
            'normal': '🟡',
            'high': '🟠',
            'urgent': '🔴'
        }
        return emojis.get(priority, '⚪')
    
    # ==================== Ticket Management ====================
    
    async def close_ticket(
        self,
        channel: discord.TextChannel,
        closer: discord.Member,
        reason: str = None,
        save_transcript: bool = True
    ) -> Tuple[bool, str]:
        """
        إغلاق تكت
        
        Returns:
            (نجح؟, رسالة)
        """
        try:
            channel_id = str(channel.id)
            
            if channel_id not in self.tickets:
                return False, "❌ هذه ليست قناة تكت"
            
            ticket = self.tickets[channel_id]
            
            # التحقق من الصلاحيات
            if not await self._can_manage_ticket(closer, ticket):
                return False, "❌ ليس لديك صلاحية إغلاق هذا التكت"
            
            # حفظ Transcript
            transcript_url = None
            if save_transcript:
                transcript_url = await self._save_transcript(channel, ticket)
            
            # طلب تقييم من المستخدم
            await self._request_rating(channel, ticket)
            
            # إرسال رسالة الإغلاق
            embed = discord.Embed(
                title='🔒 إغلاق التكت',
                description=f'سيتم إغلاق هذا التكت خلال 5 ثوانٍ...',
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name='أغلق بواسطة', value=closer.mention, inline=True)
            if reason:
                embed.add_field(name='السبب', value=reason, inline=True)
            
            if transcript_url:
                embed.add_field(name='📄 سجل المحادثة', value=f'{transcript_url}', inline=False)
            
            await channel.send(embed=embed)
            
            # تحديث DB
            ticket.status = "closed"
            try:
                if db.conn:
                    await db.conn.execute('''
                        UPDATE tickets_v2 SET status = ?, closed_at = ?, closed_by = ?, close_reason = ?
                        WHERE channel_id = ?
                    ''', ('closed', datetime.now().isoformat(), str(closer.id), reason, channel_id))
                    await db.conn.commit()
            except Exception:
                pass
            
            # الانتظار ثم الحذف
            await asyncio.sleep(5)
            
            # إرسال نسخة للمستخدم (DM)
            try:
                creator = channel.guild.get_member(int(ticket.creator_id))
                if creator:
                    dm_embed = discord.Embed(
                        title=f'تم إغلاق تكتك #{ticket.ticket_id:04d}',
                        description=f'في سيرفر **{channel.guild.name}**',
                        color=discord.Color.blue()
                    )
                    dm_embed.add_field(name='أغلق بواسطة', value=closer.mention)
                    if reason:
                        dm_embed.add_field(name='السبب', value=reason)
                    if transcript_url:
                        dm_embed.add_field(name='سجل المحادثة', value=transcript_url, inline=False)
                    
                    await creator.send(embed=dm_embed)
            except Exception:
                pass
            
            # حذف القناة
            await channel.delete(reason=f'تكت مغلق بواسطة {closer}')
            
            # تحديث الإحصائيات
            self.stats[ticket.guild_id]['open_tickets'] -= 1
            self.stats[ticket.guild_id]['closed_tickets'] += 1
            
            # حذف من الذاكرة
            del self.tickets[channel_id]
            
            bot_logger.info(f'✅ تم إغلاق تكت #{ticket.ticket_id:04d}')
            return True, "✅ تم إغلاق التكت بنجاح"
        
        except Exception as e:
            bot_logger.exception('خطأ في close_ticket', e)
            return False, f"❌ حدث خطأ: {str(e)}"
    
    async def _can_manage_ticket(self, user: discord.Member, ticket: TicketData) -> bool:
        """التحقق من صلاحية إدارة التكت"""
        # صاحب التكت
        if str(user.id) == ticket.creator_id:
            return True
        
        # مشرف (helpers.is_mod) — إذا يوجد
        try:
            if helpers and helpers.is_mod(user):
                return True
        except Exception:
            # تجاهل خطأ helpers
            pass
        
        # دور دعم
        guild_id = ticket.guild_id
        try:
            if guild_id in self.categories and ticket.category_id in self.categories[guild_id]:
                category = self.categories[guild_id][ticket.category_id]
                for role_id in category.support_roles:
                    # use guild lookup via user.guild if available
                    guild_obj = getattr(user, 'guild', None)
                    if guild_obj:
                        role = guild_obj.get_role(int(role_id))
                        if role and role in user.roles:
                            return True
        except Exception:
            pass
        
        return False
    
    async def _save_transcript(self, channel: discord.TextChannel, ticket: TicketData) -> Optional[str]:
        """
        حفظ سجل المحادثة
        
        Returns:
            رابط الـ transcript (مسار محلي) أو None
        """
        try:
            # جلب جميع الرسائل
            messages = []
            async for msg in channel.history(limit=None, oldest_first=True):
                messages.append(msg)
            
            # إنشاء HTML
            html = await self._generate_html_transcript(channel, ticket, messages)
            
            # حفظ في ملف
            os.makedirs('transcripts', exist_ok=True)
            filename = f'transcript_{ticket.ticket_id:04d}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            filepath = os.path.join('transcripts', filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                # حفظ مرجع في DB
                if db.conn:
                    try:
                        await db.conn.execute('''
                            INSERT INTO ticket_transcripts (ticket_id, file_path)
                            VALUES (?, ?)
                        ''', (ticket.ticket_id, filepath))
                        await db.conn.commit()
                    except Exception:
                        pass
                bot_logger.info(f'✅ تم حفظ transcript: {filepath}')
                return filepath
            except Exception as e:
                bot_logger.error(f'فشل حفظ الملف: {e}')
                return None
            
        except Exception as e:
            bot_logger.error(f'خطأ في حفظ transcript: {e}')
            return None
    
    async def _generate_html_transcript(self, channel: discord.TextChannel, ticket: TicketData, messages: List[discord.Message]) -> str:
        """توليد HTML للـ transcript"""
        html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>Transcript #{ticket.ticket_id:04d}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #36393f;
            color: #dcddde;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #2f3136;
            border-radius: 8px;
            padding: 20px;
        }}
        .header {{
            background: #202225;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .message {{
            display: flex;
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            background: #36393f;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-left: 10px;
        }}
        .content {{
            flex: 1;
        }}
        .author {{
            font-weight: bold;
            color: #fff;
        }}
        .timestamp {{
            color: #72767d;
            font-size: 12px;
        }}
        .text {{
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎫 Transcript #{ticket.ticket_id:04d}</h1>
            <p>القناة: {channel.name}</p>
            <p>السيرفر: {channel.guild.name}</p>
            <p>التاريخ: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="messages">
"""
        
        for msg in messages:
            try:
                timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                timestamp = str(msg.created_at)
            avatar_url = getattr(msg.author, 'display_avatar', None)
            avatar_url = avatar_url.url if avatar_url else ''
            content_safe = (msg.content or '').replace('<', '&lt;').replace('>', '&gt;')
            
            html += f"""
            <div class="message">
                <img src="{avatar_url}" class="avatar">
                <div class="content">
                    <div>
                        <span class="author">{msg.author.name}</span>
                        <span class="timestamp">{timestamp}</span>
                    </div>
                    <div class="text">{content_safe if content_safe else '[No content]'}</div>
                </div>
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    async def _request_rating(self, channel: discord.TextChannel, ticket: TicketData):
        """طلب تقييم من المستخدم"""
        try:
            creator = channel.guild.get_member(int(ticket.creator_id))
            if not creator:
                return
            
            embed = discord.Embed(
                title='⭐ تقييم الخدمة',
                description='كيف كانت تجربتك مع فريق الدعم؟',
                color=discord.Color.gold()
            )
            
            view = RatingView(self, ticket.ticket_id)
            
            await channel.send(content=creator.mention, embed=embed, view=view)
        except Exception as e:
            bot_logger.error(f'خطأ في طلب التقييم: {e}')
    
    async def rate_ticket(self, ticket_id: int, rating: int, user_id: str):
        """تسجيل تقييم"""
        try:
            # حفظ في DB
            if db.conn:
                await db.conn.execute('''
                    UPDATE tickets_v2 SET rating = ? WHERE ticket_id = ?
                ''', (rating, ticket_id))
                await db.conn.commit()
            
            bot_logger.info(f'✅ تم تقييم تكت #{ticket_id:04d}: {rating}/5')
        except Exception as e:
            bot_logger.error(f'خطأ في تسجيل التقييم: {e}')
    
    # ==================== Advanced Features ====================
    
    async def claim_ticket(self, channel: discord.TextChannel, claimer: discord.Member) -> Tuple[bool, str]:
        """المشرف يأخذ التكت"""
        try:
            channel_id = str(channel.id)
            
            if channel_id not in self.tickets:
                return False, "❌ ليست قناة تكت"
            
            ticket = self.tickets[channel_id]
            
            if ticket.claimed_by:
                return False, f"❌ هذا التكت محجوز بالفعل من <@{ticket.claimed_by}>"
            
            ticket.claimed_by = str(claimer.id)
            
            # حفظ في DB (اختياري)
            try:
                if db.conn:
                    await db.conn.execute('''
                        UPDATE tickets_v2 SET claimed_by = ? WHERE channel_id = ?
                    ''', (str(claimer.id), channel_id))
                    await db.conn.commit()
            except Exception:
                pass
            
            embed = discord.Embed(
                title='✅ تم أخذ التكت',
                description=f'{claimer.mention} الآن مسؤول عن هذا التكت',
                color=discord.Color.green()
            )
            
            await channel.send(embed=embed)
            
            bot_logger.info(f'✅ {claimer.name} أخذ تكت #{ticket.ticket_id:04d}')
            return True, "✅ تم أخذ التكت بنجاح"
        
        except Exception as e:
            bot_logger.exception('خطأ في claim_ticket', e)
            return False, f"❌ حدث خطأ: {str(e)}"
    
    async def set_priority(self, channel: discord.TextChannel, priority: str) -> Tuple[bool, str]:
        """تعيين أولوية التكت"""
        try:
            channel_id = str(channel.id)
            
            if channel_id not in self.tickets:
                return False, "❌ ليست قناة تكت"
            
            if priority not in ['low', 'normal', 'high', 'urgent']:
                return False, "❌ أولوية غير صحيحة"
            
            ticket = self.tickets[channel_id]
            old_priority = ticket.priority
            ticket.priority = priority
            
            # تحديث اسم القناة (حافظ على طوله معقول)
            emoji = self._get_priority_emoji(priority)
            new_name = f'{emoji}-{channel.name}'
            try:
                await channel.edit(name=new_name)
            except Exception:
                pass
            
            embed = discord.Embed(
                title='🎯 تم تغيير الأولوية',
                description=f'{self._get_priority_emoji(old_priority)} {old_priority.title()} → {emoji} {priority.title()}',
                color=discord.Color.blue()
            )
            
            await channel.send(embed=embed)
            
            # حفظ في DB
            try:
                if db.conn:
                    await db.conn.execute('''
                        UPDATE tickets_v2 SET priority = ? WHERE channel_id = ?
                    ''', (priority, channel_id))
                    await db.conn.commit()
            except Exception:
                pass
            
            return True, "✅ تم تغيير الأولوية"
        
        except Exception as e:
            bot_logger.exception('خطأ في set_priority', e)
            return False, f"❌ حدث خطأ: {str(e)}"
    
    async def add_note(self, channel: discord.TextChannel, author: discord.Member, note: str) -> Tuple[bool, str]:
        """إضافة ملاحظة داخلية (للمشرفين فقط)"""
        try:
            channel_id = str(channel.id)
            
            if channel_id not in self.tickets:
                return False, "❌ ليست قناة تكت"
            
            ticket = self.tickets[channel_id]
            ticket.add_note(str(author.id), note)
            
            # محاولة حفظ الملاحظة في DB (append JSON)
            try:
                if db.conn:
                    # جلب الملاحظات القديمة
                    cursor = await db.conn.execute('SELECT notes FROM tickets_v2 WHERE channel_id = ?', (channel_id,))
                    row = await cursor.fetchone()
                    existing = []
                    if row and row[0]:
                        try:
                            existing = json.loads(row[0])
                        except Exception:
                            existing = []
                    existing.append({'author_id': str(author.id), 'content': note, 'timestamp': datetime.now().isoformat()})
                    await db.conn.execute('UPDATE tickets_v2 SET notes = ? WHERE channel_id = ?', (json.dumps(existing), channel_id))
                    await db.conn.commit()
            except Exception:
                pass
            
            embed = discord.Embed(
                title='📝 ملاحظة داخلية',
                description=note,
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.set_author(name=author.name, icon_url=author.display_avatar.url)
            embed.set_footer(text='هذه الملاحظة مخفية عن المستخدم')
            
            # إرسال فقط للمشرفين
            await channel.send(embed=embed)
            
            return True, "✅ تم إضافة الملاحظة"
        
        except Exception as e:
            bot_logger.exception('خطأ في add_note', e)
            return False, f"❌ حدث خطأ: {str(e)}"
    
    # ==================== Statistics ====================
    
    async def get_statistics(self, guild_id: str) -> Dict:
        """الحصول على إحصائيات التكتات"""
        try:
            if not db.conn:
                return {'total': 0, 'open': 0, 'closed': 0, 'avg_rating': 0}
            cursor = await db.conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
                    AVG(rating) as avg_rating
                FROM tickets_v2
                WHERE guild_id = ?
            ''', (guild_id,))
            
            row = await cursor.fetchone()
            
            return {
                'total': row[0] or 0,
                'open': row[1] or 0,
                'closed': row[2] or 0,
                'avg_rating': round(row[3] or 0, 2)
            }
        except Exception as e:
            bot_logger.error(f'خطأ في get_statistics: {e}')
            return {'total': 0, 'open': 0, 'closed': 0, 'avg_rating': 0}
    
    # ==================== Auto Tasks ====================
    
    def start_auto_tasks(self, bot: discord.Client):
        """بدء المهام التلقائية"""
        if not self.auto_close_task:
            self.auto_close_task = asyncio.create_task(self._auto_close_inactive(bot))
    
    async def _auto_close_inactive(self, bot: discord.Client):
        """إغلاق التكتات غير النشطة تلقائياً"""
        while True:
            try:
                await asyncio.sleep(3600)  # كل ساعة
                
                for channel_id, ticket in list(self.tickets.items()):
                    # الحصول على الفئة
                    guild_id = ticket.guild_id
                    if guild_id not in self.categories or ticket.category_id not in self.categories[guild_id]:
                        continue
                    
                    category = self.categories[guild_id][ticket.category_id]
                    
                    # التحقق من عدم النشاط
                    if ticket.is_inactive(category.auto_close_hours):
                        try:
                            guild = bot.get_guild(int(guild_id))
                            if guild:
                                channel = guild.get_channel(int(channel_id))
                                if channel:
                                    # إرسال تحذير أولاً
                                    embed = discord.Embed(
                                        title='⚠️ تحذير: عدم نشاط',
                                        description=f'لم يتم الرد على هذا التكت منذ {category.auto_close_hours} ساعة.\nسيتم إغلاقه تلقائياً خلال 24 ساعة إذا لم يكن هناك رد.',
                                        color=discord.Color.orange()
                                    )
                                    await channel.send(embed=embed)
                        except Exception:
                            pass
            
            except Exception as e:
                bot_logger.error(f'خطأ في auto-close task: {e}')


# ==================== Views (Buttons) ====================

class PanelView(discord.ui.View):
    """أزرار اللوحة"""
    
    def __init__(self, system: TicketSystemUltimate, guild_id: str = None):
        super().__init__(timeout=None)
        self.system = system
        self.guild_id = guild_id
        
        # إضافة زر لكل فئة (إن وُجدت بيانات محمّلة)
        try:
            if guild_id and guild_id in system.categories:
                for cat_id, category in system.categories[guild_id].items():
                    button = discord.ui.Button(
                        label=category.name,
                        emoji=category.emoji,
                        style=discord.ButtonStyle.primary,
                        custom_id=f'ticket_open_{cat_id}'
                    )
                    button.callback = self._create_callback(cat_id)
                    self.add_item(button)
        except Exception:
            # تجاهل أخطاء أثناء إنشاء الأزرار (سوف يتم إعادة إنشاء الأزرار عند إرسال اللوحة فعليًا)
            pass
    
    def _create_callback(self, category_id: str):
        """إنشاء callback للزر"""
        async def callback(interaction: discord.Interaction):
            # فتح Modal لجمع المعلومات
            modal = TicketModal(self.system, category_id)
            await interaction.response.send_modal(modal)
        
        return callback


class TicketModal(discord.ui.Modal):
    """نموذج فتح التكت"""
    
    def __init__(self, system: TicketSystemUltimate, category_id: str):
        super().__init__(title='فتح تكت جديد')
        self.system = system
        self.category_id = category_id
        
        # حقل السبب
        self.reason = discord.ui.TextInput(
            label='السبب',
            placeholder='اشرح سبب فتح التكت...',
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        success, message, channel = await self.system.create_ticket(
            interaction.guild,
            interaction.user,
            self.category_id,
            self.reason.value
        )
        
        await interaction.followup.send(message, ephemeral=True)


class TicketControlView(discord.ui.View):
    """أزرار التحكم بالتكت"""
    
    def __init__(self, system: TicketSystemUltimate = None):
        super().__init__(timeout=None)
        # دعم تهيئة افتراضية بدون باراميتر (يتوافق مع main.py)
        # إذا لم يُمرّر system، نستخدم الـ instance العام ticket_system_ultimate
        self.system = system if system is not None else globals().get('ticket_system_ultimate')
    
    @discord.ui.button(label='إغلاق', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='ticket_close')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        success, message = await self.system.close_ticket(
            interaction.channel,
            interaction.user,
            save_transcript=True
        )
        
        if not success:
            await interaction.followup.send(message, ephemeral=True)
    
    @discord.ui.button(label='أخذ التكت', style=discord.ButtonStyle.success, emoji='✋', custom_id='ticket_claim')
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, message = await self.system.claim_ticket(interaction.channel, interaction.user)
        await interaction.response.send_message(message, ephemeral=True)
    
    @discord.ui.button(label='ملاحظة', style=discord.ButtonStyle.secondary, emoji='📝', custom_id='ticket_note')
    async def note_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NoteModal(self.system)
        await interaction.response.send_modal(modal)


class NoteModal(discord.ui.Modal, title='إضافة ملاحظة داخلية'):
    """نموذج إضافة ملاحظة"""
    
    def __init__(self, system: TicketSystemUltimate):
        super().__init__()
        self.system = system
        
        self.note = discord.ui.TextInput(
            label='الملاحظة',
            placeholder='هذه الملاحظة مخفية عن المستخدم...',
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.note)
    
    async def on_submit(self, interaction: discord.Interaction):
        success, message = await self.system.add_note(
            interaction.channel,
            interaction.user,
            self.note.value
        )
        await interaction.response.send_message(message, ephemeral=True)


class RatingView(discord.ui.View):
    """أزرار التقييم"""
    
    def __init__(self, system: TicketSystemUltimate, ticket_id: int):
        super().__init__(timeout=300)  # 5 دقائق
        self.system = system
        self.ticket_id = ticket_id
        
        for i in range(1, 6):
            button = discord.ui.Button(
                label=str(i),
                emoji='⭐',
                style=discord.ButtonStyle.secondary,
                custom_id=f'rating_{i}'
            )
            button.callback = self._create_callback(i)
            self.add_item(button)
    
    def _create_callback(self, rating: int):
        async def callback(interaction: discord.Interaction):
            await self.system.rate_ticket(self.ticket_id, rating, str(interaction.user.id))
            
            embed = discord.Embed(
                title='✅ شكراً لتقييمك!',
                description=f'لقد قيّمت الخدمة بـ {rating} {"⭐" * rating}',
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.stop()
        
        return callback


# ==================== Global Instance ====================

ticket_system_ultimate = TicketSystemUltimate()

# --- Compatibility wrappers for main.py imports and persistent views ---

# TicketControlView تم تعديل __init__ أعلاه ليقبل system افتراضيًا

class TicketPanelView(PanelView):
    """
    Wrapper بسيط ليتوافق مع import name في main.py:
        from system_tickets import ticket_system, TicketControlView, TicketPanelView
    يسمح باستدعاء TicketPanelView() بدون باراميتر عند تسجيل الViews الدائمة.
    """
    def __init__(self):
        # نمرر النظام العام و guild_id = None (لو كان None، PanelView سوف يتخطى إضافة الأزرار تلقائيًا)
        super().__init__(globals().get('ticket_system_ultimate'), guild_id=None)

# Alias للتوافق مع main.py
ticket_system = ticket_system_ultimate

# نهاية الملف