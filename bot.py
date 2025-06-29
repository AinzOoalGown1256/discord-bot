import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, PermissionOverwrite, ChannelType
import os
from dotenv import load_dotenv
import asyncio
import threading
import http.server
import socketserver

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

generator_channel_id = None

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True
user_text_channels = {}

bot = commands.Bot(command_prefix="!", intents=intents)

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
        "/yp generador <canal> – Asigna o actualiza el canal generador de salas temporales.\n"
        "/yp invite <usuarios> – Invita usuarios a tu sala privada.\n\n"
        "🔧 Cuando un usuario se una al canal generador, se crea una sala temporal."
    )
    await interaction.response.send_message(mensaje, ephemeral=True)

@bot.slash_command(name="yp", description="Comandos para gestiónar")
async def yp(interaction: Interaction):
    await interaction.response.send_message(
        "Usa los subcomandos:\n"
        "/yp generador <canal> - Asigna el canal generador\n"
        "/yp invite <usuarios> - Invita usuarios a tu sala privada",
        ephemeral=True
    )

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

    nuevo_id = generator.id
    if generator_channel_id and generator_channel_id != nuevo_id:
        canal_anterior = interaction.guild.get_channel(generator_channel_id)
        if canal_anterior:
            await interaction.response.send_message(
                f"Se ha actualizado el canal generador: <#{generator_channel_id}> ➔ <#{nuevo_id}>",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"Canal generador asignado: <#{nuevo_id}>", ephemeral=True)
    else:
        await interaction.response.send_message(f"Canal generador asignado: <#{nuevo_id}>", ephemeral=True)
    generator_channel_id = nuevo_id

@bot.event
async def on_voice_state_update(member, before, after):
    global generator_channel_id, user_text_channels
    if after.channel and after.channel.id == generator_channel_id:
        guild = member.guild
        new_category = await guild.create_category(name=f"# {member.display_name}")
        overwrites_voice = {
            guild.default_role: PermissionOverwrite(connect=False),
            member: PermissionOverwrite(connect=True, manage_channels=True)
        }
        voice_channel = await guild.create_voice_channel(
            name=f"🎤 Sala de {member.display_name}",
            overwrites=overwrites_voice,
            category=new_category,
            user_limit=5
        )
        await member.move_to(voice_channel)

        overwrites_text = {
            guild.default_role: PermissionOverwrite(read_messages=False),
            member: PermissionOverwrite(read_messages=True, send_messages=True)
        }
        text_channel = await guild.create_text_channel(
            name=f"💬 chat-{member.display_name}",
            overwrites=overwrites_text,
            category=new_category
        )

        user_text_channels[member.id] = text_channel.id

        async def actualizar_permisos():
            miembros_actuales = set()
            while voice_channel and voice_channel.members:
                nuevos_miembros = set(voice_channel.members)
                nuevos_ingresos = nuevos_miembros - miembros_actuales
                for m in nuevos_ingresos:
                    if text_channel.overwrites_for(m).read_messages is not True:
                        await text_channel.set_permissions(m, read_messages=True, send_messages=True)
                miembros_actuales = nuevos_miembros
                await asyncio.sleep(1)

        async def eliminar_canales_si_vacio():
            while True:
                await asyncio.sleep(1)
                if len(voice_channel.members) == 0:
                    try:
                        await voice_channel.delete()
                        await text_channel.delete()
                        await new_category.delete()
                        user_text_channels.pop(member.id, None)
                    except:
                        pass
                    break

        bot.loop.create_task(actualizar_permisos())
        bot.loop.create_task(eliminar_canales_si_vacio())

@yp.subcommand(name="invite", description="Invita hasta 4 usuarios a tu canal de voz privado")
async def yp_invite(
    interaction: Interaction,
    usuario1: nextcord.Member = SlashOption(required=True, description="Usuario 1"),
    usuario2: nextcord.Member = SlashOption(required=False, description="Usuario 2"),
    usuario3: nextcord.Member = SlashOption(required=False, description="Usuario 3"),
    usuario4: nextcord.Member = SlashOption(required=False, description="Usuario 4"),
):
    global user_text_channels

    if user_text_channels.get(interaction.user.id) != interaction.channel.id:
        await interaction.response.send_message("Este comando solo se puede usar en tu canal privado de texto.", ephemeral=True)
        return

    canal = interaction.user.voice.channel
    if not canal:
        await interaction.response.send_message("No estás en ningún canal de voz.", ephemeral=True)
        return

    limite_total = 5
    espacio_disponible = limite_total - len(canal.members)
    if espacio_disponible <= 0:
        await interaction.response.send_message("La sala ya está llena.", ephemeral=True)
        return

    usuarios = [u for u in [usuario1, usuario2, usuario3, usuario4] if u is not None]
    if len(usuarios) > espacio_disponible:
        await interaction.response.send_message(f"Solo hay espacio para {espacio_disponible} usuarios.", ephemeral=True)
        return

    for usuario in usuarios:
        await canal.set_permissions(usuario, connect=True)

    await interaction.response.send_message(
        f"Invitados: {', '.join(u.mention for u in usuarios)}", ephemeral=True
    )

if os.environ.get("RENDER") == "true":
    def fake_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    threading.Thread(target=fake_server).start()

bot.run(TOKEN)
