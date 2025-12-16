"""
cmd_info.py - Ultimate Version
===============================
أوامر المعلومات والإحصائيات

Features:
✅ Userinfo - معلومات شاملة عن عضو
✅ Serverinfo - معلومات مفصلة عن السيرفر
✅ Rank - عرض مستوى العضو مع تقدم
✅ Leaderboard - لوحة صدارة جميلة
✅ Avatar - صورة البروفايل بجودة عالية
✅ Roleinfo - معلومات عن دور
✅ Channelinfo - معلومات عن قناة
"""

import discord
from discord import app_commands
from discord.ext import commands
import embeds
from system_leveling import leveling_system
from logger import bot_logger
from datetime import datetime
from typing import Optional
import helpers


def setup_info_commands(bot: commands.Bot):
    """تسجيل أوامر المعلومات"""

    # ==================== Userinfo ====================

    @bot.tree.command(name='userinfo', description='عرض معلومات عن عضو')
    @app_commands.describe(user='العضو (افتراضي: أنت)')
    async def userinfo(interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """معلومات شاملة عن عضو"""
        try:
            user = user or interaction.user

            # إنشاء Embed
            embed = discord.Embed(
                title=f'معلومات {helpers.format_user(user)}',
                color=helpers.get_member_color(user) if isinstance(user, discord.Member) else discord.Color.blue(),
                timestamp=datetime.now()
            )

            # الصورة
            embed.set_thumbnail(url=helpers.get_user_avatar(user))

            # المعلومات الأساسية
            embed.add_field(
                name='👤 الاسم',
                value=user.name,
                inline=True
            )

            embed.add_field(
                name='🆔 الـ ID',
                value=f'`{user.id}`',
                inline=True
            )

            embed.add_field(
                name='🤖 بوت؟',
                value='✅ نعم' if user.bot else '❌ لا',
                inline=True
            )

            # التواريخ
            embed.add_field(
                name='📅 تاريخ الإنشاء',
                value=f'<t:{int(user.created_at.timestamp())}:F>\n<t:{int(user.created_at.timestamp())}:R>',
                inline=False
            )

            # معلومات العضوية (إذا كان في السيرفر)
            if isinstance(user, discord.Member):
                embed.add_field(
                    name='📥 تاريخ الانضمام',
                    value=f'<t:{int(user.joined_at.timestamp())}:F>\n<t:{int(user.joined_at.timestamp())}:R>',
                    inline=False
                )

                # أعلى دور
                if user.top_role != interaction.guild.default_role:
                    embed.add_field(
                        name='👑 أعلى دور',
                        value=user.top_role.mention,
                        inline=True
                    )

                # الحالة
                status_emoji = {
                    discord.Status.online: '🟢',
                    discord.Status.idle: '🟡',
                    discord.Status.dnd: '🔴',
                    discord.Status.offline: '⚫'
                }

                embed.add_field(
                    name='📡 الحالة',
                    value=f'{status_emoji.get(user.status, "⚫")} {str(user.status).title()}',
                    inline=True
                )

                # Boosting
                if user.premium_since:
                    embed.add_field(
                        name='💎 Boosting',
                        value=f'منذ <t:{int(user.premium_since.timestamp())}:R>',
                        inline=True
                    )

                # الأدوار
                if len(user.roles) > 1:
                    roles = [role.mention for role in user.roles[1:]][:20]  # أول 20 دور
                    roles_text = ' '.join(roles)

                    if len(user.roles) > 21:
                        roles_text += f' **+{len(user.roles) - 21}**'

                    embed.add_field(
                        name=f'🎭 الأدوار [{len(user.roles) - 1}]',
                        value=roles_text,
                        inline=False
                    )

                # الصلاحيات الرئيسية
                key_perms = []
                if user.guild_permissions.administrator:
                    key_perms.append('👑 Administrator')
                if user.guild_permissions.manage_guild:
                    key_perms.append('⚙️ إدارة السيرفر')
                if user.guild_permissions.manage_roles:
                    key_perms.append('🎭 إدارة الأدوار')
                if user.guild_permissions.manage_channels:
                    key_perms.append('📁 إدارة القنوات')
                if user.guild_permissions.kick_members:
                    key_perms.append('👢 طرد الأعضاء')
                if user.guild_permissions.ban_members:
                    key_perms.append('🔨 حظر الأعضاء')

                if key_perms:
                    embed.add_field(
                        name='🔑 الصلاحيات الرئيسية',
                        value='\n'.join(key_perms),
                        inline=False
                    )

            embed.set_footer(
                text=f'مطلوب بواسطة {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'userinfo ({user.name})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في userinfo', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض معلومات العضو'),
                ephemeral=True
            )

    # ==================== Serverinfo ====================

    @bot.tree.command(name='serverinfo', description='عرض معلومات عن السيرفر')
    async def serverinfo(interaction: discord.Interaction):
        """معلومات مفصلة عن السيرفر"""
        try:
            guild = interaction.guild

            embed = discord.Embed(
                title=f'معلومات {guild.name}',
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # أيقونة السيرفر
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            # Banner (إن وجد)
            if guild.banner:
                embed.set_image(url=guild.banner.url)

            # المعلومات الأساسية
            embed.add_field(
                name='🆔 الـ ID',
                value=f'`{guild.id}`',
                inline=True
            )

            embed.add_field(
                name='👑 المالك',
                value=guild.owner.mention if guild.owner else 'غير معروف',
                inline=True
            )

            embed.add_field(
                name='📅 تاريخ الإنشاء',
                value=f'<t:{int(guild.created_at.timestamp())}:R>',
                inline=True
            )

            # الأعضاء
            total = guild.member_count
            humans = sum(1 for m in guild.members if not m.bot)
            bots = sum(1 for m in guild.members if m.bot)
            online = sum(1 for m in guild.members if m.status != discord.Status.offline)

            embed.add_field(
                name='👥 الأعضاء',
                value=(
                    f'**الإجمالي:** {total:,}\n'
                    f'👤 **بشر:** {humans:,}\n'
                    f'🤖 **بوتات:** {bots}\n'
                    f'🟢 **متصل:** {online:,}'
                ),
                inline=True
            )

            # القنوات
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)

            embed.add_field(
                name='📁 القنوات',
                value=(
                    f'💬 **نصية:** {text_channels}\n'
                    f'🔊 **صوتية:** {voice_channels}\n'
                    f'📂 **فئات:** {categories}'
                ),
                inline=True
            )

            # الأدوار
            embed.add_field(
                name='🎭 الأدوار',
                value=f'**{len(guild.roles)}** دور',
                inline=True
            )

            # Boost
            boost_level = guild.premium_tier
            boost_count = guild.premium_subscription_count or 0

            embed.add_field(
                name='💎 Nitro Boost',
                value=(
                    f'**المستوى:** {boost_level}\n'
                    f'**العدد:** {boost_count}'
                ),
                inline=True
            )

            # الإيموجي
            embed.add_field(
                name='😀 الإيموجي',
                value=f'**{len(guild.emojis)}** إيموجي',
                inline=True
            )

            # الملصقات
            embed.add_field(
                name='🏷️ الملصقات',
                value=f'**{len(guild.stickers)}** ملصق',
                inline=True
            )

            # مستوى التحقق
            verification_levels = {
                discord.VerificationLevel.none: 'بدون',
                discord.VerificationLevel.low: 'منخفض',
                discord.VerificationLevel.medium: 'متوسط',
                discord.VerificationLevel.high: 'عالي',
                discord.VerificationLevel.highest: 'أعلى',
            }

            embed.add_field(
                name='🔒 مستوى التحقق',
                value=verification_levels.get(guild.verification_level, 'غير معروف'),
                inline=True
            )

            # المميزات
            features = []
            feature_names = {
                'COMMUNITY': '🌐 مجتمع',
                'VERIFIED': '✅ موثق',
                'PARTNERED': '🤝 شريك',
                'VANITY_URL': '🔗 رابط مخصص',
                'ANIMATED_ICON': '🎬 أيقونة متحركة',
                'BANNER': '🖼️ بانر',
                'WELCOME_SCREEN_ENABLED': '👋 شاشة ترحيب',
                'DISCOVERABLE': '🔍 قابل للاكتشاف',
            }

            for feature in guild.features:
                if feature in feature_names:
                    features.append(feature_names[feature])

            if features:
                embed.add_field(
                    name='✨ المميزات',
                    value='\n'.join(features[:10]),
                    inline=False
                )

            embed.set_footer(
                text=f'مطلوب بواسطة {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                'serverinfo',
                guild.name
            )

        except Exception as e:
            bot_logger.exception('خطأ في serverinfo', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض معلومات السيرفر'),
                ephemeral=True
            )

    # ==================== Rank ====================

    @bot.tree.command(name='rank', description='عرض مستوى عضو')
    @app_commands.describe(user='العضو (افتراضي: أنت)')
    async def rank(interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """عرض المستوى والتقدم"""
        try:
            user = user or interaction.user

            # جلب بيانات المستوى
            data = await leveling_system.get_user_level(str(interaction.guild.id), str(user.id))

            if not data:
                await interaction.response.send_message(
                    embed=embeds.warning_embed(
                        'لا توجد بيانات',
                        f'{user.mention} لم يرسل أي رسائل بعد!'
                    ),
                    ephemeral=True
                )
                return

            # الحصول على الترتيب
            rank_pos = await leveling_system.get_user_rank(str(interaction.guild.id), str(user.id))

            # إنشاء Embed
            embed = embeds.rank_embed(user, data, rank_pos)

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'rank ({user.name})',
                interaction.guild.name
            )

        except Exception as e:
            bot_logger.exception('خطأ في rank', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض المستوى'),
                ephemeral=True
            )

    # ==================== Leaderboard ====================

    @bot.tree.command(name='leaderboard', description='عرض لوحة الصدارة')
    @app_commands.describe(page='رقم الصفحة (افتراضي: 1)')
    async def leaderboard(interaction: discord.Interaction, page: Optional[int] = 1):
        """لوحة الصدارة"""
        try:
            # التحقق من رقم الصفحة
            if page < 1:
                page = 1

            # جلب البيانات
            offset = (page - 1) * 10
            lb = await leveling_system.get_leaderboard(str(interaction.guild.id), limit=10, offset=offset)

            if not lb:
                await interaction.response.send_message(
                    embed=embeds.warning_embed(
                        'لا توجد بيانات',
                        'لا توجد بيانات في لوحة الصدارة بعد!'
                    ),
                    ephemeral=True
                )
                return

            # إنشاء Embed
            embed = embeds.leaderboard_embed(interaction.guild, lb, page)

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'leaderboard (page {page})',
                interaction.guild.name
            )

        except Exception as e:
            bot_logger.exception('خطأ في leaderboard', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض لوحة الصدارة'),
                ephemeral=True
            )

    # ==================== Avatar ====================

    @bot.tree.command(name='avatar', description='عرض صورة بروفايل عضو')
    @app_commands.describe(user='العضو (افتراضي: أنت)')
    async def avatar(interaction: discord.Interaction, user: Optional[discord.User] = None):
        """عرض صورة البروفايل بجودة عالية"""
        try:
            user = user or interaction.user

            embed = discord.Embed(
                title=f'🖼️ صورة {helpers.format_user(user)}',
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # الصورة بجودة عالية
            avatar_url = user.display_avatar.with_size(1024).url
            embed.set_image(url=avatar_url)

            # روابط التحميل
            formats = []
            if user.display_avatar.is_animated():
                formats.append(f'[GIF]({user.display_avatar.with_format("gif").url})')
            formats.extend([
                f'[PNG]({user.display_avatar.with_format("png").url})',
                f'[JPG]({user.display_avatar.with_format("jpg").url})',
                f'[WEBP]({user.display_avatar.with_format("webp").url})'
            ])

            embed.add_field(
                name='📥 تحميل',
                value=' • '.join(formats),
                inline=False
            )

            embed.set_footer(
                text=f'مطلوب بواسطة {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'avatar ({user.name})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في avatar', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض الصورة'),
                ephemeral=True
            )

    # ==================== Roleinfo ====================

    @bot.tree.command(name='roleinfo', description='عرض معلومات عن دور')
    @app_commands.describe(role='الدور')
    async def roleinfo(interaction: discord.Interaction, role: discord.Role):
        """معلومات عن دور"""
        try:
            embed = discord.Embed(
                title=f'معلومات الدور: {role.name}',
                color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
                timestamp=datetime.now()
            )

            # المعلومات الأساسية
            embed.add_field(
                name='🆔 الـ ID',
                value=f'`{role.id}`',
                inline=True
            )

            embed.add_field(
                name='🎨 اللون',
                value=f'`{role.color}`',
                inline=True
            )

            embed.add_field(
                name='👥 الأعضاء',
                value=f'**{len(role.members)}** عضو',
                inline=True
            )

            # الخصائص
            properties = []
            if role.hoist:
                properties.append('📌 يظهر منفصلاً')
            if role.mentionable:
                properties.append('💬 قابل للمنشن')
            if role.managed:
                properties.append('🤖 يُدار تلقائياً')
            if role.is_bot_managed():
                properties.append('🔧 دور بوت')
            if role.is_premium_subscriber():
                properties.append('💎 دور Booster')
            if role.is_integration():
                properties.append('🔗 دور Integration')

            if properties:
                embed.add_field(
                    name='✨ الخصائص',
                    value='\n'.join(properties),
                    inline=False
                )

            # التواريخ
            embed.add_field(
                name='📅 تاريخ الإنشاء',
                value=f'<t:{int(role.created_at.timestamp())}:F>\n<t:{int(role.created_at.timestamp())}:R>',
                inline=False
            )

            # الموضع
            embed.add_field(
                name='📊 الترتيب',
                value=f'**{role.position}** من {len(interaction.guild.roles)}',
                inline=True
            )

            embed.set_footer(
                text=f'مطلوب بواسطة {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'roleinfo ({role.name})',
                interaction.guild.name
            )

        except Exception as e:
            bot_logger.exception('خطأ في roleinfo', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل عرض معلومات الدور'),
                ephemeral=True
            )

    bot_logger.success('تم تسجيل أوامر المعلومات بنجاح')