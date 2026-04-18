# bot/cogs/goal.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User
from core.onboarding import GOAL_CATEGORIES


class GoalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="goal", description="목표를 변경합니다")
    @app_commands.describe(
        category="목표 카테고리",
        text="구체적인 목표 (선택)",
    )
    @app_commands.choices(category=[
        app_commands.Choice(name=cat, value=cat) for cat in GOAL_CATEGORIES
    ])
    async def goal(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        text: str | None = None,
    ):
        session = get_session()
        user = session.query(User).filter_by(
            discord_id=str(interaction.user.id)
        ).first()

        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 시작해주세요.", ephemeral=True
            )
            session.close()
            return

        user.goal_category = category.value
        if text:
            user.goal_text = text
        else:
            user.goal_text = f"{category.value} 개선하기"
        session.commit()

        await interaction.response.send_message(
            f"목표가 변경되었어요! → {user.goal_category}: {user.goal_text}",
            ephemeral=True,
        )
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(GoalCog(bot))
