# ==================== event_welcome.py - IMPROVED ====================
"""
أحداث الترحيب والوداع
✅ تم إضافة نظام تتبع الدعوات
✅ إظهار من دعا العضو في الترحيب
✅ دعم متغير {inviter} قابل للتخصيص
✅ Guards شاملة
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
        inviter_name = "غير معروف"
        invite_count = 0
        
        try:
            # محاولة اكتشاف من دعا العضو
            inviter = await invite_tracker.find_inviter(member)
            
            if inviter:
                # جلب عدد الدعوات
                invite_count = await invite_tracker.get_user_invites(guild_id, str(inviter.id))
                inviter_name = inviter.mention  # أو inviter.name حسب التفضيل
                
                # التحقق من المكافآت
                await invite_rewards.check_rewards(
                    member.guild,
                    inviter,
                    invite_count
                )
                
                bot_logger.info(
                    f'{member.name} انضم إلى {member.guild.name} '
                    f'بدعوة من {inviter.name} (إجمالي: {invite_count})'
                )
            else:
                # لم يتم العثور على الداعي
                inviter_name = "رابط دعوة خاص"
                bot_logger.info(f'{member.name} انضم عبر رابط خاص أو Vanity URL')
        
        except Exception as e:
            bot_logger.error(f'خطأ في تتبع الدعوة: {e}')
            inviter_name = "غير متاح"
            # نكمل حتى لو فشل تتبع الدعوات
        
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
        if not bot_perms.send_messages or not bot_perms.embed_links:
            bot_logger.warning(f'البوت لا يملك صلاحيات الإرسال في {channel.name}')
            return
        
        # إرسال الرسالة
        try:
            if settings.get('type') == 'embed':
                # Embed مع معلومات الدعوة
                embed = embeds.welcome_embed(member, member.guild.member_count)
                
                # إضافة معلومات الدعوة (اختياري - فقط إذا كانت مفعلة)
                if settings.get('show_inviter', True) and inviter:
                    embed.add_field(
                        name='📨 تمت الدعوة بواسطة',
                        value=f'{inviter.mention} • **{invite_count}** دعوات',
                        inline=False
                    )
                elif settings.get('show_inviter', True):
                    embed.add_field(
                        name='📨 طريقة الانضمام',
                        value=inviter_name,
                        inline=False
                    )
                
                await channel.send(embed=embed)
            
            else:
                # رسالة نصية مع دعم متغير {inviter}
                message = settings.get('message') or config.get_default_welcome_message()
                message = helpers.replace_variables(
                    message,
                    mention=member.mention,
                    user=member.name,
                    server=member.guild.name,
                    membercount=member.guild.member_count,
                    inviter=inviter_name,  # ← المتغير الجديد
                    invitecount=invite_count  # عدد دعوات الداعي
                )
                
                await channel.send(message)
            
            bot_logger.event_processed('member_join', f'{member.name} في {member.guild.name}')
        
        except discord.Forbidden:
            bot_logger.error(f'Forbidden: لا يمكن الإرسال في {channel.name}')
        except discord.HTTPException as e:
            bot_logger.error(f'HTTPException في إرسال الترحيب: {e}')
        
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