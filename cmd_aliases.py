"""نظام الاختصارات العربي الكامل"""
import discord
from discord.ext import commands
import re
from typing import Optional, Dict, List, Tuple

# قاموس الاختصارات العربية
ALIASES = {
    # أوامر الإدارة
    'طرد': 'kick',
    'اطرد': 'kick',
    'اطردوا': 'kick',

    'حظر': 'ban',
    'احظر': 'ban',
    'احظروا': 'ban',
    'بان': 'ban',

    'اسكت': 'timeout',
    'ميوت': 'timeout',
    'صمت': 'timeout',

    'تحذير': 'warn',
    'حذر': 'warn',
    'انذار': 'warn',

    'تحذيرات': 'warnings',
    'الانذارات': 'warnings',

    'امسح': 'purge',
    'مسح': 'purge',
    'احذف': 'purge',

    # أوامر المعلومات
    'معلومات': 'userinfo',
    'معلوماتي': 'userinfo',
    'بروفايل': 'userinfo',

    'السيرفر': 'serverinfo',
    'معلومات_السيرفر': 'serverinfo',

    'رتبة': 'rank',
    'رتبتي': 'rank',
    'مستوى': 'rank',
    'مستواي': 'rank',
    'ليفل': 'rank',

    'صدارة': 'leaderboard',
    'لوحة': 'leaderboard',
    'توب': 'leaderboard',

    'صورة': 'avatar',
    'افاتار': 'avatar',
    'بروفايل': 'avatar',

    # أوامر المرح
    'نرد': 'roll',
    'رمي': 'roll',

    'عملة': 'coinflip',
    'قلب': 'coinflip',

    'اختار': 'choose',
    'اختر': 'choose',

    # أوامر التكت
    'تكت': 'ticket',
    'تذكرة': 'ticket',

    # أوامر الإعدادات
    'اعداد': 'setup',
    'اعدادات': 'config',
    'الاعدادات': 'config',
}

# أنماط متقدمة للمطابقة
PATTERNS = [
    # طرد @user سبب
    (r'^(طرد|اطرد|اطردوا)\s+<@!?(\d+)>\s*(.*)$', 'kick'),

    # حظر @user سبب
    (r'^(حظر|احظر|احظروا|بان)\s+<@!?(\d+)>\s*(.*)$', 'ban'),

    # اسكت @user مدة سبب
    (r'^(اسكت|ميوت|صمت)\s+<@!?(\d+)>\s+(\S+)\s*(.*)$', 'timeout'),

    # تحذير @user سبب
    (r'^(تحذير|حذر|انذار)\s+<@!?(\d+)>\s+(.+)$', 'warn'),

    # تحذيرات @user
    (r'^(تحذيرات|الانذارات)\s+<@!?(\d+)>$', 'warnings'),

    # مسح عدد
    (r'^(امسح|مسح|احذف)\s+(\d+)$', 'purge'),

    # معلومات @user
    (r'^(معلومات|بروفايل)\s+<@!?(\d+)>$', 'userinfo'),

    # رتبة @user
    (r'^(رتبة|مستوى|ليفل)\s+<@!?(\d+)>$', 'rank'),

    # اختر خيار1, خيار2
    (r'^(اختار|اختر)\s+(.+)$', 'choose'),

    # نرد أرقام
    (r'^(نرد|رمي)(?:\s+(\d+))?$', 'roll'),
]

