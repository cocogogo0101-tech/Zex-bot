"""
cmd_utility.py - Ultimate Version
==================================
أوامر المنفعة والأدوات العامة

Features:
✅ Ping - سرعة الاستجابة مع تفاصيل
✅ About - معلومات شاملة عن البوت
✅ Stats - إحصائيات متقدمة
✅ Uptime - وقت التشغيل
✅ System Info - معلومات النظام
✅ Help - نظام مساعدة تفاعلي
"""

import discord
from discord import app_commands
from discord.ext import commands
import embeds
from logger import bot_logger
from datetime import datetime
import platform
import psutil
import sys
from typing import Optional

# ==================== Variables ====================

# وقت بدء التشغيل (سيتم تعيينه من main.py)
bot_start_time = datetime.now()

def set_start_time(start_time: datetime):
    """تعيين وقت بدء البوت"""
    global bot_start_time
    bot_start_time = start_time


# ==================== Helper Functions ====================

def get_uptime() -> str:
    """حساب وقت التشغيل"""
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f'{days} يوم')
    if hours > 0:
        parts.append(f'{hours} ساعة')
    if minutes > 0:
        parts.append(f'{minutes} دقيقة')
    if seconds > 0 or not parts:
        parts.append(f'{seconds} ثانية')

    return ' و '.join(parts)


