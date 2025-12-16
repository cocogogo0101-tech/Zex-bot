async def kick_member(interaction, user, reason=None):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message('ما عندك صلاحية.', ephemeral=True)
    member = interaction.guild.get_member(user.id)
    if not member:
        return await interaction.response.send_message('ما لقيت العضو.', ephemeral=True)
    try:
        await member.kick(reason=reason)
        return await interaction.response.send_message(f'✅ تم طرد {user} — {reason or "لا يوجد سبب"}')
    except Exception:
        return await interaction.response.send_message('حصل خطأ أثناء الطرد.', ephemeral=True)

async def ban_member(interaction, user, reason=None):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message('ما عندك صلاحية.', ephemeral=True)
    try:
        await interaction.guild.ban(user, reason=reason)
        return await interaction.response.send_message(f'✅ تم حظر {user} — {reason or "لا يوجد سبب"}')
    except Exception:
        return await interaction.response.send_message('حصل خطأ أثناء الحظر.', ephemeral=True)

async def purge_messages(interaction, count: int):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message('ما عندك صلاحية.', ephemeral=True)
    if count <= 0:
        return await interaction.response.send_message('العدد لازم يكون أكبر من 0.', ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=min(count, 100))
        return await interaction.response.send_message(f'✅ تم مسح {len(deleted)} رسالة.', ephemeral=True)
    except Exception:
        return await interaction.response.send_message('فشل المسح.', ephemeral=True)