class AliasProcessor:
    """معالج الاختصارات"""

    def __init__(self):
        self.cache = {}  # تخزين مؤقت للمطابقات

    def parse_mention(self, text: str) -> Optional[str]:
        """استخراج معرف المستخدم من المنشن"""
        match = re.match(r'<@!?(\d+)>', text)
        return match.group(1) if match else None

    def find_command(self, message_content: str) -> Optional[Tuple[str, List[str]]]:
        """
        البحث عن الأمر المطابق

        Returns:
            tuple: (اسم الأمر, المعاملات) أو None
        """
        content = message_content.strip()

        # محاولة المطابقة بالأنماط المتقدمة أولاً
        for pattern, command in PATTERNS:
            match = re.match(pattern, content, re.IGNORECASE)
            if match:
                groups = match.groups()
                return command, list(groups[1:])  # تجاهل المجموعة الأولى (الأمر نفسه)

        # محاولة المطابقة البسيطة
        words = content.split()
        if not words:
            return None

        first_word = words[0].lower()

        if first_word in ALIASES:
            command = ALIASES[first_word]
            args = words[1:]
            return command, args

        return None

    async def convert_to_slash_command(
        self,
        bot: commands.Bot,
        message: discord.Message,
        command: str,
        args: List[str]
    ) -> bool:
        """
        تحويل الأمر النصي إلى Slash Command

        Returns:
            bool: نجح التحويل؟
        """
        try:
            # الحصول على الأمر من tree
            tree_command = bot.tree.get_command(command)

            if not tree_command:
                return False

            # إنشاء interaction وهمي
            # ملاحظة: هذا حل مؤقت - الأفضل استخدام message commands
            await message.channel.send(
                f'💡 استخدم `/{command}` بدلاً من `{message.content}`',
                delete_after=5
            )
            return True

        except Exception as e:
            print(f'خطأ في تحويل الأمر: {e}')
            return False

    async def execute_alias(
        self,
        bot: commands.Bot,
        message: discord.Message,
        command: str,
        args: List[str]
    ) -> bool:
        """
        تنفيذ الأمر المختصر

        Returns:
            bool: نجح التنفيذ؟
        """
        try:
            # معالجة خاصة لكل أمر
            if command == 'kick':
                if len(args) < 1:
                    await message.channel.send('❌ الاستخدام: `طرد @user [سبب]`', delete_after=5)
                    return False

                user_id = self.parse_mention(args[0])
                if not user_id:
                    await message.channel.send('❌ منشن العضو غير صحيح!', delete_after=5)
                    return False

                member = message.guild.get_member(int(user_id))
                if not member:
                    await message.channel.send('❌ لم أجد هذا العضو!', delete_after=5)
                    return False

                reason = ' '.join(args[1:]) if len(args) > 1 else 'لا يوجد سبب'

                # التحقق من الصلاحيات
                if not message.author.guild_permissions.kick_members:
                    await message.channel.send('❌ ليس لديك صلاحية الطرد!', delete_after=5)
                    return False

                # الطرد
                await member.kick(reason=reason)
                await message.channel.send(f'✅ تم طرد {member.mention} — {reason}')
                return True

            elif command == 'ban':
                if len(args) < 1:
                    await message.channel.send('❌ الاستخدام: `حظر @user [سبب]`', delete_after=5)
                    return False

                user_id = self.parse_mention(args[0])
                if not user_id:
                    await message.channel.send('❌ منشن العضو غير صحيح!', delete_after=5)
                    return False

                member = message.guild.get_member(int(user_id))
                if not member:
                    await message.channel.send('❌ لم أجد هذا العضو!', delete_after=5)
                    return False

                reason = ' '.join(args[1:]) if len(args) > 1 else 'لا يوجد سبب'

                # التحقق من الصلاحيات
                if not message.author.guild_permissions.ban_members:
                    await message.channel.send('❌ ليس لديك صلاحية الحظر!', delete_after=5)
                    return False

                # الحظر
                await member.ban(reason=reason)
                await message.channel.send(f'✅ تم حظر {member.mention} — {reason}')
                return True

            elif command == 'purge':
                if len(args) < 1:
                    await message.channel.send('❌ الاستخدام: `مسح [عدد]`', delete_after=5)
                    return False

                try:
                    count = int(args[0])
                except ValueError:
                    await message.channel.send('❌ العدد غير صحيح!', delete_after=5)
                    return False

                if count < 1 or count > 100:
                    await message.channel.send('❌ العدد يجب أن يكون بين 1-100!', delete_after=5)
                    return False

                # التحقق من الصلاحيات
                if not message.author.guild_permissions.manage_messages:
                    await message.channel.send('❌ ليس لديك صلاحية إدارة الرسائل!', delete_after=5)
                    return False

                # حذف الرسالة الأصلية
                await message.delete()

                # مسح الرسائل
                deleted = await message.channel.purge(limit=count)

                # رسالة تأكيد مؤقتة
                confirm = await message.channel.send(f'✅ تم مسح {len(deleted)} رسالة.')
                await confirm.delete(delay=5)
                return True

            elif command in ['userinfo', 'serverinfo', 'rank', 'leaderboard', 'avatar']:
                # هذه الأوامر تحتاج slash commands فقط
                await message.channel.send(
                    f'💡 استخدم `/{command}` للحصول على معلومات كاملة!',
                    delete_after=5
                )
                return True

            elif command in ['roll', 'coinflip', 'choose']:
                # أوامر المرح - توجيه لـ slash commands
                await message.channel.send(
                    f'💡 استخدم `/{command}` للعب!',
                    delete_after=5
                )
                return True

            else:
                return await self.convert_to_slash_command(bot, message, command, args)

        except Exception as e:
            print(f'خطأ في تنفيذ الأمر: {e}')
            import traceback
            traceback.print_exc()
            return False

# إنشاء معالج عام
alias_processor = AliasProcessor()

async def process_aliases(bot: commands.Bot, message: discord.Message):
    """
    معالجة الاختصارات في الرسائل

    هذه الدالة يتم استدعاؤها من main.py في on_message
    """
    # تجاهل البوتات
    if message.author.bot:
        return

    # تجاهل الرسائل الخاصة
    if not message.guild:
        return

    # تجاهل الرسائل التي تبدأ بـ /
    if message.content.startswith('/'):
        return

    # البحث عن أمر مطابق
    result = alias_processor.find_command(message.content)

    if not result:
        return

    command, args = result

    # تنفيذ الأمر
    await alias_processor.execute_alias(bot, message, command, args)

async def add_custom_alias(guild_id: str, arabic: str, english: str):
    """إضافة اختصار مخصص (للمستقبل)"""
    # يمكن حفظها في قاعدة البيانات لاحقاً
    ALIASES[arabic.lower()] = english.lower()

def get_all_aliases() -> Dict[str, str]:
    """الحصول على جميع الاختصارات"""
    return ALIASES.copy()

def format_aliases_help() -> str:
    """تنسيق مساعدة الاختصارات"""
    lines = ['📝 **قائمة الاختصارات المتاحة:**\n']

    categories = {
        'الإدارة': ['طرد', 'حظر', 'اسكت', 'تحذير', 'مسح'],
        'المعلومات': ['معلومات', 'السيرفر', 'رتبة', 'صدارة', 'صورة'],
        'المرح': ['نرد', 'عملة', 'اختار'],
    }

    for category, commands in categories.items():
        lines.append(f'\n**{category}:**')
        for cmd in commands:
            if cmd in ALIASES:
                lines.append(f'• `{cmd}` → `/{ALIASES[cmd]}`')

    lines.append('\n**أمثلة:**')
    lines.append('• `طرد @user سبام`')
    lines.append('• `مسح 10`')
    lines.append('• `رتبتي`')
    lines.append('• `نرد`')

    return '\n'.join(lines)