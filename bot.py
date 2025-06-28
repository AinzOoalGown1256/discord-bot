import nextcord
from nextcord.ext import commands
from nextcord import Interaction
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.slash_command(name="ping", description="Responde con pong")
async def ping(interaction: Interaction):
    await interaction.response.send_message("🏓 Pong!")

bot.run(TOKEN)
