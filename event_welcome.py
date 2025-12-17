# event_welcome.py
"""
أحداث الترحيب والوداع - مع دعم آمن لعرض "من دعا العضو"
✅ يستخدم invite_tracker الموجود في المشروع (إذا نجح)
✅ يمرّر المتغير inviter إلى replace_variables مع fallback
✅ لوقات debug واضحة لتسهيل الاختبار
"""
import discord
from config_manager import config
from system_invites import invite_tracker, invite_rewards
import embeds, helpers
from logger import bot_logger

async def handle_member_join(member: discord.Member):
    """معالجة انضمام عضو"""
    try:
        # التحقق من صحة البيانات
        if not member or not member.guild:
            bot_logger.warning('handle_member_join: بيانات غير صحيحة')
            return

        guild_id = str(member.guild.id)

        # ==================== تتبع الدعوات ====================
        inviter = None
        invite_count = None
        try:
            inviter = await invite_tracker.find_inviter(member)
            if inviter:
                # احصل على عدد دعوات الداعي إن أمكن
                try:
                    invite_count = await invite_tracker.get_user_invites(guild_id, str(inviter.id))
                except Exception as e:
                    bot_logger.debug(f'خطأ في الحصول على invite_count لـ {inviter}: {e}')
                    invite_count = None

                bot_logger.info(
                    f'Invite tracker: {member.name} انضم بواسطه {inviter} (count={invite_count})'
                )
            else:
                bot_logger.debug(f'Invite tracker: لم يُحدد داعٍ واضح لـ {member.name}')
        except Exception as e:
            bot_logger.error(f'خطأ في تتبع الدعوة (find_inviter): {e}')
            inviter = None
            invite_count = None
            # لا نوقف العملية؛ نكمل ترحيب بدون inviter

        # ==================== رسالة الترحيب ====================
        # جلب الإعدادات
        settings = await config.get_welcome_config(guild_id)

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
        if not bot_perms.send_messages:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return

        # إرسال الرسالة (Embed أو نصي)
        try:
            if settings.get('type') == 'embed':
                # Embed مع معلومات الدعوة (لو وُجدت)
                embed = embeds.welcome_embed(member, member.guild.member_count)

                if inviter:
                    # نعرض الداعي كميد في الـ embed (إن أمكن)
                    try:
                        invite_count = invite_count or await invite_tracker.get_user_invites(guild_id, str(inviter.id))
                    except Exception:
                        pass
                    embed.add_field(
                        name='📨 تمت الدعوة بواسطة',
                        value=f'{inviter.mention} • **{invite_count if invite_count is not None else "—"}** دعوات',
                        inline=False
                    )

                await channel.send(embed=embed)
            else:
                # رسالة نصية: نحاول تمرير inviter إلى replace_variables بأمان
                # بناء اسم داعي آمن (mention لو متوفر)
                inviter_var = inviter.mention if inviter else None

                message_template = settings.get('message') or config.get_default_welcome_message()

                # حاول أولًا استخدام helpers.replace_variables مع inviter
                try:
                    message = helpers.replace_variables(
                        message_template,
                        mention=member.mention,
                        user=member.name,
                        server=member.guild.name,
                        membercount=member.guild.member_count,
                        inviter=inviter_var
                    )
                except TypeError:
                    # في حال كانت replace_variables لا تقبل kwargs جديدة، نعمل استبدال يدوي
                    bot_logger.debug('replace_variables لا تقبل "inviter" كمتغير؛ استخدام fallback replace.')
                    message = helpers.replace_variables(
                        message_template,
                        mention=member.mention,
                        user=member.name,
                        server=member.guild.name,
                        membercount=member.guild.member_count
                    )
                    if inviter_var:
                        # استبدال نصي بسيط إن كان القالب يحتوي {inviter}
                        if '{inviter}' in message:
                            message = message.replace('{inviter}', inviter_var)
                        else:
                            # إذا لم يحتوي القالب على المتغير، نضيف سطر تلقائيًا أسفل الرسالة
                            try:
                                invite_count = invite_count or (await invite_tracker.get_user_invites(guild_id, str(inviter.id)) if inviter else None)
                            except Exception:
                                invite_count = invite_count or None
                            message += f'\n\n📨 تمت الدعوة بواسطة {inviter_var} • **{invite_count if invite_count is not None else "—"}** دعوات'

                # لو replace_variables نجحت ولم يكن القالب يحتوي على {inviter} ومع ذلك وجدنا inviter،
                # نضيف سطر تلقائي لضمان ظهور معلومة من دعا العضو.
                if inviter and '{inviter}' not in (message_template or '') and '{inviter}' not in message:
                    try:
                        invite_count = invite_count or (await invite_tracker.get_user_invites(guild_id, str(inviter.id)) if inviter else None)
                    except Exception:
                        invite_count = invite_count or None
                    message += f'\n\n📨 تمت الدعوة بواسطة {inviter_var} • **{invite_count if invite_count is not None else "—"}** دعوات'

                await channel.send(message)

            bot_logger.event_processed('member_join', f'{member.name} في {member.guild.name}')

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في {channel.name}')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال الترحيب: {e}')
        except Exception as e:
            bot_logger.exception(f'خطأ غير متوقع أثناء إرسال الترحيب: {e}')

        # ==================== Auto-Role ====================
        autorole_id = await config.get_autorole(guild_id)
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
        if not bot_perms.send_messages:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return

        # إرسال رسالة الوداع
        try:
            message = settings.get('message') or config.get_default_goodbye_message()
            # الوداع عادة لا يدعم membercount على بعض البوتات؛ نركّب المتغيرات المتاحة
            try:
                message = helpers.replace_variables(
                    message,
                    user=member.name,
                    server=member.guild.name
                )
            except TypeError:
                # fallback: استبدال يدوي بسيط إن لم تقبل الدالة kwargs
                message = message.replace('{user}', member.name).replace('{server}', member.guild.name)

            await channel.send(message)

            bot_logger.event_processed('member_remove', f'{member.name} من {member.guild.name}')

        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في {channel.name}')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال الوداع: {e}')

    except Exception as e:
        bot_logger.exception('خطأ غير متوقع في handle_member_remove', e)