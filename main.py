# main.py
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, DATABASE_URL
from core.database import init_db, get_engine
from core.models import Base

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced.")


async def setup():
    init_db(DATABASE_URL)
    Base.metadata.create_all(get_engine())
    await bot.load_extension("bot.cogs.start")
    await bot.load_extension("bot.cogs.quest_ui")
    await bot.load_extension("bot.cogs.status")
    await bot.load_extension("bot.cogs.goal")
    await bot.load_extension("bot.cogs.pause")
    await bot.load_extension("bot.scheduler")


def main():
    import asyncio
    asyncio.run(setup())
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