def get_system_info() -> dict:
    """الحصول على معلومات النظام"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu': cpu_percent,
            'memory_used': memory.percent,
            'memory_total': memory.total / (1024 ** 3),  # GB
            'disk_used': disk.percent,
            'disk_total': disk.total / (1024 ** 3),  # GB
            'platform': platform.system(),
            'python_version': platform.python_version()
        }
    except Exception as e:
        bot_logger.error(f'خطأ في get_system_info: {e}')
        return {}


def get_bot_stats(bot: commands.Bot) -> dict:
    """إحصائيات البوت"""
    total_members = sum(g.member_count for g in bot.guilds)
    total_channels = sum(len(g.channels) for g in bot.guilds)
    total_text_channels = sum(len(g.text_channels) for g in bot.guilds)
    total_voice_channels = sum(len(g.voice_channels) for g in bot.guilds)

    # عدد الأوامر
    commands_count = len(bot.tree.get_commands())

    return {
        'guilds': len(bot.guilds),
        'members': total_members,
        'channels': total_channels,
        'text_channels': total_text_channels,
        'voice_channels': total_voice_channels,
        'commands': commands_count,
        'latency': round(bot.latency * 1000, 2)
    }


# ==================== Commands Setup ====================

def setup_utility_commands(bot: commands.Bot):
    """تسجيل أوامر المنفعة"""

    # ==================== Ping ====================

    @bot.tree.command(name='ping', description='عرض سرعة استجابة البوت')
    async def ping(interaction: discord.Interaction):
        """قياس سرعة الاستجابة"""
        try:
            # قياس وقت الاستجابة
            start = datetime.now()
            await interaction.response.defer()
            end = datetime.now()

            api_latency = round(bot.latency * 1000)
            response_time = round((end - start).total_seconds() * 1000)

            # تحديد الحالة
            if api_latency < 100:
                color = discord.Color.green()
                status = '🟢 ممتاز'
            elif api_latency < 200:
                color = discord.Color.yellow()
                status = '🟡 جيد'
            elif api_latency < 300:
                color = discord.Color.orange()
                status = '🟠 مقبول'
            else:
                color = discord.Color.red()
                status = '🔴 بطيء'

            embed = discord.Embed(
                title='🏓 بونج!',
                color=color,
                timestamp=datetime.now()
            )

            embed.add_field(
                name='⚡ WebSocket Latency',
                value=f'`{api_latency}ms`',
                inline=True
            )
            embed.add_field(
                name='📡 Response Time',
                value=f'`{response_time}ms`',
                inline=True
            )
            embed.add_field(
                name='📊 الحالة',
                value=status,
                inline=True
            )

            # معلومات إضافية
            embed.add_field(
                name='⏰ Uptime',
                value=f'`{get_uptime()}`',
                inline=False
            )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.followup.send(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                'ping',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في ping', e)
            await interaction.followup.send(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء قياس السرعة'),
                ephemeral=True
            )

    # ==================== About ====================

    @bot.tree.command(name='about', description='معلومات شاملة عن البوت')
    async def about(interaction: discord.Interaction):
        """معلومات عن البوت"""
        try:
            stats = get_bot_stats(bot)

            embed = discord.Embed(
                title='🤖 معلومات البوت',
                description=(
                    'بوت Discord احترافي متطور لإدارة السيرفرات\n'
                    'مكتوب بـ Python باستخدام discord.py'
                ),
                color=discord.Color.blurple(),
                timestamp=datetime.now()
            )

            # الإحصائيات
            embed.add_field(
                name='📊 الإحصائيات',
                value=(
                    f'**السيرفرات:** `{stats["guilds"]}`\n'
                    f'**الأعضاء:** `{stats["members"]:,}`\n'
                    f'**القنوات:** `{stats["channels"]}`\n'
                    f'**الأوامر:** `{stats["commands"]}`'
                ),
                inline=True
            )

            # الأداء
            embed.add_field(
                name='⚡ الأداء',
                value=(
                    f'**Ping:** `{stats["latency"]}ms`\n'
                    f'**Uptime:** `{get_uptime()}`\n'
                    f'**Python:** `{sys.version.split()[0]}`\n'
                    f'**discord.py:** `{discord.__version__}`'
                ),
                inline=True
            )

            # المميزات
            features = [
                '✅ نظام ترحيب ووداع متقدم',
                '✅ أوامر إدارة شاملة',
                '✅ نظام تكتات احترافي',
                '✅ نظام مستويات وXP',
                '✅ ردود تلقائية ذكية',
                '✅ حماية من السبام والروابط',
                '✅ نظام تحذيرات مع إجراءات تلقائية',
                '✅ نظام سجلات مفصل',
                '✅ اختصارات عربية',
                '✅ Database محلية (SQLite)'
            ]

            embed.add_field(
                name='🎯 المميزات',
                value='\n'.join(features),
                inline=False
            )

            # الروابط
            embed.add_field(
                name='🔗 روابط مفيدة',
                value=(
                    '[الدليل الكامل](https://github.com) • '
                    '[دليل البدء السريع](https://github.com) • '
                    '[الدعم](https://discord.gg)'
                ),
                inline=False
            )

            if bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)

            embed.set_footer(
                text=f'تم الطلب بواسطة {interaction.user.name}',
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                'about',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في about', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء عرض المعلومات'),
                ephemeral=True
            )

    # ==================== Stats ====================

    @bot.tree.command(name='stats', description='إحصائيات مفصلة عن البوت')
    async def stats(interaction: discord.Interaction):
        """إحصائيات متقدمة"""
        try:
            await interaction.response.defer()

            bot_stats = get_bot_stats(bot)
            sys_info = get_system_info()

            embed = discord.Embed(
                title='📊 إحصائيات البوت',
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # إحصائيات Discord
            embed.add_field(
                name='💬 Discord',
                value=(
                    f'**السيرفرات:** `{bot_stats["guilds"]}`\n'
                    f'**الأعضاء:** `{bot_stats["members"]:,}`\n'
                    f'**القنوات النصية:** `{bot_stats["text_channels"]}`\n'
                    f'**القنوات الصوتية:** `{bot_stats["voice_channels"]}`\n'
                    f'**إجمالي القنوات:** `{bot_stats["channels"]}`'
                ),
                inline=True
            )

            # إحصائيات البوت
            embed.add_field(
                name='🤖 البوت',
                value=(
                    f'**الأوامر:** `{bot_stats["commands"]}`\n'
                    f'**Latency:** `{bot_stats["latency"]}ms`\n'
                    f'**Uptime:** `{get_uptime()}`\n'
                    f'**Python:** `{sys.version.split()[0]}`\n'
                    f'**discord.py:** `{discord.__version__}`'
                ),
                inline=True
            )

            # إحصائيات النظام (إن وجدت)
            if sys_info:
                embed.add_field(
                    name='💻 النظام',
                    value=(
                        f'**المنصة:** `{sys_info.get("platform", "N/A")}`\n'
                        f'**CPU:** `{sys_info.get("cpu", 0):.1f}%`\n'
                        f'**RAM:** `{sys_info.get("memory_used", 0):.1f}%` '
                        f'({sys_info.get("memory_total", 0):.2f} GB)\n'
                        f'**Disk:** `{sys_info.get("disk_used", 0):.1f}%` '
                        f'({sys_info.get("disk_total", 0):.2f} GB)'
                    ),
                    inline=False
                )

            # Shards (إذا كان البوت مُجزّأ)
            if bot.shard_count and bot.shard_count > 1:
                embed.add_field(
                    name='🔢 Shards',
                    value=f'**Count:** `{bot.shard_count}`',
                    inline=True
                )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.followup.send(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                'stats',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في stats', e)
            await interaction.followup.send(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء عرض الإحصائيات'),
                ephemeral=True
            )

    # ==================== Uptime ====================

    @bot.tree.command(name='uptime', description='عرض مدة تشغيل البوت')
    async def uptime_cmd(interaction: discord.Interaction):
        """وقت التشغيل"""
        try:
            uptime_str = get_uptime()

            embed = discord.Embed(
                title='⏰ وقت التشغيل',
                description=f'البوت يعمل منذ: **{uptime_str}**',
                color=discord.Color.green(),
                timestamp=datetime.now()
            )

            # وقت البدء
            embed.add_field(
                name='🕐 بدأ التشغيل',
                value=f'<t:{int(bot_start_time.timestamp())}:F>',
                inline=False
            )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            bot_logger.exception('خطأ في uptime', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ'),
                ephemeral=True
            )

    # ==================== Help ====================

    @bot.tree.command(name='help', description='عرض قائمة الأوامر والمساعدة')
    @app_commands.describe(category='الفئة')
    @app_commands.choices(category=[
        app_commands.Choice(name='الإدارة', value='moderation'),
        app_commands.Choice(name='الإعدادات', value='config'),
        app_commands.Choice(name='المعلومات', value='info'),
        app_commands.Choice(name='المرح', value='fun'),
        app_commands.Choice(name='المنفعة', value='utility'),
        app_commands.Choice(name='التكتات', value='tickets'),
        app_commands.Choice(name='الردود التلقائية', value='autoresponse')
    ])
    async def help_cmd(interaction: discord.Interaction, category: Optional[str] = None):
        """نظام المساعدة"""
        try:
            if not category:
                # عرض جميع الفئات
                embed = discord.Embed(
                    title='📚 قائمة المساعدة',
                    description='اختر فئة لعرض الأوامر المتاحة',
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )

                categories = {
                    '🛡️ الإدارة': 'أوامر إدارة السيرفر والأعضاء',
                    '⚙️ الإعدادات': 'إعداد وتخصيص البوت',
                    'ℹ️ المعلومات': 'عرض المعلومات والإحصائيات',
                    '🎮 المرح': 'أوامر ترفيهية وألعاب',
                    '🔧 المنفعة': 'أدوات مساعدة عامة',
                    '🎫 التكتات': 'نظام التكتات',
                    '🤖 الردود التلقائية': 'إدارة الردود التلقائية'
                }

                for cat_name, cat_desc in categories.items():
                    embed.add_field(
                        name=cat_name,
                        value=cat_desc,
                        inline=True
                    )

                embed.add_field(
                    name='📖 الاستخدام',
                    value='استخدم `/help category:<الفئة>` لعرض أوامر فئة محددة',
                    inline=False
                )

                embed.set_footer(text='استخدم الاختصارات العربية أيضاً!')

            else:
                # عرض أوامر فئة محددة
                commands_dict = {
                    'moderation': {
                        'title': '🛡️ أوامر الإدارة',
                        'commands': [
                            ('`/kick`', 'طرد عضو من السيرفر'),
                            ('`/ban`', 'حظر عضو من السيرفر'),
                            ('`/unban`', 'إلغاء حظر عضو'),
                            ('`/timeout`', 'إسكات عضو مؤقتاً'),
                            ('`/warn`', 'تحذير عضو'),
                            ('`/warnings`', 'عرض تحذيرات عضو'),
                            ('`/clearwarnings`', 'مسح تحذيرات عضو'),
                            ('`/purge`', 'مسح عدد من الرسائل'),
                        ]
                    },
                    'config': {
                        'title': '⚙️ أوامر الإعدادات',
                        'commands': [
                            ('`/setup welcome`', 'إعداد نظام الترحيب'),
                            ('`/setup goodbye`', 'إعداد نظام الوداع'),
                            ('`/setup logs`', 'إعداد قناة السجلات'),
                            ('`/setup support`', 'إعداد دور الدعم'),
                            ('`/setup autorole`', 'إعداد الدور التلقائي'),
                            ('`/setup antispam`', 'إعداد مكافحة السبام'),
                            ('`/setup antilink`', 'إعداد مكافحة الروابط'),
                            ('`/setup leveling`', 'إعداد نظام المستويات'),
                            ('`/config`', 'عرض الإعدادات الحالية'),
                        ]
                    },
                    'info': {
                        'title': 'ℹ️ أوامر المعلومات',
                        'commands': [
                            ('`/userinfo`', 'معلومات عن عضو'),
                            ('`/serverinfo`', 'معلومات عن السيرفر'),
                            ('`/rank`', 'عرض مستوى عضو'),
                            ('`/leaderboard`', 'لوحة الصدارة'),
                            ('`/avatar`', 'عرض صورة بروفايل'),
                        ]
                    },
                    'fun': {
                        'title': '🎮 أوامر المرح',
                        'commands': [
                            ('`/roll`', 'رمي النرد'),
                            ('`/coinflip`', 'قلب عملة'),
                            ('`/choose`', 'الاختيار بين خيارات'),
                            ('`/8ball`', 'اسأل الكرة السحرية'),
                        ]
                    },
                    'utility': {
                        'title': '🔧 أوامر المنفعة',
                        'commands': [
                            ('`/ping`', 'سرعة استجابة البوت'),
                            ('`/about`', 'معلومات عن البوت'),
                            ('`/stats`', 'إحصائيات مفصلة'),
                            ('`/uptime`', 'وقت تشغيل البوت'),
                            ('`/help`', 'قائمة المساعدة'),
                        ]
                    },
                    'tickets': {
                        'title': '🎫 أوامر التكتات',
                        'commands': [
                            ('`/ticket open`', 'فتح تكت جديد'),
                            ('`/ticket close`', 'إغلاق التكت الحالي'),
                            ('`/ticket panel`', 'إنشاء لوحة تكتات'),
                        ]
                    },
                    'autoresponse': {
                        'title': '🤖 أوامر الردود التلقائية',
                        'commands': [
                            ('`/autoresponse add`', 'إضافة رد تلقائي'),
                            ('`/autoresponse list`', 'عرض جميع الردود'),
                            ('`/autoresponse remove`', 'حذف رد تلقائي'),
                        ]
                    }
                }

                if category not in commands_dict:
                    await interaction.response.send_message(
                        embed=embeds.error_embed('خطأ', 'فئة غير موجودة'),
                        ephemeral=True
                    )
                    return

                cat_info = commands_dict[category]

                embed = discord.Embed(
                    title=cat_info['title'],
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )

                for cmd, desc in cat_info['commands']:
                    embed.add_field(
                        name=cmd,
                        value=desc,
                        inline=False
                    )

                embed.set_footer(text='💡 نصيحة: يمكنك استخدام الاختصارات العربية!')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                'help',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في help', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ في عرض المساعدة'),
                ephemeral=True
            )

    bot_logger.success('تم تسجيل أوامر المنفعة بنجاح')