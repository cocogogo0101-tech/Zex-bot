# ==================== event_welcome.py ====================
"""
أحداث الترحيب والوداع
✅ تم إضافة Guards للحماية
✅ تم تحسين error handling
✅ تم إضافة logging
"""
import discord
from config_manager import config
import embeds, helpers
from logger import bot_logger

async def handle_member_join(member: discord.Member):
    """معالجة انضمام عضو"""
    try:
        # التحقق من صحة البيانات
        if not member or not member.guild:
            bot_logger.warning('handle_member_join: بيانات غير صحيحة')
            return

        # جلب الإعدادات
        settings = await config.get_welcome_config(str(member.guild.id))

        if not settings or not settings.get('enabled') or not settings.get('channel_id'):
            bot_logger.debug(f'الترحيب معطل أو غير مُعد في {member.guild.name}')
            return

        # التحقق من القناة
        channel = await config.validate_channel(member.guild, settings['channel_id'])
        if not channel:
            bot_logger.warning(f'قناة الترحيب غير موجودة في {member.guild.name}')
            return

        # التحقق من صلاحيات البوت
        bot_perms = channel.permissions_for(member.guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return

        # إرسال الرسالة
        try:
            if settings.get('type') == 'embed':
                embed = embeds.welcome_embed(member, member.guild.member_count)
                await channel.send(embed=embed)
            else:
                message = settings.get('message') or config.get_default_welcome_message()
                message = helpers.replace_variables(
                    message,
                    mention=member.mention,
                    user=member.name,
                    server=member.guild.name,
                    membercount=member.guild.member_count
                )
                await channel.send(message)

            bot_logger.event_processed('member_join', f'{member.name} في {member.guild.name}')

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في {channel.name}')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال الترحيب: {e}')

        # Auto-Role
        autorole_id = await config.get_autorole(str(member.guild.id))
        if autorole_id:
            try:
                role = member.guild.get_role(int(autorole_id))
                if role:
                    # التحقق من التسلسل الهرمي
                    if role < member.guild.me.top_role:
                        await member.add_roles(role, reason='Auto-Role')
                        bot_logger.debug(f'تم إعطاء {member.name} دور {role.name}')
                    else:
                        bot_logger.warning(f'دور Auto-Role أعلى من دور البوت في {member.guild.name}')
            except discord.Forbidden:
                bot_logger.error(f'Forbidden: لا يمكن إعطاء Auto-Role في {member.guild.name}')
            except Exception as e:
                bot_logger.error(f'خطأ في Auto-Role: {e}')

    except Exception as e:
        bot_logger.exception('خطأ غير متوقع في handle_member_join', e)


async def handle_member_remove(member: discord.Member):
    """معالجة مغادرة عضو"""
    try:
        # التحقق من صحة البيانات
        if not member or not member.guild:
            bot_logger.warning('handle_member_remove: بيانات غير صحيحة')
            return

        # جلب الإعدادات
        settings = await config.get_goodbye_config(str(member.guild.id))

        if not settings or not settings.get('enabled') or not settings.get('channel_id'):
            bot_logger.debug(f'الوداع معطل أو غير مُعد في {member.guild.name}')
            return

        # التحقق من القناة
        channel = await config.validate_channel(member.guild, settings['channel_id'])
        if not channel:
            bot_logger.warning(f'قناة الوداع غير موجودة في {member.guild.name}')
            return

        # التحقق من صلاحيات البوت
        bot_perms = channel.permissions_for(member.guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return

        # إرسال رسالة الوداع
        try:
            message = settings.get('message') or config.get_default_goodbye_message()
            message = helpers.replace_variables(
                message,
                user=member.name,
                server=member.guild.name
            )
            await channel.send(message)

            bot_logger.event_processed('member_remove', f'{member.name} من {member.guild.name}')

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في {channel.name}')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال الوداع: {e}')

    except Exception as e:
        bot_logger.exception('خطأ غير متوقع في handle_member_remove', e)
