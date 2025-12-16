"""
أوامر الإدارة والمودريشن
✅ تم إصلاح جميع استخدامات Embeds
✅ تم توحيد Interaction responses
✅ تم تحسين error handling
✅ تم إضافة logging
"""
import discord
from discord import app_commands
from discord.ext import commands
import permissions, helpers, embeds
from system_warnings import warning_system
from database import db
from event_logs import send_log
from logger import bot_logger

def setup_moderation_commands(bot: commands.Bot):
    """تسجيل أوامر الإدارة"""

    @bot.tree.command(name='kick', description='طرد عضو من السيرفر')
    @app_commands.describe(user='العضو المراد طرده', reason='السبب')
    @permissions.is_moderator()
    async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """طرد عضو"""
        # التحقق من الصلاحيات
        async with permissions.PermissionChecker(interaction) as checker:
            if not await checker.check_target(user, 'kick'):
                return
            if not await checker.check_bot_perms(kick_members=True):
                return

        try:
            # طرد العضو
            await user.kick(reason=reason)

            # إنشاء embed
            embed = embeds.kick_embed(user, interaction.user, reason)

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(embed=embed)

            # إرسال للسجل
            await send_log(interaction.guild, embed)

            # حفظ في قاعدة البيانات
            await db.add_log(
                str(interaction.guild.id),
                'kick',
                str(user.id),
                str(interaction.user.id),
                reason=reason
            )

            # Logging
            bot_logger.moderation_action(
                'KICK',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                reason or 'لا يوجد سبب'
            )

        except discord.Forbidden:
            bot_logger.error(f'فشل طرد {user.name}: Forbidden')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'ليس لدي صلاحية لطرد هذا العضو'),
                ephemeral=True
            )
        except discord.HTTPException as e:
            bot_logger.error(f'فشل طرد {user.name}: {e}')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل طرد العضو'),
                ephemeral=True
            )
        except Exception as e:
            bot_logger.exception('خطأ غير متوقع في kick', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ غير متوقع'),
                ephemeral=True
            )

    @bot.tree.command(name='ban', description='حظر عضو من السيرفر')
    @app_commands.describe(
        user='العضو المراد حظره',
        reason='السبب',
        delete_days='حذف رسائله آخر X أيام (0-7)'
    )
    @permissions.is_moderator()
    async def ban(interaction: discord.Interaction, user: discord.User, reason: str = None, delete_days: int = 0):
        """حظر عضو"""
        # التحقق من الصلاحيات
        if isinstance(user, discord.Member):
            async with permissions.PermissionChecker(interaction) as checker:
                if not await checker.check_target(user, 'ban'):
                    return

        if not await permissions.check_bot_permissions(interaction.guild, ban_members=True):
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'البوت يحتاج صلاحية الحظر'),
                ephemeral=True
            )
            return

        try:
            # حظر المستخدم
            await interaction.guild.ban(
                user,
                reason=reason,
                delete_message_days=min(max(delete_days, 0), 7)
            )

            # إنشاء embed
            embed = embeds.ban_embed(user, interaction.user, reason)

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(embed=embed)

            # إرسال للسجل
            await send_log(interaction.guild, embed)

            # حفظ في قاعدة البيانات
            await db.add_log(
                str(interaction.guild.id),
                'ban',
                str(user.id),
                str(interaction.user.id),
                reason=reason
            )

            # Logging
            bot_logger.moderation_action(
                'BAN',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                reason or 'لا يوجد سبب'
            )

        except discord.Forbidden:
            bot_logger.error(f'فشل حظر {user.name}: Forbidden')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'ليس لدي صلاحية لحظر هذا العضو'),
                ephemeral=True
            )
        except discord.HTTPException as e:
            bot_logger.error(f'فشل حظر {user.name}: {e}')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل حظر العضو'),
                ephemeral=True
            )
        except Exception as e:
            bot_logger.exception('خطأ غير متوقع في ban', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ غير متوقع'),
                ephemeral=True
            )

    @bot.tree.command(name='timeout', description='إسكات عضو مؤقتاً')
    @app_commands.describe(
        user='العضو',
        duration='المدة (مثال: 10m, 1h, 1d)',
        reason='السبب'
    )
    @permissions.is_moderator()
    async def timeout(interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = None):
        """إسكات عضو مؤقتاً"""
        # التحقق من الصلاحيات
        async with permissions.PermissionChecker(interaction) as checker:
            if not await checker.check_target(user, 'timeout'):
                return
            if not await checker.check_bot_perms(moderate_members=True):
                return

        # تحليل المدة
        time_delta = helpers.parse_time(duration)
        if not time_delta:
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'صيغة الوقت خاطئة. استخدم: 10m, 1h, 1d'),
                ephemeral=True
            )
            return

        # التحقق من الحد الأقصى (28 يوم)
        if time_delta.total_seconds() > 28 * 24 * 60 * 60:
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'الحد الأقصى للإسكات هو 28 يوماً'),
                ephemeral=True
            )
            return

        try:
            # إسكات العضو
            until = discord.utils.utcnow() + time_delta
            await user.timeout(until, reason=reason)

            # إنشاء embed
            embed = embeds.timeout_embed(user, interaction.user, duration, reason)

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(embed=embed)

            # إرسال للسجل
            await send_log(interaction.guild, embed)

            # حفظ في قاعدة البيانات
            await db.add_log(
                str(interaction.guild.id),
                'timeout',
                str(user.id),
                str(interaction.user.id),
                reason=reason,
                details=duration
            )

            # Logging
            bot_logger.moderation_action(
                'TIMEOUT',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                f'{duration} - {reason or "لا يوجد سبب"}'
            )

        except discord.Forbidden:
            bot_logger.error(f'فشل إسكات {user.name}: Forbidden')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'ليس لدي صلاحية لإسكات هذا العضو'),
                ephemeral=True
            )
        except discord.HTTPException as e:
            bot_logger.error(f'فشل إسكات {user.name}: {e}')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل إسكات العضو'),
                ephemeral=True
            )
        except Exception as e:
            bot_logger.exception('خطأ غير متوقع في timeout', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ غير متوقع'),
                ephemeral=True
            )

    @bot.tree.command(name='warn', description='تحذير عضو')
    @app_commands.describe(user='العضو', reason='سبب التحذير')
    @permissions.is_moderator()
    async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
        """تحذير عضو"""
        # التحقق من الصلاحيات
        async with permissions.PermissionChecker(interaction) as checker:
            if not await checker.check_target(user, 'warn'):
                return

        try:
            # إضافة التحذير
            result = await warning_system.warn_user(
                interaction.guild,
                user,
                interaction.user,
                reason
            )

            # إنشاء embed
            embed = embeds.warn_embed(
                user,
                interaction.user,
                reason,
                result['warn_count']
            )

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(embed=embed)

            # إرسال للسجل
            await send_log(interaction.guild, embed)

            # إشعار بالإجراء التلقائي
            if result['auto_action']:
                await interaction.followup.send(
                    embed=embeds.warning_embed(
                        'إجراء تلقائي',
                        f'تم تنفيذ: **{result["auto_action"]}**'
                    ),
                    ephemeral=True
                )

            # Logging
            bot_logger.moderation_action(
                'WARN',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                f'{reason} (#{result["warn_count"]})'
            )

        except Exception as e:
            bot_logger.exception('خطأ في warn', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل تحذير العضو'),
                ephemeral=True
            )

    @bot.tree.command(name='warnings', description='عرض تحذيرات عضو')
    @app_commands.describe(user='العضو')
    async def warnings(interaction: discord.Interaction, user: discord.Member):
        """عرض تحذيرات عضو"""
        try:
            # جلب التحذيرات
            warns = await warning_system.get_warnings(
                str(interaction.guild.id),
                str(user.id)
            )

            # إنشاء embed
            embed = embeds.warnings_list_embed(user, warns)

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            bot_logger.exception('خطأ في warnings', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل جلب التحذيرات'),
                ephemeral=True
            )

    @bot.tree.command(name='clearwarnings', description='مسح تحذيرات عضو')
    @app_commands.describe(user='العضو')
    @permissions.is_moderator()
    async def clearwarnings(interaction: discord.Interaction, user: discord.Member):
        """مسح تحذيرات عضو"""
        try:
            # مسح التحذيرات
            await warning_system.clear_warnings(
                str(interaction.guild.id),
                str(user.id)
            )

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(
                embed=embeds.success_embed(
                    'تم',
                    f'تم مسح جميع تحذيرات {user.mention}'
                )
            )

            # Logging
            bot_logger.moderation_action(
                'CLEAR_WARNINGS',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                'مسح جميع التحذيرات'
            )

        except Exception as e:
            bot_logger.exception('خطأ في clearwarnings', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'فشل مسح التحذيرات'),
                ephemeral=True
            )

    @bot.tree.command(name='purge', description='مسح عدد من الرسائل')
    @app_commands.describe(count='عدد الرسائل (1-100)')
    @permissions.has_permissions(manage_messages=True)
    async def purge(interaction: discord.Interaction, count: int):
        """مسح رسائل"""
        # التحقق من العدد
        if count < 1 or count > 100:
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'العدد يجب أن يكون بين 1-100'),
                ephemeral=True
            )
            return

        try:
            # ✅ توحيد الـ response: defer أولاً
            await interaction.response.defer(ephemeral=True)

            # مسح الرسائل
            deleted = await interaction.channel.purge(limit=count)

            # ✅ استخدام followup بعد defer
            await interaction.followup.send(
                embed=embeds.success_embed(
                    'تم',
                    f'تم مسح {len(deleted)} رسالة'
                ),
                ephemeral=True
            )

            # Logging
            bot_logger.moderation_action(
                'PURGE',
                f'{interaction.channel.name}',
                f'{interaction.user.name} ({interaction.user.id})',
                f'مسح {len(deleted)} رسالة'
            )

        except discord.Forbidden:
            bot_logger.error(f'فشل purge: Forbidden')
            await interaction.followup.send(
                embed=embeds.error_embed('خطأ', 'ليس لدي صلاحية إدارة الرسائل'),
                ephemeral=True
            )
        except discord.HTTPException as e:
            bot_logger.error(f'فشل purge: {e}')
            await interaction.followup.send(
                embed=embeds.error_embed('خطأ', 'فشل مسح الرسائل'),
                ephemeral=True
            )
        except Exception as e:
            bot_logger.exception('خطأ غير متوقع في purge', e)
            await interaction.followup.send(
                embed=embeds.error_embed('خطأ', 'حدث خطأ غير متوقع'),
                ephemeral=True
            )

    @bot.tree.command(name='unban', description='إلغاء حظر عضو')
    @app_commands.describe(user_id='معرف المستخدم', reason='السبب')
    @permissions.is_moderator()
    async def unban(interaction: discord.Interaction, user_id: str, reason: str = None):
        """إلغاء حظر عضو"""
        # التحقق من صلاحيات البوت
        if not await permissions.check_bot_permissions(interaction.guild, ban_members=True):
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'البوت يحتاج صلاحية الحظر'),
                ephemeral=True
            )
            return

        try:
            # تحويل ID إلى int
            user_id_int = int(user_id)

            # إنشاء User object
            user = await bot.fetch_user(user_id_int)

            # إلغاء الحظر
            await interaction.guild.unban(user, reason=reason)

            # ✅ إصلاح: إضافة embed=
            await interaction.response.send_message(
                embed=embeds.success_embed(
                    'تم',
                    f'تم إلغاء حظر **{user.name}**\nالسبب: {reason or "لا يوجد سبب"}'
                )
            )

            # Logging
            bot_logger.moderation_action(
                'UNBAN',
                f'{user.name} ({user.id})',
                f'{interaction.user.name} ({interaction.user.id})',
                reason or 'لا يوجد سبب'
            )

        except ValueError:
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'معرف المستخدم غير صحيح'),
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'لم يتم العثور على المستخدم أو ليس محظوراً'),
                ephemeral=True
            )
        except discord.Forbidden:
            bot_logger.error(f'فشل unban: Forbidden')
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'ليس لدي صلاحية إلغاء الحظر'),
                ephemeral=True
            )
        except Exception as e:
            bot_logger.exception('خطأ في unban', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ غير متوقع'),
                ephemeral=True
            )