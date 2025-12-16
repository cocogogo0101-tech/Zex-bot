"""
cmd_fun.py - Ultimate Version
==============================
أوامر المرح والترفيه

Features:
✅ Roll - رمي النرد مع خيارات متقدمة
✅ Coinflip - قلب عملة
✅ Choose - اختيار عشوائي
✅ 8ball - الكرة السحرية
✅ Dice - مجموعة نرد (D&D style)
✅ RPS - حجر ورقة مقص
✅ Magic8 - كرة سحرية محسّنة
"""

import discord
from discord import app_commands
from discord.ext import commands
import embeds
from logger import bot_logger
import random
from typing import Optional, Literal
from datetime import datetime


def setup_fun_commands(bot: commands.Bot):
    """تسجيل أوامر المرح"""

    # ==================== Roll (رمي النرد) ====================

    @bot.tree.command(name='roll', description='رمي النرد')
    @app_commands.describe(
        sides='عدد أوجه النرد (2-100)',
        count='عدد مرات الرمي (1-10)'
    )
    async def roll(
        interaction: discord.Interaction,
        sides: int = 6,
        count: int = 1
    ):
        """رمي النرد"""
        try:
            # التحقق من المدخلات
            if sides < 2 or sides > 100:
                await interaction.response.send_message(
                    embed=embeds.error_embed('خطأ', 'عدد الأوجه يجب أن يكون بين 2 و 100'),
                    ephemeral=True
                )
                return

            if count < 1 or count > 10:
                await interaction.response.send_message(
                    embed=embeds.error_embed('خطأ', 'عدد مرات الرمي يجب أن يكون بين 1 و 10'),
                    ephemeral=True
                )
                return

            # رمي النرد
            results = [random.randint(1, sides) for _ in range(count)]
            total = sum(results)

            # إنشاء Embed
            embed = discord.Embed(
                title='🎲 رمي النرد',
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # النتائج
            if count == 1:
                embed.description = f'رميت نردًا من **{sides}** أوجه\n\n🎯 النتيجة: **{results[0]}**'
            else:
                results_str = ' + '.join([f'**{r}**' for r in results])
                embed.description = (
                    f'رميت **{count}** نرد من **{sides}** أوجه\n\n'
                    f'📊 النتائج: {results_str}\n'
                    f'🎯 المجموع: **{total}**'
                )

            # إحصائيات
            if count > 1:
                avg = total / count
                max_val = max(results)
                min_val = min(results)

                embed.add_field(
                    name='📈 الإحصائيات',
                    value=(
                        f'**المتوسط:** {avg:.2f}\n'
                        f'**الأعلى:** {max_val}\n'
                        f'**الأقل:** {min_val}'
                    ),
                    inline=False
                )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'roll (d{sides} x{count})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في roll', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء رمي النرد'),
                ephemeral=True
            )

    # ==================== Coinflip (قلب عملة) ====================

    @bot.tree.command(name='coinflip', description='قلب عملة')
    async def coinflip(interaction: discord.Interaction):
        """قلب عملة"""
        try:
            # قلب العملة
            result = random.choice(['كتابة', 'صورة'])
            emoji = '📜' if result == 'كتابة' else '🖼️'

            # إنشاء Embed
            embed = discord.Embed(
                title='🪙 قلب العملة',
                description=f'## {emoji} **{result}**',
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # رسالة عشوائية
            messages = {
                'كتابة': [
                    'الكتابة تفوز!',
                    'العملة وقعت على الكتابة!',
                    'كتابة! حظك جيد اليوم',
                ],
                'صورة': [
                    'الصورة تفوز!',
                    'العملة وقعت على الصورة!',
                    'صورة! ربما حان وقت اللعب مرة أخرى',
                ]
            }

            embed.add_field(
                name='',
                value=random.choice(messages[result]),
                inline=False
            )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'coinflip ({result})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في coinflip', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء قلب العملة'),
                ephemeral=True
            )

    # ==================== Choose (اختيار) ====================

    @bot.tree.command(name='choose', description='الاختيار بين خيارات متعددة')
    @app_commands.describe(options='الخيارات مفصولة بـ | (مثال: خيار1 | خيار2 | خيار3)')
    async def choose(interaction: discord.Interaction, options: str):
        """اختيار عشوائي"""
        try:
            # تقسيم الخيارات
            choices = [c.strip() for c in options.split('|') if c.strip()]

            if len(choices) < 2:
                await interaction.response.send_message(
                    embed=embeds.error_embed(
                        'خطأ',
                        'أدخل خيارين على الأقل مفصولين بـ |\n**مثال:** `/choose options:خيار1 | خيار2 | خيار3`'
                    ),
                    ephemeral=True
                )
                return

            # الاختيار العشوائي
            selected = random.choice(choices)

            # إنشاء Embed
            embed = discord.Embed(
                title='🤔 الاختيار العشوائي',
                description=f'## ✨ **{selected}**',
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )

            # عرض جميع الخيارات
            all_choices = '\n'.join([f'• {c}' for c in choices])
            embed.add_field(
                name='📋 الخيارات المتاحة',
                value=all_choices,
                inline=False
            )

            # رسالة تحفيزية
            messages = [
                'اخترت لك!',
                'هذا هو الخيار الأفضل!',
                'قرار حكيم!',
                'هذا اختياري لك',
                'الحظ معك!',
            ]

            embed.set_footer(
                text=f'{random.choice(messages)} | {interaction.user.name}'
            )

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'choose ({len(choices)} options)',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في choose', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء الاختيار'),
                ephemeral=True
            )

    # ==================== 8ball (الكرة السحرية) ====================

    @bot.tree.command(name='8ball', description='اسأل الكرة السحرية سؤالاً')
    @app_commands.describe(question='سؤالك')
    async def eightball(interaction: discord.Interaction, question: str):
        """الكرة السحرية"""
        try:
            # الإجابات المحتملة (مقسمة حسب النوع)
            responses = {
                'positive': [
                    '✅ نعم بالتأكيد',
                    '✅ نعم',
                    '✅ بكل تأكيد',
                    '✅ بدون شك',
                    '✅ يمكنك الاعتماد على ذلك',
                    '✅ كما أراه، نعم',
                    '✅ على الأرجح',
                    '✅ النتائج تبدو جيدة',
                    '✅ نعم، بالتأكيد',
                    '✅ الإشارات تشير إلى نعم',
                ],
                'neutral': [
                    '🤔 الرد غامض، حاول مرة أخرى',
                    '🤔 اسأل مرة أخرى لاحقاً',
                    '🤔 من الأفضل ألا أخبرك الآن',
                    '🤔 لا يمكنني التنبؤ الآن',
                    '🤔 ركز واسأل مرة أخرى',
                    '🤔 ليس واضحاً بعد',
                ],
                'negative': [
                    '❌ لا تعتمد على ذلك',
                    '❌ إجابتي هي لا',
                    '❌ مصادري تقول لا',
                    '❌ النتائج لا تبدو جيدة',
                    '❌ مشكوك فيه جداً',
                    '❌ لا',
                    '❌ بالتأكيد لا',
                ],
            }

            # اختيار نوع عشوائي
            response_type = random.choice(['positive'] * 4 + ['neutral'] * 2 + ['negative'] * 4)
            response = random.choice(responses[response_type])

            # تحديد اللون
            colors = {
                'positive': discord.Color.green(),
                'neutral': discord.Color.orange(),
                'negative': discord.Color.red()
            }
            color = colors[response_type]

            # إنشاء Embed
            embed = discord.Embed(
                title='🎱 الكرة السحرية',
                color=color,
                timestamp=datetime.now()
            )

            embed.add_field(
                name='❓ السؤال',
                value=f'*{question}*',
                inline=False
            )

            embed.add_field(
                name='💬 الإجابة',
                value=f'## {response}',
                inline=False
            )

            embed.set_footer(text=f'سأل بواسطة {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                '8ball',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في 8ball', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ في الكرة السحرية'),
                ephemeral=True
            )

    # ==================== Dice (نرد D&D) ====================

    @bot.tree.command(name='dice', description='رمي نرد بصيغة D&D (مثال: 2d6, 3d20)')
    @app_commands.describe(notation='صيغة النرد (مثال: 2d6, 3d20, 1d100)')
    async def dice(interaction: discord.Interaction, notation: str):
        """رمي نرد بصيغة D&D"""
        try:
            # تحليل الصيغة (مثال: 2d6 = رمي نردين من 6 أوجه)
            import re
            match = re.match(r'^(\d+)d(\d+)$', notation.lower().strip())

            if not match:
                await interaction.response.send_message(
                    embed=embeds.error_embed(
                        'خطأ',
                        'صيغة خاطئة! استخدم: `XdY` حيث X = عدد النرد، Y = عدد الأوجه\n'
                        '**أمثلة:** `2d6`, `3d20`, `1d100`'
                    ),
                    ephemeral=True
                )
                return

            count = int(match.group(1))
            sides = int(match.group(2))

            # التحقق من الحدود
            if count < 1 or count > 20:
                await interaction.response.send_message(
                    embed=embeds.error_embed('خطأ', 'عدد النرد يجب أن يكون بين 1 و 20'),
                    ephemeral=True
                )
                return

            if sides < 2 or sides > 100:
                await interaction.response.send_message(
                    embed=embeds.error_embed('خطأ', 'عدد الأوجه يجب أن يكون بين 2 و 100'),
                    ephemeral=True
                )
                return

            # رمي النرد
            results = [random.randint(1, sides) for _ in range(count)]
            total = sum(results)

            # إنشاء Embed
            embed = discord.Embed(
                title=f'🎲 رمي النرد: {notation.upper()}',
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # النتائج
            results_str = ', '.join([f'`{r}`' for r in results])

            embed.add_field(
                name='📊 النتائج',
                value=results_str,
                inline=False
            )

            embed.add_field(
                name='🎯 المجموع',
                value=f'## **{total}**',
                inline=False
            )

            # إحصائيات إضافية
            if count > 1:
                avg = total / count
                embed.add_field(
                    name='📈 الإحصائيات',
                    value=(
                        f'**المتوسط:** {avg:.2f}\n'
                        f'**الأعلى:** {max(results)}\n'
                        f'**الأقل:** {min(results)}'
                    ),
                    inline=False
                )

            embed.set_footer(text=f'مطلوب بواسطة {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'dice ({notation})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في dice', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ أثناء رمي النرد'),
                ephemeral=True
            )

    # ==================== RPS (حجر ورقة مقص) ====================

    @bot.tree.command(name='rps', description='العب حجر ورقة مقص ضد البوت')
    @app_commands.describe(choice='اختيارك')
    @app_commands.choices(choice=[
        app_commands.Choice(name='🪨 حجر', value='rock'),
        app_commands.Choice(name='📄 ورقة', value='paper'),
        app_commands.Choice(name='✂️ مقص', value='scissors')
    ])
    async def rps(interaction: discord.Interaction, choice: str):
        """حجر ورقة مقص"""
        try:
            # خيارات اللعبة
            choices = {
                'rock': {'emoji': '🪨', 'name': 'حجر'},
                'paper': {'emoji': '📄', 'name': 'ورقة'},
                'scissors': {'emoji': '✂️', 'name': 'مقص'}
            }

            # اختيار البوت
            bot_choice = random.choice(['rock', 'paper', 'scissors'])

            # تحديد النتيجة
            results = {
                ('rock', 'scissors'): 'win',
                ('paper', 'rock'): 'win',
                ('scissors', 'paper'): 'win',
                ('rock', 'paper'): 'lose',
                ('paper', 'scissors'): 'lose',
                ('scissors', 'rock'): 'lose',
            }

            if choice == bot_choice:
                result = 'tie'
            else:
                result = results.get((choice, bot_choice), 'lose')

            # تحديد اللون والرسالة
            if result == 'win':
                color = discord.Color.green()
                result_text = '🎉 **فزت!**'
            elif result == 'lose':
                color = discord.Color.red()
                result_text = '😔 **خسرت!**'
            else:
                color = discord.Color.orange()
                result_text = '🤝 **تعادل!**'

            # إنشاء Embed
            embed = discord.Embed(
                title='🎮 حجر ورقة مقص',
                description=result_text,
                color=color,
                timestamp=datetime.now()
            )

            embed.add_field(
                name='اختيارك',
                value=f'{choices[choice]["emoji"]} **{choices[choice]["name"]}**',
                inline=True
            )

            embed.add_field(
                name='اختيار البوت',
                value=f'{choices[bot_choice]["emoji"]} **{choices[bot_choice]["name"]}**',
                inline=True
            )

            # رسالة إضافية
            messages = {
                'win': ['أحسنت!', 'رائع!', 'ممتاز!', 'حظك جيد!'],
                'lose': ['حظ أفضل في المرة القادمة!', 'البوت فاز هذه المرة!', 'قريب جداً!'],
                'tie': ['عقول متشابهة!', 'لنحاول مرة أخرى!', 'تعادل مثير!']
            }

            embed.set_footer(text=f'{random.choice(messages[result])} | {interaction.user.name}')

            await interaction.response.send_message(embed=embed)

            bot_logger.command_executed(
                interaction.user.name,
                f'rps ({choice} vs {bot_choice} = {result})',
                interaction.guild.name if interaction.guild else 'DM'
            )

        except Exception as e:
            bot_logger.exception('خطأ في rps', e)
            await interaction.response.send_message(
                embed=embeds.error_embed('خطأ', 'حدث خطأ في اللعبة'),
                ephemeral=True
            )

    bot_logger.success('تم تسجيل أوامر المرح بنجاح')