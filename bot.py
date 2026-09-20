import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ChannelType, PermissionOverwrite, ButtonStyle
from nextcord.ui import View, Button
import os
from dotenv import load_dotenv
import asyncio
import aiohttp

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario: {guild_id: generator_channel_id}
generadores = {}

# ------------------- COMANDO /generador -------------------
@bot.slash_command(name="generador", description="Asignar canal generador de salas temporales")
async def generador(
    interaction: Interaction,
    generator: nextcord.VoiceChannel = SlashOption(
        name="generator",
        description="Canal de voz generador",
        channel_types=[ChannelType.voice]
    )
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No tienes permisos.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild.id
    nuevo_id = generator.id
    old_id = generadores.get(guild_id)
    generadores[guild_id] = nuevo_id
    
    mensaje = f"Canal generador asignado: <#{nuevo_id}>"
    if old_id and old_id != nuevo_id:
        mensaje = f"Canal actualizado: <#{old_id}> ➔ <#{nuevo_id}>"
    
    await interaction.followup.send(mensaje, ephemeral=True)

# ------------------- EVENTO CANALES TEMPORALES (generador) -------------------
@bot.event
async def on_voice_state_update(member, before, after):
    if not after.channel:
        return
    
    guild_id = member.guild.id
    generator_id = generadores.get(guild_id)
    
    if generator_id is None:
        return
    
    if after.channel.id != generator_id:
        return
    
    guild = member.guild
    new_category = await guild.create_category(name=f"# {member.display_name}")

    overwrites_voice = {
        guild.default_role: PermissionOverwrite(connect=True),
        member: PermissionOverwrite(manage_channels=True)
    }
    voice_channel = await guild.create_voice_channel(
        name=f"AUDIO",
        overwrites=overwrites_voice,
        category=new_category,
        user_limit=11
    )
    await member.edit(voice_channel=voice_channel)

    overwrites_text = {
        guild.default_role: PermissionOverwrite(read_messages=True, send_messages=True)
    }
    text_channel = await guild.create_text_channel(
        name=f"CHAT",
        overwrites=overwrites_text,
        category=new_category
    )

    async def eliminar_canales_si_vacio():
        while True:
            await asyncio.sleep(1)
            if len(voice_channel.members) == 0:
                try:
                    await voice_channel.delete()
                    await text_channel.delete()
                    await new_category.delete()
                except:
                    pass
                break

    bot.loop.create_task(eliminar_canales_si_vacio())

# ------------------- VISTA CON BOTÓN PARA UNIRSE AL CREADOR -------------------
class UnirseAlCreadorView(View):
    def __init__(self, creador_id, timeout=600):
        super().__init__(timeout=timeout)
        self.creador_id = creador_id

    @nextcord.ui.button(label="Unirse a la partida", style=ButtonStyle.success, emoji="🎮")
    async def unirse(self, button: Button, interaction: Interaction):
        guild = interaction.guild
        creador = guild.get_member(self.creador_id)
        
        if not creador:
            await interaction.response.send_message(
                "El creador ya no está en el servidor.",
                ephemeral=True
            )
            return
        
        # Verificar si el creador está en un canal de voz
        if not creador.voice or not creador.voice.channel:
            await interaction.response.send_message(
                "El creador no está en un canal de voz en este momento.",
                ephemeral=True
            )
            return
        
        canal_voz_creador = creador.voice.channel
        member = interaction.user
        
        # Si ya está en el mismo canal
        if member.voice and member.voice.channel and member.voice.channel.id == canal_voz_creador.id:
            await interaction.response.send_message(
                "Ya estás en la partida del creador.",
                ephemeral=True
            )
            return
        
        # Si el que presiona ya está en un canal de voz, moverlo automáticamente
        if member.voice and member.voice.channel:
            try:
                await member.move_to(canal_voz_creador)
                await interaction.response.send_message(
                    f"Te uniste a la partida en <#{canal_voz_creador.id}>.",
                    ephemeral=True
                )
                return
            except Exception as e:
                print(f"Error al mover: {e}")
        
        # Si no está en ningún canal de voz, enviar enlace directo
        enlace = f"https://discord.com/channels/{guild.id}/{canal_voz_creador.id}"
        await interaction.response.send_message(
            f"🎮 **Únete a la partida aquí:**\n{enlace}",
            ephemeral=True
        )

# ------------------- COMANDO /buscarpartida -------------------
@bot.slash_command(name="buscarpartida", description="Publica tu perfil para buscar partida")
async def buscarpartida(
    interaction: Interaction,
    id_jugador: int = SlashOption(
        name="id",
        description="Steam32 Account ID (ej: 1568537464)",
        required=True
    )
):
    await interaction.response.defer()

    url = f"https://api.opendota.com/api/players/{id_jugador}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send("No se pudo encontrar al jugador. Verifica el ID.")
                    return
                data = await response.json()
    except Exception as e:
        await interaction.followup.send(f"Error al consultar la API: {e}")
        return

    perfil = data.get('profile', {})
    nombre = perfil.get('personaname', 'Desconocido')
    avatar = perfil.get('avatarfull')
    rank_tier = data.get('rank_tier')

    medalla_texto = "Unranked"
    if rank_tier:
        medallas = ["Heraldo", "Guardián", "Cruzado", "Arconte", "Leyenda", "Ancestro", "Divino", "Inmortal"]
        estrellas = ["", "I", "II", "III", "IV", "V"]
        indice_medalla = (rank_tier // 10) - 1
        indice_estrella = rank_tier % 10
        if 0 <= indice_medalla < len(medallas):
            medalla_texto = f"{medallas[indice_medalla]} {estrellas[indice_estrella]}"

    embed = nextcord.Embed(
        title=f"🎮 Buscando partida - {nombre}",
        description=f"**Rango:** {medalla_texto}\n**ID:** {id_jugador}",
        color=0x00FF00
    )
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text="Haz clic en el botón para unirte a la partida del creador")

    view = UnirseAlCreadorView(interaction.user.id)
    await interaction.followup.send(embed=embed, view=view)

# ------------------- READY -------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("Comandos slash sincronizados")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
