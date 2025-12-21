"""
cmd_fun.py - Ultimate Edition
-----------------------------
تنفيذ متكامل لأوامر المرح (Fun) — إصدار "مطلق".
- يقرأ mystery.json المجاور ويشغّل محرك القصص.
- أوامر محسّنة، ألعاب جديدة، واجهة /fun ببانر.
- لا يعتمد DB، كل شيء session-based في الذاكرة.
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

# --- logger (مشابه لما في مشروعك) ---
try:
    from logger import bot_logger
except Exception:
    import logging
    bot_logger = logging.getLogger('cmd_fun')
    if not bot_logger.handlers:
        bot_logger.addHandler(logging.StreamHandler())
    bot_logger.setLevel(logging.INFO)

# --- optional project embeds module (fallback implemented) ---
try:
    import embeds  # مشروعك قد يحتوي على module مخصص للـ embeds
except Exception:
    embeds = None

# -------- Configuration --------
MYSTERY_FILE = os.path.join(os.path.dirname(__file__), 'mystery.json')
FUN_BANNER_URL = "https://cdn.phototourl.com/uploads/2025-12-21-862960d6-ee99-4812-aae7-cca1852d3bfe.gif"

# Session stores (in-memory)
_sessions: Dict[int, Dict[str, Any]] = {}  # user_id -> session data
_mystery_sessions: Dict[int, Dict[str, Any]] = {}  # user_id -> mystery progress
_reaction_games: Dict[str, Dict[str, Any]] = {}  # channel_id -> reaction game
_risk_sessions: Dict[int, Dict[str, Any]] = {}  # user_id -> risk state

# Mystery data loaded from JSON
_mystery_data: Dict[str, Any] = {}

# Lock for concurrency safety on file load
_mystery_lock = asyncio.Lock()

# --- Utility embed helpers (fall back if no embeds module) ---
def _make_embed(title: str = None, description: str = None, color: Optional[discord.Color] = None, footer: Optional[str] = None):
    if color is None:
        color = discord.Color.blurple()
    embed = discord.Embed(title=title or discord.Embed.Empty, description=description or discord.Embed.Empty, color=color, timestamp=datetime.utcnow())
    if footer:
        embed.set_footer(text=footer)
    return embed

def _error_embed(title: str, message: str):
    if embeds and hasattr(embeds, 'error_embed'):
        try:
            return embeds.error_embed(title, message)
        except Exception:
            pass
    return _make_embed(title=title, description=message, color=discord.Color.red())

def _info_embed(title: str, description: str, footer: Optional[str] = None, image: Optional[str] = None):
    if embeds and hasattr(embeds, 'info_embed'):
        try:
            return embeds.info_embed(title, description)
        except Exception:
            pass
    emb = _make_embed(title=title, description=description, color=discord.Color.teal(), footer=footer)
    if image:
        emb.set_image(url=image)
    return emb

# --- Load mystery.json (safe) ---
async def load_mystery_file():
    global _mystery_data
    async with _mystery_lock:
        if _mystery_data:
            return _mystery_data
        if not os.path.exists(MYSTERY_FILE):
            bot_logger.warning(f"mystery file not found at {MYSTERY_FILE}")
            _mystery_data = {"stories": {}}
            return _mystery_data
        try:
            with open(MYSTERY_FILE, 'r', encoding='utf-8') as f:
                _mystery_data = json.load(f)
                bot_logger.info(f"Loaded mystery.json with {len(_mystery_data.get('stories', {}))} stories")
        except Exception as e:
            bot_logger.exception("Failed to load mystery.json", e)
            _mystery_data = {"stories": {}}
    return _mystery_data

# --- Helpers for sessions ---
def get_session(user_id: int) -> Dict[str, Any]:
    if user_id not in _sessions:
        _sessions[user_id] = {"created_at": datetime.utcnow(), "data": {}}
    return _sessions[user_id]["data"]

def get_mystery_session(user_id: int) -> Dict[str, Any]:
    if user_id not in _mystery_sessions:
        _mystery_sessions[user_id] = {"story_id": None, "current": None, "path": [], "started_at": None, "timer_task": None}
    return _mystery_sessions[user_id]

def clear_mystery_session(user_id: int):
    s = _mystery_sessions.get(user_id)
    if s and s.get("timer_task"):
        try:
            s["timer_task"].cancel()
        except Exception:
            pass
    _mystery_sessions.pop(user_id, None)

# --- Utility: pick random text if list provided ---
def choose_text(node_text):
    if isinstance(node_text, list):
        return random.choice(node_text)
    return node_text

# --- Utility: resolve 'next' which might be probabilistic ---
def resolve_next(next_field):
    """
    next_field may be:
    - string: next scene id
    - {"chance": {"a":0.5, "b":0.5}} -> chooses one based on weights
    - nested mapping with chance percentages
    """
    if isinstance(next_field, str):
        return next_field
    if isinstance(next_field, dict) and "chance" in next_field:
        chance_map = next_field["chance"]
        keys = list(chance_map.keys())
        weights = [chance_map[k] for k in keys]
        # normalize
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
    # fallback
    return None

# --- Timer helper for mystery scenes ---
async def _start_scene_timer(interaction: discord.Interaction, user_id: int, seconds: int, timeout_next: Optional[str], story_id: str):
    """
    Waits seconds; if session still at same scene, advance to timeout_next.
    """
    await asyncio.sleep(seconds)
    session = get_mystery_session(user_id)
    # check still active and same story
    if session.get("story_id") != story_id:
        return
    cur = session.get("current")
    # only proceed if still at same scene
    if cur and session.get("wait_for_choice") and session.get("wait_for_choice_scene") == cur:
        # choose the timeout_next
        next_scene = timeout_next
        # apply random chance if defined in scene
        story = (_mystery_data.get("stories") or {}).get(story_id, {})
        scenes = story.get("scenes", {})
        node = scenes.get(cur, {})
        if node and node.get("choices") and timeout_next is None:
            # if none provided, try choose default first choice next
            # but safer to pick random choice
            choices = list(node.get("choices", {}).items())
            if choices:
                _, choice = random.choice(choices)
                next_scene = choice.get("next")
                next_scene = resolve_next(next_scene)
        # simulate choice: move forward automatically
        if next_scene:
            # call engine to advance (we cannot call interaction.response here — instead send a followup message)
            # But we can send a DM or channel message informing user of auto-choice.
            try:
                # send a message in the same channel
                await interaction.channel.send(f"<@{user_id}> لم يتم اختيار ردّ خلال المهلة؛ يتم اختيار مسار تلقائياً...")
            except Exception:
                pass
            # advance by editing session and send next node content
            session["current"] = next_scene
            # remove wait_for_choice
            session["wait_for_choice"] = False
            session["wait_for_choice_scene"] = None
            # send next scene content if possible
            try:
                # find the next node and send its content
                node = scenes.get(next_scene, {})
                if node:
                    text = choose_text(node.get("text", ""))
                    embed = _make_embed(title=f"🔎 {story.get('title', 'قصة')}", description=text)
                    # build choices list
                    choices = node.get("choices", {})
                    if choices:
                        field_value = "\n".join([f"**{k}** — {v.get('label')}" for k, v in choices.items()])
                        embed.add_field(name="❓ الاختيارات", value=field_value, inline=False)
                    elif node.get("ending"):
                        # present ending
                        ending_key = node.get("ending")
                        ending = (story.get("endings") or {}).get(ending_key)
                        if ending:
                            embed = _make_embed(title=f"🏁 {ending.get('title', 'النهاية')}", description=ending.get("text", ""))
                    await interaction.channel.send(embed=embed)
            except Exception:
                pass

# ----------------- Core Mystery Engine -----------------
async def _start_mystery(interaction: discord.Interaction, story_id: str, silent_rules: bool = False):
    """
    Initializes session for user and starts the story at 'start' scene.
    """
    await load_mystery_file()
    user_id = interaction.user.id
    story = _mystery_data.get("stories", {}).get(story_id)
    if not story:
        await interaction.response.send_message(embed=_error_embed("خطأ", "القصة غير موجودة."), ephemeral=True)
        return

    session = get_mystery_session(user_id)
    # reset any previous session
    clear_mystery_session(user_id)
    session = get_mystery_session(user_id)
    session["story_id"] = story_id
    session["started_at"] = datetime.utcnow()
    session["path"] = []
    session["current"] = story.get("start")
    session["wait_for_choice"] = False
    session["wait_for_choice_scene"] = None

    # show rules first (unless silent)
    if not silent_rules:
        rules = story.get("rules", [])
        desc = "\n".join([f"• {r}" for r in rules]) if rules else "لا قواعد محددة للقصة."
        emb = _info_embed(title=f"📜 {story.get('title', 'قصة تفاعلية')}", description=desc, image=FUN_BANNER_URL)
        emb.set_footer(text="اضغط على أي رد عبر الأزرار لاختيارك. لديك وقت محدود لبعض المشاهد.")
        # send ephemeral reply with rules and start button
        view = MysteryStartView(story_id)
        await interaction.response.send_message(embed=emb, view=view, ephemeral=True)
        return
    else:
        # silent start: directly send first scene
        await _send_current_scene(interaction, user_id)

async def _send_current_scene(interaction: discord.Interaction, user_id: int, public: bool = True):
    """
    Sends current scene as a message in the interaction's channel (public) or as ephemeral followup.
    """
    session = get_mystery_session(user_id)
    story_id = session.get("story_id")
    if not story_id:
        return
    story = _mystery_data.get("stories", {}).get(story_id, {})
    scenes = story.get("scenes", {})
    cur = session.get("current")
    if not cur:
        return
    node = scenes.get(cur)
    if not node:
        return
    text = choose_text(node.get("text", ""))
    emb = _make_embed(title=f"🔎 {story.get('title', '')}", description=text, color=discord.Color.dark_magenta())
    # choices
    choices = node.get("choices", {})
    if choices:
        field_value = "\n".join([f"**{k}** — {v.get('label')}" for k, v in choices.items()])
        emb.add_field(name="❓ الاختيارات", value=field_value, inline=False)
    elif node.get("ending"):
        ending_key = node.get("ending")
        ending = (story.get("endings") or {}).get(ending_key)
        if ending:
            emb = _make_embed(title=f"🏁 {ending.get('title', 'النهاية')}", description=ending.get("text", ""))
    # send as normal message (non-ephemeral) so it's visible in channel
    try:
        # Using followup if interaction.response already done
        if interaction.response.is_done():
            await interaction.followup.send(embed=emb)
        else:
            await interaction.response.send_message(embed=emb)
    except Exception:
        try:
            await interaction.channel.send(embed=emb)
        except Exception:
            pass

    # if node has a timer, start it
    timer = node.get("timer")
    timeout_next = node.get("timeout_next")
    if timer:
        # create background task to advance after timer seconds
        # store marker to ensure it's still valid
        session["wait_for_choice"] = True
        session["wait_for_choice_scene"] = cur
        story_id_local = story_id
        # create task attached to session
        async def timer_task():
            await _start_scene_timer(interaction, user_id, int(timer), timeout_next, story_id_local)
        t = asyncio.create_task(timer_task())
        session["timer_task"] = t

# View for starting mystery
class MysteryStartView(discord.ui.View):
    def __init__(self, story_id: str):
        super().__init__(timeout=120)
        self.story_id = story_id

    @discord.ui.button(label='▶ ابدأ القصة', style=discord.ButtonStyle.primary, custom_id='mystery_start')
    async def start_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # start silently (skip rules display)
        await _start_mystery(interaction, self.story_id, silent_rules=True)
        # send the first scene content publicly
        await _send_current_scene(interaction, interaction.user.id)

# View for presenting choices as buttons (dynamic)
class MysteryChoiceView(discord.ui.View):
    def __init__(self, story_id: str, scene_id: str):
        super().__init__(timeout=60)
        self.story_id = story_id
        self.scene_id = scene_id
        # dynamically add buttons based on scene
        story = _mystery_data.get("stories", {}).get(story_id, {})
        scene = (story.get("scenes") or {}).get(scene_id, {})
        choices = scene.get("choices", {}) if scene else {}
        # limit buttons to 5 for neatness
        added = 0
        for key, info in choices.items():
            if added >= 5:
                break
            label = f"{key} — {info.get('label')}"
            btn = discord.ui.Button(label=label[:80], style=discord.ButtonStyle.secondary, custom_id=f"mchoice_{key}")
            async def _callback(interaction: discord.Interaction, key=key):
                await interaction.response.defer(thinking=True)
                await process_mystery_choice(interaction, interaction.user.id, self.story_id, self.scene_id, key)
            btn.callback = _callback
            self.add_item(btn)
            added += 1

# Process a choice clicked
async def process_mystery_choice(interaction: discord.Interaction, user_id: int, story_id: str, scene_id: str, choice_key: str):
    story = _mystery_data.get("stories", {}).get(story_id, {})
    scenes = story.get("scenes", {})
    node = scenes.get(scene_id, {})
    choice = (node.get("choices") or {}).get(choice_key)
    if not choice:
        await interaction.followup.send(embed=_error_embed("خطأ", "خيار غير صالح"), ephemeral=True)
        return
    next_field = choice.get("next")
    next_scene = resolve_next(next_field)
    # update session
    session = get_mystery_session(user_id)
    session["path"].append({"scene": scene_id, "choice": choice_key})
    session["current"] = next_scene
    session["wait_for_choice"] = False
    session["wait_for_choice_scene"] = None
    # send next
    await _send_current_scene(interaction, user_id)

# ----------------- Fun Commands Setup -----------------
def setup_fun_commands(bot: commands.Bot):
    """
    Register all fun commands to bot.tree
    """
    # ensure mystery file is loaded at startup
    bot.loop.create_task(load_mystery_file())

    # ---------- /fun menu ----------
    @bot.tree.command(name='fun', description='عرض ألعاب المرح المتاحة')
    async def fun_menu(interaction: discord.Interaction):
        await load_mystery_file()
        stories = _mystery_data.get("stories", {})
        # build embed
        desc = "قائمة ألعاب المرح المتوفرة حالياً. اختر أحد الأوامر لتبدأ اللعبة.\n\n"
        categories = {
            "التفاعلية": ["mystery", "reaction", "codebreak", "risk"],
            "العقلية": ["iq", "mindtrap"],
            "الألعاب الكلاسيكية": ["roll", "dice", "coinflip", "rps", "8ball"]
        }
        for cat, cmds in categories.items():
            desc += f"**{cat}** — " + ", ".join([f'`/{c}`' for c in cmds]) + "\n"
        emb = _make_embed(title="🎮 ZEX // FUN MENU", description=desc, color=discord.Color.blurple())
        emb.set_image(url=FUN_BANNER_URL)
        emb.set_footer(text=f"قصص متاحة: {len(stories)}")
        await interaction.response.send_message(embed=emb)

    # ---------- /mystery ----------
    @bot.tree.command(name='mystery', description='ابدأ قصة تفاعلية عشوائية من مجموعة القصص')
    @app_commands.describe(story='معرف القصة (اختياري) أو اتركها فارغة لاختيار عشوائي')
    async def mystery_cmd(interaction: discord.Interaction, story: Optional[str] = None):
        await load_mystery_file()
        stories = _mystery_data.get("stories", {})
        if not stories:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا توجد قصص مُحمّلة."), ephemeral=True)
            return
        if story:
            if story not in stories:
                await interaction.response.send_message(embed=_error_embed("خطأ", "القصة غير موجودة."), ephemeral=True)
                return
            chosen = story
        else:
            chosen = random.choice(list(stories.keys()))
        # start story with rules shown
        await _start_mystery(interaction, chosen, silent_rules=False)

    # ---------- /mystery-choose (start without rules) ----------
    @bot.tree.command(name='mystery-start', description='ابدأ قصة بسرعة (تخطى عرض القواعد)')
    @app_commands.describe(story='معرف القصة (اختياري)')
    async def mystery_start(interaction: discord.Interaction, story: Optional[str] = None):
        await load_mystery_file()
        stories = _mystery_data.get("stories", {})
        if not stories:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا توجد قصص مُحمّلة."), ephemeral=True)
            return
        if story and story in stories:
            chosen = story
        else:
            chosen = random.choice(list(stories.keys()))
        # start silently
        await _start_mystery(interaction, chosen, silent_rules=True)
        # send first scene publicly
        await _send_current_scene(interaction, interaction.user.id)

    # ---------- /roll (enhanced) ----------
    @bot.tree.command(name='roll', description='رمي نرد ذكي (مثال: 1d6 أو sides=count)')
    @app_commands.describe(sides='أوجه النرد (2-100)', count='عدد مرات الرمي (1-20)')
    async def roll_cmd(interaction: discord.Interaction, sides: int = 6, count: int = 1):
        try:
            if sides < 2 or sides > 100:
                await interaction.response.send_message(embed=_error_embed("خطأ", "عدد الأوجه يجب أن يكون بين 2 و 100"), ephemeral=True)
                return
            if count < 1 or count > 20:
                await interaction.response.send_message(embed=_error_embed("خطأ", "عدد مرات الرمي يجب أن يكون بين 1 و 20"), ephemeral=True)
                return
            results = [random.randint(1, sides) for _ in range(count)]
            total = sum(results)
            # rare events
            rare_msg = None
            if any(r == sides for r in results) and random.random() < 0.02:
                rare_msg = "✨ رول مثالي! الحظ في صفك!"
            if any(r == 1 for r in results) and random.random() < 0.02:
                rare_msg = "☠️ لعنة! ظهر الرقم الأدنى... ما الذي حدث؟"
            emb = _make_embed(title="🎲 رمي النرد", description=f"نتائج: {' + '.join([str(r) for r in results])}\nالمجموع: **{total}**", color=discord.Color.blue())
            if rare_msg:
                emb.add_field(name="حدث نادر", value=rare_msg, inline=False)
            # stats
            if count > 1:
                avg = total / count
                emb.add_field(name="📈 إحصائيات", value=f"المتوسط: {avg:.2f}\nالأعلى: {max(results)}\nالأقل: {min(results)}", inline=False)
            emb.set_footer(text=f"مطلوب بواسطة {interaction.user.display_name}")
            await interaction.response.send_message(embed=emb)
            bot_logger.info(f"roll used by {interaction.user}")
        except Exception as e:
            bot_logger.exception("roll error", e)
            await interaction.response.send_message(embed=_error_embed("خطأ", "حدث خطأ أثناء رمي النرد"), ephemeral=True)

    # ---------- /coinflip (streak) ----------
    @bot.tree.command(name='coinflip', description='قلب عملة ذكي (يتبع streak داخل الجلسة)')
    async def coinflip_cmd(interaction: discord.Interaction):
        uid = interaction.user.id
        sess = get_session(uid)
        streak = sess.get("coin_streak", {"face": None, "count": 0})
        result = random.choice(["وجه", "كتابة"])
        if streak["face"] == result:
            streak["count"] += 1
        else:
            streak["face"] = result
            streak["count"] = 1
        sess["coin_streak"] = streak
        messages = {
            "وجه": ["الوجه يفوز!", "وجه! واصل التحدي.", "الوجه ينتصر!"],
            "كتابة": ["الكتابة تفوز!", "كتابة! حان دورك.", "الكتابة تفوز..."]
        }
        emb = _make_embed(title="🪙 قلب العملة", description=f"النتيجة: **{result}**\nStreak: {streak['count']} مرات متتالية", color=discord.Color.gold())
        emb.add_field(name="", value=random.choice(messages[result]), inline=False)
        await interaction.response.send_message(embed=emb)
        bot_logger.info(f"coinflip by {interaction.user}")

    # ---------- /rps (enhanced) ----------
    @bot.tree.command(name='rps', description='حجر ورقة مقص ذكي')
    @app_commands.describe(choice='اختيارك')
    @app_commands.choices(choice=[
        app_commands.Choice(name='🪨 حجر', value='rock'),
        app_commands.Choice(name='📄 ورقة', value='paper'),
        app_commands.Choice(name='✂️ مقص', value='scissors')
    ])
    async def rps_cmd(interaction: discord.Interaction, choice: str):
        uid = interaction.user.id
        sess = get_session(uid)
        last = sess.get("rps_last")
        # bot choice
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        if choice == bot_choice:
            result = 'tie'
        else:
            wins = {('rock', 'scissors'), ('paper', 'rock'), ('scissors', 'paper')}
            if (choice, bot_choice) in wins:
                result = 'win'
            else:
                result = 'lose'
        # analysis: track user's tendency
        tendencies = sess.get("rps_tendencies", {"rock":0, "paper":0, "scissors":0})
        tendencies[choice] = tendencies.get(choice, 0) + 1
        sess["rps_tendencies"] = tendencies
        sess["rps_last"] = choice
        # flavor
        messages = {
            "win": ["🎉 ممتاز!", "أحسنت!", "انتصار جميل!"],
            "lose": ["😔 حظ أوفر!", "قريب جدا!", "الأمر كان لصالح البوت هذه المرة."],
            "tie": ["🤝 تعادل!", "أذكياء!", "تعادل ممتع!"]
        }
        emb = _make_embed(title="🎮 حجر ورقة مقص", description=random.choice(messages[result]), color=(discord.Color.green() if result == 'win' else discord.Color.red() if result == 'lose' else discord.Color.orange()))
        choices_map = {'rock':'🪨 حجر','paper':'📄 ورقة','scissors':'✂️ مقص'}
        emb.add_field(name='اختيارك', value=choices_map[choice], inline=True)
        emb.add_field(name='اختيار البوت', value=choices_map[bot_choice], inline=True)
        emb.set_footer(text=f"نتيجة: {result} | لعبت آخر مرة: {last or 'لا يوجد'}")
        await interaction.response.send_message(embed=emb)

    # ---------- /8ball (improved) ----------
    @bot.tree.command(name='8ball', description='الكرة السحرية بنكهة زيكس')
    @app_commands.describe(question='اسأل سؤالاً')
    async def eightball_cmd(interaction: discord.Interaction, question: str):
        # categories with weights for flavor
        responses = {
            'positive': [
                '✅ نعم بالتأكيد',
                '✅ نعم',
                '✅ على الأرجح'
            ],
            'neutral': [
                '🤔 من الأفضل أن تنتظر',
                '🤔 الإجابة غير واضحة'
            ],
            'negative': [
                '❌ لا',
                '❌ غير مرجّح'
            ],
            'weird': [
                '... ??? ...',
                '🔮 الإشارات ضبابية'
            ]
        }
        # weighted selection: more neutral/positive, with rare weird
        types = ['positive']*4 + ['neutral']*3 + ['negative']*3 + ['weird']*1
        t = random.choice(types)
        ans = random.choice(responses[t])
        # glitch rare
        if random.random() < 0.01:
            ans = '⚠️ GLITCH: النتائج غير متاحة الآن...'
        emb = _make_embed(title="🎱 الكرة السحرية", description=f"*{question}*\n\n**{ans}**", color=discord.Color.from_rgb(128,0,128))
        await interaction.response.send_message(embed=emb)

    # ---------- /dice ----------
    @bot.tree.command(name='dice', description='رمي نرد بصيغة D&D (مثال: 2d6)')
    @app_commands.describe(notation='مثال: 2d6 أو 1d20')
    async def dice_cmd(interaction: discord.Interaction, notation: str):
        import re
        m = re.match(r'^(\d+)d(\d+)$', notation.lower().strip())
        if not m:
            await interaction.response.send_message(embed=_error_embed("خطأ", "صيغة خاطئة. مثال: `2d6`"), ephemeral=True)
            return
        count = int(m.group(1)); sides = int(m.group(2))
        if count < 1 or count > 50 or sides < 2 or sides > 1000:
            await interaction.response.send_message(embed=_error_embed("خطأ", "حدود غير مسموح بها"), ephemeral=True)
            return
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        emb = _make_embed(title=f"🎲 {notation.upper()}", description=f"نتائج: {', '.join(map(str, rolls))}\nالمجموع: **{total}**", color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb)

    # ---------- /iq (mini test) ----------
    @bot.tree.command(name='iq', description='اختبار سريع: 5 أسئلة منطقية — تحليل سريع')
    async def iq_cmd(interaction: discord.Interaction):
        uid = interaction.user.id
        # simple question bank (expandable)
        bank = [
            {"q":"ما هو الشكل التالي في المتسلسلة: 2,4,8,16,؟", "choices":{"A":"24","B":"32","C":"18"}, "answer":"B", "explain":"تضاعف كل مرة."},
            {"q":"إذا كان كل A هو B، وكل B هو C، فهل كل A هو C؟", "choices":{"A":"نعم","B":"لا","C":"غير معروف"}, "answer":"A", "explain":"العلاقة انتقالية."},
            {"q":"أي كلمة لا تنتمي للمجموعة: تفاحة، موز، طماطم، برتقال؟", "choices":{"A":"طماطم","B":"موز","C":"برتقال"}, "answer":"A", "explain":"طماطم فاكهة طبية (أشباه الخضروات) — لكن هذا للنقاش."},
            {"q":"اكمل النمط: AB, BC, CD, ?", "choices":{"A":"DE","B":"EF","C":"DA"}, "answer":"A", "explain":"تحريك كل حرف بمقدار 1."},
            {"q":"أي رقم لا ينتمي: 2,3,5,7,9?", "choices":{"A":"9","B":"7","C":"5"}, "answer":"A", "explain":"9 ليس عددًا أوليًا."}
        ]
        # pick 5 random (or fewer if short bank)
        questions = random.sample(bank, k=min(5, len(bank)))
        # store in session
        sess = get_session(uid)
        sess["iq_test"] = {"questions": questions, "current": 0, "score": 0, "start": datetime.utcnow()}
        # send first question via modal-like ephemeral flow: we'll send as ephemeral message listing choices and instruct to use /iq-answer command
        q0 = questions[0]
        desc = f"{q0['q']}\n\n" + "\n".join([f"**{k}** — {v}" for k,v in q0['choices'].items()])
        emb = _make_embed(title="🧠 IQ Test — سؤال 1", description=desc)
        emb.set_footer(text="استخدم الأمر /iq-answer <A|B|C> للإجابة. لديك 20 ثانية لكل سؤال (غير مفروض).")
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @bot.tree.command(name='iq-answer', description='أجب على سؤال IQ (مثال: /iq-answer answer:A)')
    @app_commands.describe(answer='A أو B أو C')
    async def iq_answer(interaction: discord.Interaction, answer: str):
        uid = interaction.user.id
        sess = get_session(uid)
        test = sess.get("iq_test")
        if not test:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا يوجد اختبار جاري."), ephemeral=True)
            return
        cur_idx = test["current"]
        question = test["questions"][cur_idx]
        chosen = answer.strip().upper()
        correct = question.get("answer")
        reacted = False
        if chosen == correct:
            test["score"] += 1
            reacted = True
        test["current"] += 1
        # feedback
        text = "✅ إجابة صحيحة!" if reacted else f"❌ إجابة خاطئة! الإجابة الصحيحة: **{correct}**"
        # explanation
        text += f"\n\nتوضيح: {question.get('explain','')}"
        if test["current"] < len(test["questions"]):
            next_q = test["questions"][test["current"]]
            desc = f"{next_q['q']}\n\n" + "\n".join([f"**{k}** — {v}" for k,v in next_q['choices'].items()])
            emb = _make_embed(title=f"🧠 IQ Test — سؤال {test['current']+1}", description=text + "\n\nالتالي:\n" + desc)
            await interaction.response.send_message(embed=emb, ephemeral=True)
        else:
            # finished
            score = test["score"]
            total = len(test["questions"])
            # classification
            if score == total:
                classification = "تحليلي ممتاز"
            elif score >= total*0.7:
                classification = "تفكير جيد"
            elif score >= total*0.4:
                classification = "متوسط"
            else:
                classification = "تحتاج تدريب"
            emb = _make_embed(title="🧠 IQ Test — النتيجة", description=f"حصلت على **{score}/{total}**\nالتصنيف: **{classification}**")
            await interaction.response.send_message(embed=emb, ephemeral=True)
            # clear test
            sess.pop("iq_test", None)

    # ---------- /risk (munchkin style) ----------
    @bot.tree.command(name='risk', description='لعبة مخاطرة: اكسب نقاطًا أو تخسر كل شيء')
    async def risk_cmd(interaction: discord.Interaction):
        uid = interaction.user.id
        if uid in _risk_sessions:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لديك جلسة مخاطرة قائمة. استخدم /risk-stop أو أكمل."), ephemeral=True)
            return
        # initialize
        session = {"bank": 100, "current": 0, "rounds": 0}
        _risk_sessions[uid] = session
        emb = _make_embed(title="🔥 Risk — بدأت اللعبة", description="لديك 100 نقطة. في كل جولة تختار: `take` (تحصل على الجائزة الحالية) أو `risk` (تخاطر لتضاعف) . اكتب /risk-take أو /risk-risk", color=discord.Color.orange())
        await interaction.response.send_message(embed=emb)
        bot_logger.info(f"risk started by {interaction.user}")

    @bot.tree.command(name='risk-take', description='خُذ الجائزة الحالية في لعبة Risk')
    async def risk_take(interaction: discord.Interaction):
        uid = interaction.user.id
        s = _risk_sessions.get(uid)
        if not s:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا توجد جلسة مخاطرة جارية."), ephemeral=True)
            return
        # award current to bank and end round
        s["bank"] += s["current"]
        s["current"] = 0
        s["rounds"] += 1
        await interaction.response.send_message(embed=_make_embed(title="🎯 أخذت الجائزة", description=f"رصيدك الآن: {s['bank']} نقطة"))
        bot_logger.info(f"risk take by {interaction.user} new bank {s['bank']}")

    @bot.tree.command(name='risk-risk', description='اخاطر لتضاعف الجائزة (أو تخسرها)')
    async def risk_risk(interaction: discord.Interaction):
        uid = interaction.user.id
        s = _risk_sessions.get(uid)
        if not s:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا توجد جلسة مخاطرة جارية."), ephemeral=True)
            return
        # generate event: doubling chance decreases each round
        base_chance = max(0.6 - 0.05 * s["rounds"], 0.2)
        outcome = random.random() < base_chance
        if outcome:
            # success: double current (or set to 50 if first)
            if s["current"] == 0:
                s["current"] = 50
            else:
                s["current"] *= 2
            await interaction.response.send_message(embed=_make_embed(title="✅ نجاح!", description=f"الجائزة الحالية تضاعفت لتصبح {s['current']} نقطة"))
        else:
            # fail: lose current
            s["current"] = 0
            await interaction.response.send_message(embed=_make_embed(title="💥 خسارة!", description="خسرت الجائزة الحالية!"))
        bot_logger.info(f"risk action by {interaction.user} current {s['current']} bank {s['bank']}")

    @bot.tree.command(name='risk-stop', description='إنهاء جلسة Risk وإضافة الرصيد المؤمّن')
    async def risk_stop(interaction: discord.Interaction):
        uid = interaction.user.id
        s = _risk_sessions.pop(uid, None)
        if not s:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لا توجد جلسة مخاطرة جارية."), ephemeral=True)
            return
        final = s["bank"] + s["current"]
        await interaction.response.send_message(embed=_make_embed(title="🏁 انتهت جلسة Risk", description=f"رصيدك النهائي: {final} نقطة"))
        bot_logger.info(f"risk stopped by {interaction.user} final {final}")

    # ---------- /reaction (fast reflex) ----------
    @bot.tree.command(name='reaction', description='اختبر رد فعلك (القناة تستعمل مسابقات تفاعلية)')
    @app_commands.describe(duration='عدد الفائزين المطلوب (1 = الأول فقط)')
    async def reaction_cmd(interaction: discord.Interaction, duration: int = 1):
        channel_id = str(interaction.channel_id)
        if channel_id in _reaction_games:
            await interaction.response.send_message(embed=_error_embed("خطأ", "هناك لعبة تفاعل قائمة في هذه القناة."), ephemeral=True)
            return
        await interaction.response.defer()
        # announce
        announce = await interaction.followup.send("استعد... سيتم الانطلاق بعد لحظة...")
        # delay random between 2 and 6 seconds
        wait = random.uniform(2, 6)
        await asyncio.sleep(wait)
        # send NOW message
        msg = await interaction.channel.send("NOW! اكتب الكلمة: **ZEX** بسرعة!")
        _reaction_games[channel_id] = {"winner_count": duration, "winners": [], "message_id": str(msg.id)}
        # add a collector: we'll listen for messages for 5 seconds
        def check(m):
            return m.channel.id == interaction.channel_id and m.content.strip().upper() == "ZEX"
        try:
            winners = []
            timeout = 5
            start = datetime.utcnow()
            while len(winners) < duration:
                try:
                    m = await interaction.client.wait_for('message', timeout=timeout, check=check)
                except asyncio.TimeoutError:
                    break
                if m.author.id in [w['id'] for w in winners]:
                    continue
                winners.append({"id": m.author.id, "name": m.author.display_name})
                timeout = max(0.5, 5 - (datetime.utcnow() - start).total_seconds())
            if winners:
                names = ", ".join([w["name"] for w in winners])
                await interaction.channel.send(f"🟢 الفائزون: {names}")
            else:
                await interaction.channel.send("لم يسبق أحد بالسرعة الكافية، حاول مرة أخرى.")
        finally:
            _reaction_games.pop(channel_id, None)

    # ---------- /codebreak (Mastermind-lite) ----------
    @bot.tree.command(name='codebreak', description='حل الشيفرة: خمن رمزًا مكوّنًا من 4 أرقام (0-9)')
    async def codebreak_cmd(interaction: discord.Interaction):
        uid = interaction.user.id
        sess = get_session(uid)
        # generate secret code
        secret = ''.join(str(random.randint(0, 9)) for _ in range(4))
        sess["codebreak"] = {"secret": secret, "attempts": 0, "start": datetime.utcnow()}
        emb = _make_embed(title="🔐 CodeBreak", description="لقد تم إنشاء الشيفرة! استخدم `/codebreak-guess code:1234` لمحاولة التخمين. لديك 8 محاولات.")
        await interaction.response.send_message(embed=emb)

    @bot.tree.command(name='codebreak-guess', description='خمن الشيفرة (مثال: /codebreak-guess code:1234)')
    @app_commands.describe(code='أربعة أرقام مثل 1234')
    async def codebreak_guess(interaction: discord.Interaction, code: str):
        uid = interaction.user.id
        sess = get_session(uid)
        cb = sess.get("codebreak")
        if not cb:
            await interaction.response.send_message(embed=_error_embed("خطأ", "لم تبدأ لعبة الشيفرة. استخدم /codebreak أولاً."), ephemeral=True)
            return
        if not code.isdigit() or len(code) != 4:
            await interaction.response.send_message(embed=_error_embed("خطأ", "أدخل 4 أرقام فقط."), ephemeral=True)
            return
        cb["attempts"] += 1
        secret = cb["secret"]
        # evaluate: bulls (correct place), cows (correct digit wrong place)
        bulls = sum(1 for a, b in zip(code, secret) if a == b)
        cows = sum(min(code.count(d), secret.count(d)) for d in set(code)) - bulls
        if bulls == 4:
            await interaction.response.send_message(embed=_make_embed(title="✅ فزت!", description=f"صحيح! الشيفرة: {secret} | محاولات: {cb['attempts']}"))
            sess.pop("codebreak", None)
            return
        if cb["attempts"] >= 8:
            await interaction.response.send_message(embed=_make_embed(title="💥 خسرت!", description=f"انتهت محاولاتك. الشيفرة كانت: {secret}"))
            sess.pop("codebreak", None)
            return
        await interaction.response.send_message(embed=_make_embed(title="🔎 نتيجة التخمين", description=f"Bulls: {bulls} | Cows: {cows} | محاولات متبقية: {8 - cb['attempts']}"))
        return

    bot_logger.success("✅ Registered ultimate fun commands")

# End of setup_fun_commands