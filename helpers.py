"""
دوال مساعدة عامة للبوت
"""

import discord
import re
from datetime import datetime, timedelta
from typing import Optional, Union, List
import random

# ==================== تنسيق الوقت ====================

def parse_time(time_str: str) -> Optional[timedelta]:
    """
    تحويل نص الوقت إلى timedelta
    مثال: "10m" -> 10 دقائق, "2h" -> ساعتين, "1d" -> يوم
    """
    pattern = r'^(\d+)([smhd])$'
    match = re.match(pattern, time_str.lower())

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == 's':
        return timedelta(seconds=amount)
    elif unit == 'm':
        return timedelta(minutes=amount)
    elif unit == 'h':
        return timedelta(hours=amount)
    elif unit == 'd':
        return timedelta(days=amount)

    return None

def format_time(seconds: int) -> str:
    """تنسيق الثواني إلى نص قابل للقراءة"""
    if seconds < 60:
        return f'{seconds} ثانية'
    elif seconds < 3600:
        minutes = seconds // 60
        return f'{minutes} دقيقة'
    elif seconds < 86400:
        hours = seconds // 3600
        return f'{hours} ساعة'
    else:
        days = seconds // 86400
        return f'{days} يوم'

def format_datetime(dt: Union[datetime, str]) -> str:
    """تنسيق التاريخ والوقت"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# ==================== معالجة النصوص ====================

def replace_variables(text: str, **kwargs) -> str:
    """
    استبدال المتغيرات في النص
    مثال: replace_variables("مرحباً {user}", user="أحمد")
    """
    for key, value in kwargs.items():
        text = text.replace(f'{{{key}}}', str(value))
    return text

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """اختصار النص"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_text(text: str) -> str:
    """تنظيف النص من الأحرف الخاصة"""
    return re.sub(r'[^\w\s\u0600-\u06FF]', '', text)

def contains_link(text: str) -> bool:
    """التحقق من وجود رابط في النص"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return bool(re.search(url_pattern, text))

def extract_links(text: str) -> List[str]:
    """استخراج جميع الروابط من النص"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

# ==================== Discord Helpers ====================

def get_member_color(member: discord.Member) -> discord.Color:
    """الحصول على لون العضو"""
    return member.color if member.color != discord.Color.default() else discord.Color.blue()

def format_user(user: Union[discord.User, discord.Member]) -> str:
    """تنسيق اسم المستخدم"""
    return f'{user.name}#{user.discriminator}' if user.discriminator != '0' else user.name

def get_user_avatar(user: Union[discord.User, discord.Member]) -> str:
    """الحصول على رابط صورة البروفايل"""
    return user.display_avatar.url

def safe_send(channel: discord.TextChannel, content: str = None, embed: discord.Embed = None):
    """إرسال رسالة مع معالجة الأخطاء"""
    try:
        return channel.send(content=content, embed=embed)
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        return None

# ==================== رسائل التأكيد ====================

async def confirm_action(interaction: discord.Interaction, message: str, timeout: int = 30) -> bool:
    """
    طلب تأكيد من المستخدم
    """
    view = ConfirmView(timeout=timeout)
    await interaction.response.send_message(message, view=view, ephemeral=True)

    await view.wait()
    return view.value

class ConfirmView(discord.ui.View):
    """عرض أزرار التأكيد"""
    def __init__(self, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label='تأكيد', style=discord.ButtonStyle.green, emoji='✅')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label='إلغاء', style=discord.ButtonStyle.red, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

# ==================== الترقيم والصفحات ====================

def paginate_list(items: List, per_page: int = 10) -> List[List]:
    """تقسيم قائمة إلى صفحات"""
    return [items[i:i + per_page] for i in range(0, len(items), per_page)]

