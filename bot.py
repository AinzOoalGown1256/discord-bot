import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ChannelType, ButtonStyle, PermissionOverwrite, ChannelType, PartialEmoji
import os
from dotenv import load_dotenv
import asyncio
from nextcord.ui import View, Button
import yt_dlp
from nextcord import FFmpegPCMAudio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

generator_channel_id = None

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
music_queues = {}

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.slash_command(name="setup", description="Panel de configuración del bot")
async def setup(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No tienes permisos.", ephemeral=True)
        return
    mensaje = (
        "**📋 Comandos disponibles:**\n"
        "/yp generador <canal> – Asigna o actualiza el canal generador de salas temporales.\n\n"
        "🔧 Cuando un usuario se una al canal generador, se crea una sala temporal."
    )
    await interaction.response.send_message(mensaje, ephemeral=True)

@bot.slash_command(name="yp", description="Comandos para gestiónar")
async def yp(interaction: Interaction):
    await interaction.response.send_message(
        "Usa los subcomandos:\n"
        "/yp generador <canal> - Asigna el canal generador",
        ephemeral=True
    )

@yp.subcommand(name="rango", description="Panel de selección de rango de Dota 2")
async def rango(interaction: Interaction):
    ranks = {
        "MedallaHeraldo": PartialEmoji(name="MedallaHeraldo", id=1389344036980265101),
        "MedallaGuardian": PartialEmoji(name="MedallaGuardian", id=1389344040150892674),
        "MedallaCruzado": PartialEmoji(name="MedallaCruzado", id=1389344044089348096),
        "MedallaArconte": PartialEmoji(name="MedallaArconte", id=1389344046261993632),
        "MedallaLeyenda": PartialEmoji(name="MedallaLeyenda", id=1389344030793400451),
        "MedallaAncestro": PartialEmoji(name="MedallaAncestro", id=1389344027815579698),
        "MedallaDivino": PartialEmoji(name="MedallaDivino", id=1389344042076213258),
        "MedallaInmortal": PartialEmoji(name="MedallaInmortal", id=1389344033784201356)
    }
    view = View(timeout=None)
    items = list(ranks.items())
    for i in range(len(items)):
        nombre, emoji = items[i]
        async def make_callback(role_name):
            async def callback(interaction_btn: Interaction):
                member = interaction_btn.user
                guild = interaction_btn.guild
                for r in ranks:
                    old = nextcord.utils.get(guild.roles, name=r)
                    if old in member.roles:
                        await member.remove_roles(old)
                role = nextcord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.add_roles(role)
                await interaction_btn.response.defer()
            return callback
        button = Button(label=nombre, emoji=emoji, style=ButtonStyle.primary, row=i // 2)
        button.callback = await make_callback(nombre)
        view.add_item(button)
    await interaction.response.send_message("Selecciona tu rango:", view=view, ephemeral=False)

@yp.subcommand(name="generador", description="Asignar o actualizar canal generador")
async def yp_generador(
    interaction: Interaction,
    generator: nextcord.VoiceChannel = SlashOption(
        name="generator",
        description="Selecciona un canal de voz generador",
        channel_types=[ChannelType.voice]
    )
):
    global generator_channel_id
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No tienes permisos.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    nuevo_id = generator.id
    old_id = generator_channel_id
    generator_channel_id = nuevo_id

    if old_id and old_id != nuevo_id:
        mensaje = f"Se ha actualizado el canal generador: <#{old_id}> ➔ <#{nuevo_id}>"
    else:
        mensaje = f"Canal generador asignado: <#{nuevo_id}>"

    await interaction.followup.send(mensaje, ephemeral=True)

@yp.subcommand(name="musica", description="Reproduce música como un bot de música")
async def musica(
    interaction: Interaction,
    nombre: str = SlashOption(
        name="nombre",
        description="Nombre de canción o URL de YouTube",
        required=True
    )
):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Debes estar en un canal de voz.", ephemeral=True)
        return

    canal = interaction.user.voice.channel

    if interaction.guild.voice_client:
        vc = interaction.guild.voice_client
        if vc.channel != canal:
            await vc.move_to(canal)
    else:
        vc = await canal.connect()

    await interaction.response.defer()

    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(nombre, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        stream_url = info['url']
        title = info.get('title', 'Sin título')

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    vc.stop()
    vc.play(FFmpegPCMAudio(stream_url, **ffmpeg_options))

    await interaction.followup.send(f"🎵 Reproduciendo: **{title}**")

async def play_next(ctx, guild_id):
    if music_queues[guild_id]:
        url, title = music_queues[guild_id].pop(0)
        vc = ctx.guild.voice_client
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        vc.play(FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop))
        await ctx.channel.send(f"🎵 Reproduciendo: **{title}**")
    else:
        await ctx.guild.voice_client.disconnect()

@yp.subcommand(name="add", description="Agregar canción a la cola")
async def add(
    interaction: Interaction,
    nombre: str = SlashOption(
        name="nombre",
        description="Nombre o URL de canción",
        required=True
    )
):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Debes estar en un canal de voz.", ephemeral=True)
        return

    canal = interaction.user.voice.channel
    guild_id = interaction.guild.id

    await interaction.response.defer()

    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(nombre, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        url = info['url']
        title = info.get('title', 'Sin título')

    if guild_id not in music_queues:
        music_queues[guild_id] = []

    music_queues[guild_id].append((url, title))

    if not interaction.guild.voice_client:
        vc = await canal.connect()
        await play_next(interaction, guild_id)
    elif not interaction.guild.voice_client.is_playing():
        await play_next(interaction, guild_id)
    else:
        await interaction.followup.send(f"🎶 Agregado a la cola: **{title}**")

@yp.subcommand(name="skip", description="Saltar canción actual")
async def skip(interaction: Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Saltando...")
    else:
        await interaction.response.send_message("No hay música reproduciéndose.", ephemeral=True)

@yp.subcommand(name="cola", description="Mostrar canciones en la cola")
async def cola(interaction: Interaction):
    guild_id = interaction.guild.id

    if guild_id not in music_queues or not music_queues[guild_id]:
        await interaction.response.send_message("🎶 La cola está vacía.", ephemeral=True)
        return

    lista = ""
    for i, (_, title) in enumerate(music_queues[guild_id], 1):
        lista += f"**{i}.** {title}\n"

    await interaction.response.send_message(f"📀 **Canciones en la cola:**\n{lista}", ephemeral=False)

@bot.event
async def on_voice_state_update(member, before, after):
    global generator_channel_id
    if after.channel and after.channel.id == generator_channel_id:
        guild = member.guild
        new_category = await guild.create_category(name=f"# {member.display_name}")

        overwrites_voice = {
            guild.default_role: PermissionOverwrite(connect=True),
            member: PermissionOverwrite(manage_channels=True)
        }
        voice_channel = await guild.create_voice_channel(
            name=f"🎤-AUDIO",
            overwrites=overwrites_voice,
            category=new_category,
            user_limit=5
        )
        await member.move_to(voice_channel)

        overwrites_text = {
            guild.default_role: PermissionOverwrite(read_messages=True, send_messages=True)
        }
        text_channel = await guild.create_text_channel(
            name=f"💬-CHAT",
            overwrites=overwrites_text,
            category=new_category
        )

        async def eliminar_canales_si_vacio():
            while True:
                await asyncio.sleep(0.1)
                if len(voice_channel.members) == 0:
                    try:
                        await voice_channel.delete()
                        await text_channel.delete()
                        await new_category.delete()
                    except:
                        pass
                    break

        bot.loop.create_task(eliminar_canales_si_vacio())

bot.run(TOKEN)
