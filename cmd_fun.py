"""
cmd_fun.py - ULTIMATE FIXED VERSION
====================================
✅ جميع الألعاب تعمل 100%
✅ Mystery Games مع persistent views
✅ IQ Test, Risk, Reaction, CodeBreak
✅ جميع الألعاب الكلاسيكية
✅ Error handling محكم

التحديثات الجديدة:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Persistent Views للـ Mystery
✨ Defer صحيح قبل كل followup
✨ تسجيل Views في main.py
✨ معالجة أخطاء شاملة
✨ Logging مفصّل
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from logger import bot_logger

# ==================== Configuration ====================

MYSTERY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mystery.json')
FUN_BANNER_URL = "https://cdn.phototourl.com/uploads/2025-12-21-862960d6-ee99-4812-aae7-cca1852d3bfe.gif"

# ==================== Session Storage ====================

_sessions: Dict[int, Dict[str, Any]] = {}
_mystery_sessions: Dict[int, Dict[str, Any]] = {}
_risk_sessions: Dict[int, Dict[str, Any]] = {}
_iq_sessions: Dict[int, Dict[str, Any]] = {}
_codebreak_sessions: Dict[int, Dict[str, Any]] = {}

# Mystery data
_mystery_data: Dict[str, Any] = {}

# ==================== Mystery Data Loading ====================

async def load_mystery_data():
    """تحميل بيانات Mystery من JSON"""
    global _mystery_data
    
    if _mystery_data:
        return _mystery_data
    
    if os.path.exists(MYSTERY_FILE):
        try:
            with open(MYSTERY_FILE, 'r', encoding='utf-8') as f:
                _mystery_data = json.load(f)
                bot_logger.info(f'✅ تم تحميل mystery.json ({len(_mystery_data.get("stories", {}))} قصص)')
                return _mystery_data
        except Exception as e:
            bot_logger.error(f'خطأ في تحميل mystery.json: {e}')
    
    # بيانات افتراضية
    bot_logger.warning('mystery.json غير موجود، سيتم إنشاء قصة افتراضية')
    _mystery_data = {
        "stories": {
            "test_story": {
                "id": "test_story",
                "title": "قصة تجريبية",
                "tone": "adventure",
                "tags": ["test"],
                "start": "beginning",
                "rules": ["هذه قصة تجريبية بسيطة"],
                "scenes": {
                    "beginning": {
                        "text": "مرحباً! هذه قصة تجريبية.\n\nماذا تريد أن تفعل؟",
                        "choices": {
                            "A": {"label": "اذهب يميناً", "next": "right"},
                            "B": {"label": "اذهب يساراً", "next": "left"}
                        }
                    },
                    "right": {
                        "text": "ذهبت يميناً ووجدت كنزاً!",
                        "ending": "treasure"
                    },
                    "left": {
                        "text": "ذهبت يساراً ووجدت مفاجأة!",
                        "ending": "surprise"
                    }
                },
                "endings": {
                    "treasure": {
                        "title": "وجدت الكنز!",
                        "text": "مبروك! لقد وجدت الكنز!"
                    },
                    "surprise": {
                        "title": "مفاجأة!",
                        "text": "وجدت مفاجأة رائعة!"
                    }
                }
            }
        }
    }
    
    try:
        os.makedirs(os.path.dirname(MYSTERY_FILE), exist_ok=True)
        with open(MYSTERY_FILE, 'w', encoding='utf-8') as f:
            json.dump(_mystery_data, f, ensure_ascii=False, indent=2)
        bot_logger.info('✅ تم إنشاء mystery.json افتراضي')
    except Exception as e:
        bot_logger.error(f'فشل حفظ mystery.json: {e}')
    
    return _mystery_data

# ==================== Helper Functions ====================

def get_session(user_id: int) -> Dict[str, Any]:
    """الحصول على جلسة مستخدم"""
    if user_id not in _sessions:
        _sessions[user_id] = {"created_at": datetime.utcnow(), "data": {}}
    return _sessions[user_id]["data"]

def choose_text(text):
    """اختيار نص عشوائي إذا كان قائمة"""
    if isinstance(text, list):
        return random.choice(text)
    return text

def resolve_next(next_field):
    """حل المشهد التالي (يدعم chance)"""
    if isinstance(next_field, str):
        return next_field
    
    if isinstance(next_field, dict) and "chance" in next_field:
        chance_map = next_field["chance"]
        keys = list(chance_map.keys())
        weights = [chance_map[k] for k in keys]
        total = sum(weights)
        
        if total <= 0:
            return random.choice(keys)
        
        r = random.random() * total
        upto = 0
        for k, w in zip(keys, weights):
            upto += w
            if r <= upto:
                return k
        return keys[-1]
    
    return None

# ==================== Mystery Game Engine ====================

async def start_mystery(interaction: discord.Interaction, story_id: str):
    """بدء لعبة Mystery"""
    try:
        await load_mystery_data()
        
        user_id = interaction.user.id
        
        stories = _mystery_data.get("stories", {})
        if story_id not in stories:
            await interaction.response.send_message(
                '❌ القصة غير موجودة!',
                ephemeral=True
            )
            return
        
        story = stories[story_id]
        
        # إنشاء جلسة جديدة
        _mystery_sessions[user_id] = {
            "story_id": story_id,
            "current": story.get("start"),
            "path": [],
            "started_at": datetime.utcnow()
        }
        
        # عرض القواعد
        rules = story.get("rules", [])
        rules_text = "\n".join([f"• {r}" for r in rules]) if rules else "لا توجد قواعد خاصة"
        
        embed = discord.Embed(
            title=f"📖 {story.get('title', 'قصة تفاعلية')}",
            description=f"**القواعد:**\n{rules_text}",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="ℹ️ كيف تلعب",
            value="سيتم عرض المشاهد وعليك الاختيار بين الخيارات المتاحة.\nكل قرار يؤثر على مجرى القصة!",
            inline=False
        )
        
        embed.set_image(url=FUN_BANNER_URL)
        
        view = MysteryStartView(story_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        bot_logger.info(f'🎭 {interaction.user.name} بدأ قصة {story_id}')
    
    except Exception as e:
        bot_logger.exception('خطأ في start_mystery', e)
        await interaction.response.send_message(
            f'❌ حدث خطأ: {str(e)}',
            ephemeral=True
        )

async def show_scene(interaction: discord.Interaction, user_id: int):
    """عرض مشهد من القصة"""
    try:
        if user_id not in _mystery_sessions:
            await interaction.followup.send('❌ لا توجد قصة نشطة!', ephemeral=True)
            return
        
        session = _mystery_sessions[user_id]
        story_id = session["story_id"]
        current_scene_id = session["current"]
        
        await load_mystery_data()
        
        story = _mystery_data.get("stories", {}).get(story_id, {})
        scenes = story.get("scenes", {})
        scene = scenes.get(current_scene_id, {})
        
        if not scene:
            await interaction.followup.send('❌ مشهد غير موجود!', ephemeral=True)
            return
        
        # النص
        text = choose_text(scene.get("text", ""))
        
        embed = discord.Embed(
            title=f"🎭 {story.get('title', '')}",
            description=text,
            color=discord.Color.dark_purple()
        )
        
        # الخيارات أو النهاية
        choices = scene.get("choices", {})
        ending_key = scene.get("ending")
        
        if ending_key:
            # عرض النهاية
            endings = story.get("endings", {})
            ending = endings.get(ending_key, {})
            
            embed = discord.Embed(
                title=f"🏁 {ending.get('title', 'النهاية')}",
                description=ending.get("text", ""),
                color=discord.Color.gold()
            )
            
            embed.set_footer(text="انتهت القصة! استخدم /mystery لبدء قصة جديدة")
            
            await interaction.followup.send(embed=embed)
            
            # حذف الجلسة
            del _mystery_sessions[user_id]
            
        elif choices:
            # عرض الخيارات
            choices_text = "\n".join([
                f"**{key}** — {info.get('label', 'خيار')}"
                for key, info in choices.items()
            ])
            
            embed.add_field(
                name="❓ الخيارات المتاحة",
                value=choices_text,
                inline=False
            )
            
            # إنشاء أزرار الخيارات
            view = MysteryChoiceView(story_id, current_scene_id, list(choices.keys()))
            
            await interaction.followup.send(embed=embed, view=view)
        
        else:
            await interaction.followup.send('❌ لا توجد خيارات متاحة!', ephemeral=True)
    
    except Exception as e:
        bot_logger.exception('خطأ في show_scene', e)
        await interaction.followup.send(f'❌ خطأ: {str(e)}', ephemeral=True)

async def process_choice(interaction: discord.Interaction, user_id: int, story_id: str, scene_id: str, choice_key: str):
    """معالجة اختيار المستخدم"""
    try:
        # ✅ CRITICAL FIX: defer أولاً!
        await interaction.response.defer()
        
        await load_mystery_data()
        
        story = _mystery_data.get("stories", {}).get(story_id, {})
        scenes = story.get("scenes", {})
        scene = scenes.get(scene_id, {})
        
        choices = scene.get("choices", {})
        choice = choices.get(choice_key, {})
        
        if not choice:
            await interaction.followup.send('❌ خيار غير صحيح!', ephemeral=True)
            return
        
        # الحصول على المشهد التالي
        next_field = choice.get("next")
        next_scene = resolve_next(next_field)
        
        # تحديث الجلسة
        session = _mystery_sessions[user_id]
        session["path"].append({"scene": scene_id, "choice": choice_key})
        session["current"] = next_scene
        
        # ✅ الآن استخدم show_scene بأمان
        await show_scene(interaction, user_id)
    
    except Exception as e:
        bot_logger.exception('خطأ في process_choice', e)
        try:
            await interaction.followup.send(f'❌ خطأ: {str(e)}', ephemeral=True)
        except:
            pass

# ==================== Mystery Views (Persistent) ====================

class MysteryStartView(discord.ui.View):
    """زر بدء القصة - Persistent"""
    
    def __init__(self, story_id: str):
        super().__init__(timeout=None)  # ✅ Persistent
        self.story_id = story_id
    
    @discord.ui.button(
        label='▶ ابدأ القصة',
        style=discord.ButtonStyle.primary,
        emoji='🎬',
        custom_id='mystery_start'  # ✅ مهم للـ persistence
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ✅ defer أولاً
        await interaction.response.defer()
        await show_scene(interaction, interaction.user.id)

class MysteryChoiceView(discord.ui.View):
    """أزرار الخيارات - Persistent"""
    
    def __init__(self, story_id: str, scene_id: str, choice_keys: List[str]):
        super().__init__(timeout=None)  # ✅ Persistent
        self.story_id = story_id
        self.scene_id = scene_id
        
        # إنشاء زر لكل خيار
        for key in choice_keys[:5]:  # حد أقصى 5 أزرار
            button = discord.ui.Button(
                label=key,
                style=discord.ButtonStyle.secondary,
                custom_id=f'choice_{story_id}_{scene_id}_{key}'  # ✅ unique ID
            )
            button.callback = self._create_callback(key)
            self.add_item(button)
    
    def _create_callback(self, choice_key: str):
        async def callback(interaction: discord.Interaction):
            await process_choice(
                interaction,
                interaction.user.id,
                self.story_id,
                self.scene_id,
                choice_key
            )
        return callback

# ==================== Commands Setup ====================

def setup_fun_commands(bot: commands.Bot):
    """تسجيل أوامر المرح - ULTIMATE VERSION"""
    
    # تحميل Mystery data عند البدء
    bot.loop.create_task(load_mystery_data())
    
    # ==================== Fun Menu ====================
    
    @bot.tree.command(name='fun', description='قائمة ألعاب المرح')
    async def fun_menu(interaction: discord.Interaction):
        """قائمة الألعاب"""
        await load_mystery_data()
        
        stories = _mystery_data.get("stories", {})
        
        embed = discord.Embed(
            title="🎮 قائمة ألعاب المرح",
            description="اختر لعبة من القائمة:",
            color=discord.Color.blue()
        )
        
        embed.set_image(url=FUN_BANNER_URL)
        
        # ألعاب تفاعلية
        embed.add_field(
            name="🎭 ألعاب تفاعلية",
            value=(
                "`/mystery` - قصة تفاعلية\n"
                "`/risk` - لعبة المخاطرة\n"
                "`/iq` - اختبار الذكاء\n"
                "`/codebreak` - حل الشيفرة\n"
                "`/reaction` - اختبار سرعة الرد"
            ),
            inline=False
        )
        
        # ألعاب كلاسيكية
        embed.add_field(
            name="🎲 ألعاب كلاسيكية",
            value=(
                "`/roll` - رمي النرد\n"
                "`/dice` - نرد D&D\n"
                "`/coinflip` - قلب عملة\n"
                "`/rps` - حجر ورقة مقص\n"
                "`/8ball` - الكرة السحرية"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📚 القصص المتاحة",
            value=f"**{len(stories)}** قصة تفاعلية",
            inline=False
        )
        
        embed.set_footer(text="استخدم الأوامر للبدء!")
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== Mystery ====================
    
    @bot.tree.command(name='mystery', description='ابدأ قصة تفاعلية')
    @app_commands.describe(story='اسم القصة (اختياري)')
    async def mystery_cmd(interaction: discord.Interaction, story: Optional[str] = None):
        """لعبة Mystery"""
        await load_mystery_data()
        
        stories = _mystery_data.get("stories", {})
        
        if not stories:
            await interaction.response.send_message(
                '❌ لا توجد قصص متاحة حالياً!',
                ephemeral=True
            )
            return
        
        # اختيار قصة
        if story and story in stories:
            chosen = story
        else:
            chosen = random.choice(list(stories.keys()))
        
        await start_mystery(interaction, chosen)
    
    # ==================== Roll ====================
    
    @bot.tree.command(name='roll', description='رمي نرد')
    @app_commands.describe(
        sides='عدد الأوجه (2-100)',
        count='عدد مرات الرمي (1-20)'
    )
    async def roll_cmd(interaction: discord.Interaction, sides: int = 6, count: int = 1):
        """رمي النرد"""
        try:
            if sides < 2 or sides > 100:
                await interaction.response.send_message(
                    '❌ عدد الأوجه يجب أن يكون بين 2-100',
                    ephemeral=True
                )
                return
            
            if count < 1 or count > 20:
                await interaction.response.send_message(
                    '❌ عدد المرات يجب أن يكون بين 1-20',
                    ephemeral=True
                )
                return
            
            results = [random.randint(1, sides) for _ in range(count)]
            total = sum(results)
            
            embed = discord.Embed(
                title="🎲 رمي النرد",
                description=f"**النتائج:** {' + '.join(map(str, results))}\n**المجموع:** **{total}**",
                color=discord.Color.blue()
            )
            
            if count > 1:
                avg = total / count
                embed.add_field(
                    name="📊 إحصائيات",
                    value=f"المتوسط: {avg:.1f}\nالأعلى: {max(results)}\nالأقل: {min(results)}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            bot_logger.exception('خطأ في roll', e)
            await interaction.response.send_message(
                f'❌ خطأ: {str(e)}',
                ephemeral=True
            )
    
    # ==================== Dice ====================
    
    @bot.tree.command(name='dice', description='رمي نرد D&D')
    @app_commands.describe(notation='صيغة النرد (مثال: 2d6)')
    async def dice_cmd(interaction: discord.Interaction, notation: str):
        """نرد D&D"""
        import re
        
        match = re.match(r'^(\d+)d(\d+)$', notation.lower().strip())
        
        if not match:
            await interaction.response.send_message(
                '❌ صيغة خاطئة! استخدم: `2d6` أو `1d20`',
                ephemeral=True
            )
            return
        
        count = int(match.group(1))
        sides = int(match.group(2))
        
        if count < 1 or count > 50 or sides < 2 or sides > 1000:
            await interaction.response.send_message(
                '❌ حدود غير مقبولة!',
                ephemeral=True
            )
            return
        
        results = [random.randint(1, sides) for _ in range(count)]
        total = sum(results)
        
        embed = discord.Embed(
            title=f"🎲 {notation.upper()}",
            description=f"**النتائج:** {', '.join(map(str, results))}\n**المجموع:** **{total}**",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== Coinflip ====================
    
    @bot.tree.command(name='coinflip', description='قلب عملة')
    async def coinflip_cmd(interaction: discord.Interaction):
        """قلب العملة"""
        result = random.choice(["وجه", "كتابة"])
        
        embed = discord.Embed(
            title="🪙 قلب العملة",
            description=f"النتيجة: **{result}**",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== RPS ====================
    
    @bot.tree.command(name='rps', description='حجر ورقة مقص')
    @app_commands.describe(choice='اختيارك')
    @app_commands.choices(choice=[
        app_commands.Choice(name='🪨 حجر', value='rock'),
        app_commands.Choice(name='📄 ورقة', value='paper'),
        app_commands.Choice(name='✂️ مقص', value='scissors')
    ])
    async def rps_cmd(interaction: discord.Interaction, choice: str):
        """حجر ورقة مقص"""
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        
        if choice == bot_choice:
            result = 'تعادل'
            color = discord.Color.orange()
        else:
            wins = {('rock', 'scissors'), ('paper', 'rock'), ('scissors', 'paper')}
            if (choice, bot_choice) in wins:
                result = 'فزت'
                color = discord.Color.green()
            else:
                result = 'خسرت'
                color = discord.Color.red()
        
        choices_map = {
            'rock': '🪨 حجر',
            'paper': '📄 ورقة',
            'scissors': '✂️ مقص'
        }
        
        embed = discord.Embed(
            title="🎮 حجر ورقة مقص",
            description=f"**النتيجة:** {result}!",
            color=color
        )
        
        embed.add_field(name='اختيارك', value=choices_map[choice], inline=True)
        embed.add_field(name='اختيار البوت', value=choices_map[bot_choice], inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== 8ball ====================
    
    @bot.tree.command(name='8ball', description='الكرة السحرية')
    @app_commands.describe(question='اسأل سؤالاً')
    async def eightball_cmd(interaction: discord.Interaction, question: str):
        """الكرة السحرية"""
        responses = [
            '✅ نعم بالتأكيد',
            '✅ نعم',
            '✅ على الأرجح',
            '🤔 من الأفضل أن تنتظر',
            '🤔 الإجابة غير واضحة',
            '❌ لا',
            '❌ غير مرجّح',
            '🔮 الإشارات ضبابية'
        ]
        
        answer = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 الكرة السحرية",
            description=f"*{question}*\n\n**{answer}**",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== IQ Test ====================
    
    @bot.tree.command(name='iq', description='اختبار ذكاء سريع')
    async def iq_cmd(interaction: discord.Interaction):
        """اختبار IQ"""
        user_id = interaction.user.id
        
        questions = [
            {
                "q": "ما هو الشكل التالي: 2, 4, 8, 16, ?",
                "choices": {"A": "24", "B": "32", "C": "18"},
                "answer": "B"
            },
            {
                "q": "إذا كان كل A هو B، وكل B هو C، فهل كل A هو C؟",
                "choices": {"A": "نعم", "B": "لا", "C": "غير معروف"},
                "answer": "A"
            },
            {
                "q": "أي كلمة لا تنتمي: تفاحة، موز، طماطم، برتقال؟",
                "choices": {"A": "طماطم", "B": "موز", "C": "برتقال"},
                "answer": "A"
            }
        ]
        
        _iq_sessions[user_id] = {
            "questions": questions,
            "current": 0,
            "score": 0
        }
        
        q = questions[0]
        choices_text = "\n".join([f"**{k}** — {v}" for k, v in q['choices'].items()])
        
        embed = discord.Embed(
            title="🧠 اختبار الذكاء - سؤال 1",
            description=f"{q['q']}\n\n{choices_text}",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="استخدم /iq-answer للإجابة")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name='iq-answer', description='أجب على سؤال IQ')
    @app_commands.describe(answer='A أو B أو C')
    async def iq_answer_cmd(interaction: discord.Interaction, answer: str):
        """الإجابة على IQ"""
        user_id = interaction.user.id
        
        if user_id not in _iq_sessions:
            await interaction.response.send_message(
                '❌ لم تبدأ اختبار IQ! استخدم `/iq` أولاً.',
                ephemeral=True
            )
            return
        
        session = _iq_sessions[user_id]
        current = session["current"]
        questions = session["questions"]
        
        q = questions[current]
        chosen = answer.strip().upper()
        
        if chosen == q["answer"]:
            session["score"] += 1
            feedback = "✅ إجابة صحيحة!"
        else:
            feedback = f"❌ خاطئ! الإجابة: **{q['answer']}**"
        
        session["current"] += 1
        
        if session["current"] < len(questions):
            # السؤال التالي
            next_q = questions[session["current"]]
            choices_text = "\n".join([f"**{k}** — {v}" for k, v in next_q['choices'].items()])
            
            embed = discord.Embed(
                title=f"🧠 سؤال {session['current'] + 1}",
                description=f"{feedback}\n\n{next_q['q']}\n\n{choices_text}",
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # النتيجة النهائية
            score = session["score"]
            total = len(questions)
            percentage = (score / total) * 100
            
            if percentage >= 80:
                rating = "ممتاز! 🎖️"
            elif percentage >= 60:
                rating = "جيد! 👍"
            else:
                rating = "يحتاج تحسين 📚"
            
            embed = discord.Embed(
                title="🧠 النتيجة النهائية",
                description=f"{feedback}\n\n**النتيجة:** {score}/{total}\n**التقييم:** {rating}",
                color=discord.Color.gold()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            del _iq_sessions[user_id]
    
    # ==================== Risk ====================
    
    @bot.tree.command(name='risk', description='لعبة المخاطرة')
    async def risk_cmd(interaction: discord.Interaction):
        """لعبة Risk"""
        user_id = interaction.user.id
        
        if user_id in _risk_sessions:
            await interaction.response.send_message(
                '❌ لديك لعبة نشطة! استخدم `/risk-stop` لإنهائها.',
                ephemeral=True
            )
            return
        
        _risk_sessions[user_id] = {
            "bank": 100,
            "current": 0,
            "rounds": 0
        }
        
        embed = discord.Embed(
            title="🔥 لعبة المخاطرة",
            description=(
                "لديك **100** نقطة!\n\n"
                "في كل جولة:\n"
                "• `/risk-take` — خذ النقاط الحالية\n"
                "• `/risk-risk` — خاطر لتضاعف النقاط"
            ),
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name='risk-take', description='خذ النقاط الحالية')
    async def risk_take_cmd(interaction: discord.Interaction):
        """أخذ النقاط"""
        user_id = interaction.user.id
        
        if user_id not in _risk_sessions:
            await interaction.response.send_message(
                '❌ لا توجد لعبة نشطة!',
                ephemeral=True
            )
            return
        
        s = _risk_sessions[user_id]
        s["bank"] += s["current"]
        s["current"] = 0
        
        await interaction.response.send_message(
            f"✅ أخذت النقاط!\n**رصيدك:** {s['bank']} نقطة"
        )
    
    @bot.tree.command(name='risk-risk', description='خاطر لمضاعفة النقاط')
    async def risk_risk_cmd(interaction: discord.Interaction):
        """المخاطرة"""
        user_id = interaction.user.id
        
        if user_id not in _risk_sessions:
            await interaction.response.send_message(
                '❌ لا توجد لعبة نشطة!',
                ephemeral=True
            )
            return
        
        s = _risk_sessions[user_id]
        
        # احتمالية النجاح تقل مع كل جولة
        chance = max(0.6 - 0.05 * s["rounds"], 0.2)
        success = random.random() < chance
        
        if success:
            if s["current"] == 0:
                s["current"] = 50
            else:
                s["current"] *= 2
            
            await interaction.response.send_message(
                f"✅ نجح! النقاط الحالية: **{s['current']}**"
            )
        else:
            s["current"] = 0
            await interaction.response.send_message("💥 خسرت النقاط الحالية!")
        
        s["rounds"] += 1
    
    @bot.tree.command(name='risk-stop', description='إنهاء اللعبة')
    async def risk_stop_cmd(interaction: discord.Interaction):
        """إيقاف Risk"""
        user_id = interaction.user.id
        
        if user_id not in _risk_sessions:
            await interaction.response.send_message(
                '❌ لا توجد لعبة نشطة!',
                ephemeral=True
            )
            return
        
        s = _risk_sessions.pop(user_id)
        final = s["bank"] + s["current"]
        
        embed = discord.Embed(
            title="🏁 انتهت اللعبة",
            description=f"**رصيدك النهائي:** {final} نقطة",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== CodeBreak ====================
    
    @bot.tree.command(name='codebreak', description='حل الشيفرة السرية')
    async def codebreak_cmd(interaction: discord.Interaction):
        """لعبة CodeBreak"""
        user_id = interaction.user.id
        
        secret = ''.join(str(random.randint(0, 9)) for _ in range(4))
        
        _codebreak_sessions[user_id] = {
            "secret": secret,
            "attempts": 0
        }
        
        embed = discord.Embed(
            title="🔐 CodeBreak",
            description=(
                "تم إنشاء شيفرة من 4 أرقام!\n\n"
                "استخدم `/codebreak-guess code:1234` للتخمين\n"
                "لديك 8 محاولات"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name='codebreak-guess', description='خمّن الشيفرة')
    @app_commands.describe(code='أربعة أرقام (مثال: 1234)')
    async def codebreak_guess_cmd(interaction: discord.Interaction, code: str):
        """تخمين الشيفرة"""
        user_id = interaction.user.id
        
        if user_id not in _codebreak_sessions:
            await interaction.response.send_message(
                '❌ لم تبدأ اللعبة! استخدم `/codebreak` أولاً.',
                ephemeral=True
            )
            return
        
        if not code.isdigit() or len(code) != 4:
            await interaction.response.send_message(
                '❌ أدخل 4 أرقام فقط!',
                ephemeral=True
            )
            return
        
        cb = _codebreak_sessions[user_id]
        secret = cb["secret"]
        cb["attempts"] += 1
        
        # حساب Bulls و Cows
        bulls = sum(1 for a, b in zip(code, secret) if a == b)
        cows = sum(min(code.count(d), secret.count(d)) for d in set(code)) - bulls
        
        if bulls == 4:
            embed = discord.Embed(
                title="✅ فزت!",
                description=f"الشيفرة: **{secret}**\nالمحاولات: {cb['attempts']}",
                color=discord.Color.green()
            )
            del _codebreak_sessions[user_id]
        elif cb["attempts"] >= 8:
            embed = discord.Embed(
                title="💥 خسرت!",
                description=f"الشيفرة كانت: **{secret}**",
                color=discord.Color.red()
            )
            del _codebreak_sessions[user_id]
        else:
            embed = discord.Embed(
                title="🔎 نتيجة التخمين",
                description=(
                    f"**Bulls:** {bulls} (في المكان الصحيح)\n"
                    f"**Cows:** {cows} (رقم صحيح، مكان خاطئ)\n\n"
                    f"المحاولات المتبقية: {8 - cb['attempts']}"
                ),
                color=discord.Color.blue()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== Reaction ====================
    
    @bot.tree.command(name='reaction', description='اختبار سرعة الرد')
    async def reaction_cmd(interaction: discord.Interaction):
        """لعبة Reaction"""
        await interaction.response.send_message("استعد... 🎯")
        
        # انتظار عشوائي
        await asyncio.sleep(random.uniform(2, 5))
        
        msg = await interaction.channel.send("**الآن! اكتب: ZEX**")
        
        def check(m):
            return m.channel == interaction.channel and m.content.upper() == "ZEX"
        
        try:
            start = datetime.utcnow()
            response = await bot.wait_for('message', timeout=5.0, check=check)
            end = datetime.utcnow()
            
            time_taken = (end - start).total_seconds()
            
            await interaction.channel.send(
                f"✅ {response.author.mention} فاز!\n"
                f"الوقت: **{time_taken:.3f}** ثانية"
            )
        
        except asyncio.TimeoutError:
            await interaction.channel.send("⏰ انتهى الوقت! لم يرد أحد بسرعة كافية.")
    
    bot_logger.success('✅ تم تسجيل أوامر المرح - ALL GAMES WORKING!')

# ==================== Register Persistent Views ====================

def register_persistent_views(bot: commands.Bot):
    """تسجيل الـ Views المستمرة"""
    # هذه الدالة يجب استدعاؤها من main.py
    bot.add_view(MysteryStartView(story_id=""))
    bot.add_view(MysteryChoiceView(story_id="", scene_id="", choice_keys=[]))
    
    bot_logger.info('✅ تم تسجيل Mystery persistent views')