class PaginationView(discord.ui.View):
    """عرض الصفحات"""
    def __init__(self, pages: List[discord.Embed], timeout: int = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.message: Optional[discord.Message] = None

        self.update_buttons()

    def update_buttons(self):
        """تحديث حالة الأزرار"""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.pages) - 1
        self.last_page.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(emoji='⏮️', style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji='◀️', style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji='▶️', style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji='⏭️', style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(emoji='🗑️', style=discord.ButtonStyle.red)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()

# ==================== التحقق من الصلاحيات ====================

def has_permission(member: discord.Member, permission: str) -> bool:
    """التحقق من صلاحية محددة"""
    perms = member.guild_permissions
    return getattr(perms, permission, False)

def is_mod(member: discord.Member) -> bool:
    """التحقق إذا كان العضو مشرف"""
    return (
        member.guild_permissions.kick_members or
        member.guild_permissions.ban_members or
        member.guild_permissions.manage_messages or
        member.guild_permissions.administrator
    )

def is_admin(member: discord.Member) -> bool:
    """التحقق إذا كان العضو أدمن"""
    return member.guild_permissions.administrator

# ==================== الأرقام العشوائية والاختيارات ====================

def random_color() -> discord.Color:
    """لون عشوائي"""
    return discord.Color.from_rgb(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )

def choose_random(items: List) -> any:
    """اختيار عشوائي من قائمة"""
    return random.choice(items) if items else None

def roll_chance(percentage: int) -> bool:
    """فرصة عشوائية (0-100)"""
    return random.randint(1, 100) <= percentage

# ==================== معالجة المستخدم والأدوار ====================

async def get_or_fetch_user(bot: discord.Client, user_id: int) -> Optional[discord.User]:
    """الحصول على المستخدم من الكاش أو جلبه"""
    user = bot.get_user(user_id)
    if user:
        return user
    try:
        return await bot.fetch_user(user_id)
    except discord.NotFound:
        return None

async def get_or_fetch_member(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    """الحصول على العضو من الكاش أو جلبه"""
    member = guild.get_member(user_id)
    if member:
        return member
    try:
        return await guild.fetch_member(user_id)
    except discord.NotFound:
        return None

def get_role_by_name(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    """الحصول على دور بالاسم"""
    return discord.utils.get(guild.roles, name=name)

def get_role_by_id(guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
    """الحصول على دور بالـ ID"""
    return guild.get_role(role_id)

# ==================== تنسيق القوائم ====================

def format_list(items: List, prefix: str = '•') -> str:
    """تنسيق قائمة إلى نص"""
    if not items:
        return 'لا يوجد عناصر'
    return '\n'.join([f'{prefix} {item}' for item in items])

def format_numbered_list(items: List) -> str:
    """تنسيق قائمة مرقمة"""
    if not items:
        return 'لا يوجد عناصر'
    return '\n'.join([f'{i+1}. {item}' for i, item in enumerate(items)])

# ==================== التحقق من المحتوى ====================

def is_spam(messages: List[discord.Message], threshold: int = 5, time_window: int = 5) -> bool:
    """
    التحقق من السبام
    threshold: عدد الرسائل
    time_window: الوقت بالثواني
    """
    if len(messages) < threshold:
        return False

    now = datetime.now()
    recent_messages = [
        msg for msg in messages 
        if (now - msg.created_at).total_seconds() <= time_window
    ]

    return len(recent_messages) >= threshold

def contains_mass_mention(message: discord.Message, threshold: int = 5) -> bool:
    """التحقق من المنشن الجماعي"""
    return len(message.mentions) >= threshold

# ==================== أخرى ====================

def get_guild_icon(guild: discord.Guild) -> str:
    """الحصول على أيقونة السيرفر"""
    return guild.icon.url if guild.icon else None

def get_invite_link(bot: discord.Client) -> str:
    """الحصول على رابط دعوة البوت"""
    return discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True)
    )

def bytes_to_readable(size: int) -> str:
    """تحويل البايتات إلى قراءة سهلة"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

import hashlib

def generate_hash(text: str) -> str:
    """
    توليد hash للنص

    Args:
        text: النص

    Returns:
        str: hash بصيغة SHA256
    """
    return hashlib.sha256(text.encode()).hexdigest()[:16]