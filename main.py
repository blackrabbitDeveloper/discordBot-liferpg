# main.py
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, DATABASE_URL
from core.database import init_db, get_engine
from core.models import Base

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced.")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Persistent View의 동적 custom_id를 처리."""
    if interaction.type == discord.InteractionType.component:
        from bot.views.quest_views import handle_quest_interaction
        handled = await handle_quest_interaction(bot, interaction)
        if handled:
            return


async def setup_hook():
    init_db(DATABASE_URL)
    Base.metadata.create_all(get_engine())
    await bot.load_extension("bot.cogs.start")
    await bot.load_extension("bot.cogs.quest_ui")
    await bot.load_extension("bot.cogs.status")
    await bot.load_extension("bot.cogs.goal")
    await bot.load_extension("bot.cogs.pause")
    await bot.load_extension("bot.scheduler")
    await bot.load_extension("bot.cogs.settings")
    await bot.load_extension("bot.cogs.welcome")
    await bot.load_extension("bot.cogs.admin")

bot.setup_hook = setup_hook


def main():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
