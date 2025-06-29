import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, PermissionOverwrite, ChannelType
import os
from dotenv import load_dotenv
import asyncio

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
        new_category = await guild.create_category(name=f"# {member.display_name}")

        overwrites_voice = {
            guild.default_role: PermissionOverwrite(connect=True),
            member: PermissionOverwrite(manage_channels=True)
        }
        voice_channel = await guild.create_voice_channel(
            name=f"🎤 Sala de {member.display_name}",
            overwrites=overwrites_voice,
            category=new_category,
            user_limit=5
        )
        await member.move_to(voice_channel)

        overwrites_text = {
            guild.default_role: PermissionOverwrite(read_messages=True, send_messages=True)
        }
        text_channel = await guild.create_text_channel(
            name=f"💬 chat-{member.display_name}",
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
