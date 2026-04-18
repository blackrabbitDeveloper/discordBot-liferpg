# bot/cogs/quest_ui.py
import discord
from discord.ext import commands
from core.database import get_session
from core.models import User
from core.quest_engine import generate_daily_quests, get_today_quests
from core.quest_loader import load_quests
from core.time_utils import get_game_date
from bot.views.quest_views import QuestActionView


class QuestUICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quest_pool = load_quests("data/quests.yaml")

    async def cog_load(self):
        self.bot.add_view(QuestActionView())

    async def send_daily_quests(self, user_discord_id: str):
        session = get_session()
        user = session.query(User).filter_by(discord_id=user_discord_id).first()
        if not user or user.status != "active":
            session.close()
            return

        game_date = get_game_date()
        quests = get_today_quests(session, user, game_date)
        if not quests:
            quests = generate_daily_quests(session, user, self.quest_pool, game_date)

        discord_user = await self.bot.fetch_user(int(user_discord_id))
        if not discord_user:
            session.close()
            return

        for quest in quests:
            if quest.state != "PENDING":
                continue

            embed = discord.Embed(
                title=quest.title,
                description=quest.description,
                color=discord.Color.blue(),
            )
            embed.add_field(name="난이도", value=quest.difficulty, inline=True)
            embed.add_field(name="소요 시간", value=f"{quest.estimated_minutes}분", inline=True)
            embed.add_field(
                name="보상",
                value=f"+{quest.reward_xp}XP, {quest.reward_stat_type} +{quest.reward_stat_value}",
                inline=True,
            )

            view = QuestActionView()
            msg = await discord_user.send(embed=embed, view=view)
            quest.message_id = str(msg.id)

        session.commit()
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestUICog(bot))
