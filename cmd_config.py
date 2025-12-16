"""أوامر الإعدادات"""
import discord
from discord import app_commands
from discord.ext import commands
from config_manager import config
import permissions, embeds

def setup_config_commands(bot: commands.Bot):
    """تسجيل أوامر الإعدادات"""
    
    setup_group = app_commands.Group(name='setup', description='إعداد البوت')
    
    @setup_group.command(name='welcome', description='إعداد نظام الترحيب')
    @app_commands.describe(
        enabled='تفعيل/تعطيل',
        channel='قناة الترحيب',
        message='رسالة الترحيب (متغيرات: {mention}, {user}, {server}, {membercount})',
        type='نوع الرسالة'
    )
    @app_commands.choices(type=[
        app_commands.Choice(name='نص عادي', value='text'),
        app_commands.Choice(name='Embed', value='embed')
    ])
    @permissions.is_admin()
    async def setup_welcome(
        interaction: discord.Interaction,
        enabled: bool = None,
        channel: discord.TextChannel = None,
        message: str = None,
        type: str = None
    ):
        await config.setup_welcome(
            str(interaction.guild.id),
            enabled=enabled,
            channel_id=str(channel.id) if channel else None,
            message=message,
            type=type
        )
        await interaction.response.send_message(embeds.success_embed('تم', 'تم تحديث إعدادات الترحيب'))
    
    @setup_group.command(name='goodbye', description='إعداد نظام الوداع')
    @app_commands.describe(
        enabled='تفعيل/تعطيل',
        channel='قناة الوداع',
        message='رسالة الوداع'
    )
    @permissions.is_admin()
    async def setup_goodbye(
        interaction: discord.Interaction,
        enabled: bool = None,
        channel: discord.TextChannel = None,
        message: str = None
    ):
        await config.setup_goodbye(
            str(interaction.guild.id),
            enabled=enabled,
            channel_id=str(channel.id) if channel else None,
            message=message
        )
        await interaction.response.send_message(embeds.success_embed('تم', 'تم تحديث إعدادات الوداع'))
    
    @setup_group.command(name='logs', description='إعداد قناة السجلات')
    @app_commands.describe(channel='قناة السجلات')
    @permissions.is_admin()
    async def setup_logs(interaction: discord.Interaction, channel: discord.TextChannel):
        await config.setup_logs(str(interaction.guild.id), str(channel.id))
        await interaction.response.send_message(embeds.success_embed('تم', f'تم تعيين قناة السجلات: {channel.mention}'))
    
    @setup_group.command(name='support', description='إعداد دور الدعم')
    @app_commands.describe(role='دور الدعم')
    @permissions.is_admin()
    async def setup_support(interaction: discord.Interaction, role: discord.Role):
        await config.setup_support_role(str(interaction.guild.id), str(role.id))
        await interaction.response.send_message(embeds.success_embed('تم', f'تم تعيين دور الدعم: {role.mention}'))
    
    @setup_group.command(name='autorole', description='إعداد الدور التلقائي')
    @app_commands.describe(role='الدور التلقائي للأعضاء الجدد')
    @permissions.is_admin()
    async def setup_autorole(interaction: discord.Interaction, role: discord.Role):
        await config.setup_autorole(str(interaction.guild.id), str(role.id))
        await interaction.response.send_message(embeds.success_embed('تم', f'الدور التلقائي: {role.mention}'))
    
    @setup_group.command(name='antispam', description='إعداد مكافحة السبام')
    @app_commands.describe(enabled='تفعيل/تعطيل', threshold='عدد الرسائل المسموح (5-10)')
    @permissions.is_admin()
    async def setup_antispam(interaction: discord.Interaction, enabled: bool, threshold: int = 5):
        await config.setup_antispam(str(interaction.guild.id), enabled, threshold)
        await interaction.response.send_message(embeds.success_embed('تم', f'مكافحة السبام: {"مفعل" if enabled else "معطل"}'))
    
    @setup_group.command(name='antilink', description='إعداد مكافحة الروابط')
    @app_commands.describe(enabled='تفعيل/تعطيل')
    @permissions.is_admin()
    async def setup_antilink(interaction: discord.Interaction, enabled: bool):
        await config.setup_antilink(str(interaction.guild.id), enabled)
        await interaction.response.send_message(embeds.success_embed('تم', f'مكافحة الروابط: {"مفعل" if enabled else "معطل"}'))
    
    @setup_group.command(name='leveling', description='إعداد نظام المستويات')
    @app_commands.describe(enabled='تفعيل/تعطيل')
    @permissions.is_admin()
    async def setup_leveling(interaction: discord.Interaction, enabled: bool):
        await config.setup_leveling(str(interaction.guild.id), enabled)
        await interaction.response.send_message(embeds.success_embed('تم', f'نظام المستويات: {"مفعل" if enabled else "معطل"}'))
    
    bot.tree.add_command(setup_group)
    
    @bot.tree.command(name='config', description='عرض الإعدادات الحالية')
    async def view_config(interaction: discord.Interaction):
        settings = await config.get_settings(str(interaction.guild.id))
        embed = embeds.config_embed(interaction.guild, settings)
        await interaction.response.send_message(embed=embed)