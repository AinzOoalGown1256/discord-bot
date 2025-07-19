import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ChannelType, ButtonStyle, PermissionOverwrite, ChannelType, PartialEmoji
import os
from dotenv import load_dotenv
import asyncio
from nextcord.ui import View, Button

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

generator_channel_id = None

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

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

@bot.event
async def on_voice_state_update(member, before, after):
    global generator_channel_id

    if after.channel and after.channel.id == generator_channel_id:
        guild = member.guild
        stage_channel = await guild.create_stage_channel(
            name=f"{member.display_name}",
            topic="Partida Rankeada de Dota 2",
            user_limit=99
        )

        presentadores = set()
        presentadores.add(member.id)

        try:
            await stage_channel.set_permissions(member, speak=True, connect=True, view_channel=True)
            await member.move_to(stage_channel)
            await stage_channel.edit(user_limit=99)
            await asyncio.sleep(1)
            await stage_channel.request_to_speak()
            await stage_channel.set_permissions(guild.default_role, connect=True, speak=False)
            await stage_channel.start(topic=f"{member.display_name}")
        except Exception as e:
            print(f"Error moviendo a {member.display_name}: {e}")

        async def controlar_participantes():
            while True:
                await asyncio.sleep(1)
                miembros = stage_channel.members
                if len(miembros) == 0:
                    try:
                        await stage_channel.delete()
                    except:
                        pass
                    break
                for user in miembros:
                    if user.id not in presentadores and len(presentadores) < 6:
                        try:
                            await stage_channel.set_permissions(user, speak=True, connect=True, view_channel=True)
                            await stage_channel.request_to_speak()
                            presentadores.add(user.id)
                        except:
                            pass
                    elif user.id not in presentadores:
                        try:
                            await stage_channel.set_permissions(user, speak=False, connect=True, view_channel=True)
                        except:
                            pass

        bot.loop.create_task(controlar_participantes())

bot.run(TOKEN)
