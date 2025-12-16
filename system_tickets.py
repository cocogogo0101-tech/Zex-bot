"""
نظام التكتات المحسّن مع أزرار وإدارة متقدمة
"""

import discord
import asyncio
from datetime import datetime
from typing import Optional
from database import db
from config_manager import config
import embeds
import helpers

class TicketSystem:
    """نظام التكتات المتقدم"""
    
    async def create_ticket(
        self,
        guild: discord.Guild,
        user: discord.User,
        reason: Optional[str] = None
    ) -> Optional[discord.TextChannel]:
        """
        إنشاء تكت جديد
        
        Returns:
            القناة أو None
        """
        # الحصول على دور الدعم
        support_role_id = await config.get_support_role(str(guild.id))
        
        # إنشاء اسم فريد للقناة
        timestamp = datetime.now().strftime('%m%d%H%M%S')
        channel_name = f'ticket-{user.name}-{timestamp}'
        
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
                manage_channels=True
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
        
        try:
            # إنشاء القناة
            channel = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                reason=f'تكت بواسطة {user}'
            )
            
            # حفظ في قاعدة البيانات
            await db.create_ticket(str(channel.id), str(guild.id), str(user.id), reason)
            
            # رسالة الترحيب
            embed = embeds.ticket_created_embed(user, reason)
            view = TicketControlView()
            await channel.send(content=f'{user.mention}', embed=embed, view=view)
            
            # تسجيل في السجل
            await db.add_log(
                str(guild.id),
                'ticket_open',
                str(user.id),
                reason=reason,
                details=f'Channel: {channel.id}'
            )
            
            return channel
        
        except discord.Forbidden:
            return None
        except discord.HTTPException:
            return None
    
    async def close_ticket(
        self,
        channel: discord.TextChannel,
        closer: discord.User
    ) -> bool:
        """
        إغلاق تكت
        
        Returns:
            bool: نجح؟
        """
        # التحقق من أنها قناة تكت
        ticket = await db.get_ticket(str(channel.id))
        if not ticket:
            return False
        
        # التحقق من الصلاحيات
        if not await self._can_close_ticket(channel, closer, ticket):
            return False
        
        try:
            # حفظ نسخة من المحادثة (اختياري)
            # await self._save_transcript(channel)
            
            # تحديث قاعدة البيانات
            await db.close_ticket(str(channel.id), str(closer.id))
            
            # رسالة الإغلاق
            embed = embeds.ticket_closed_embed(closer)
            await channel.send(embed=embed)
            
            # تسجيل في السجل
            await db.add_log(
                str(channel.guild.id),
                'ticket_close',
                ticket['opener_id'],
                str(closer.id),
                details=f'Channel: {channel.id}'
            )
            
            # الانتظار قليلاً ثم الحذف
            await asyncio.sleep(3)
            await channel.delete(reason=f'تكت مغلق بواسطة {closer}')
            
            return True
        
        except (discord.Forbidden, discord.HTTPException):
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
    
    async def add_user_to_ticket(
        self,
        channel: discord.TextChannel,
        user: discord.Member
    ) -> bool:
        """إضافة مستخدم للتكت"""
        try:
            await channel.set_permissions(
                user,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
            await channel.send(f'✅ تمت إضافة {user.mention} للتكت.')
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False
    
    async def remove_user_from_ticket(
        self,
        channel: discord.TextChannel,
        user: discord.Member
    ) -> bool:
        """إزالة مستخدم من التكت"""
        try:
            await channel.set_permissions(user, overwrite=None)
            await channel.send(f'✅ تمت إزالة {user.mention} من التكت.')
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

class TicketControlView(discord.ui.View):
    """أزرار التحكم بالتكت"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='إغلاق التكت', style=discord.ButtonStyle.red, emoji='🔒', custom_id='close_ticket')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """زر إغلاق التكت"""
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
        """زر فتح تكت"""
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
            await interaction.followup.send('❌ فشل إنشاء التكت.', ephemeral=True)

ticket_system = TicketSystem()