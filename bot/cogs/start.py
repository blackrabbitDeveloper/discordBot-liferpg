# bot/cogs/start.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.onboarding import create_user, is_onboarded, reset_user
from bot.views.onboarding_views import (
    CategoryView, TimeBudgetView, EnergyView, DifficultyView,
)


class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="Life RPG 모험을 시작합니다")
    async def start(self, interaction: discord.Interaction):
        session = get_session()
        discord_id = str(interaction.user.id)

        if is_onboarded(session, discord_id):
            reset_user(session, discord_id)

        await interaction.response.send_message(
            "모험을 시작할게요! 몇 가지 질문에 답해주세요.",
            ephemeral=True,
        )

        cat_view = CategoryView()
        await interaction.followup.send(
            "**Step 1/4** 가장 바꾸고 싶은 영역은?",
            view=cat_view, ephemeral=True,
        )
        await cat_view.wait()
        if cat_view.goal_category is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        goal_text = f"{cat_view.goal_category} 개선하기"

        time_view = TimeBudgetView()
        await interaction.followup.send(
            "**Step 2/4** 하루 여유 시간은?",
            view=time_view, ephemeral=True,
        )
        await time_view.wait()
        if time_view.time_budget is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        energy_view = EnergyView()
        await interaction.followup.send(
            "**Step 3/4** 현재 에너지 상태는?",
            view=energy_view, ephemeral=True,
        )
        await energy_view.wait()
        if energy_view.energy is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        diff_view = DifficultyView()
        await interaction.followup.send(
            "**Step 4/4** 원하는 플레이 강도는?",
            view=diff_view, ephemeral=True,
        )
        await diff_view.wait()
        if diff_view.difficulty is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        user = create_user(
            session,
            discord_id=discord_id,
            nickname=interaction.user.display_name,
            goal_category=cat_view.goal_category,
            goal_text=goal_text,
            time_budget=time_view.time_budget,
            energy_preference=energy_view.energy,
            difficulty_preference=diff_view.difficulty,
        )

        embed = discord.Embed(
            title="온보딩 완료!",
            description=f"Lv.{user.level} {user.nickname}으로 모험을 시작합니다!",
            color=discord.Color.green(),
        )
        embed.add_field(name="목표", value=f"{user.goal_category}: {user.goal_text}")
        embed.set_footer(text="첫 퀘스트를 보내드릴게요!")

        await interaction.followup.send(embed=embed, ephemeral=True)
        session.close()

        # 온보딩 직후 첫 퀘스트 DM 발송
        quest_cog = self.bot.get_cog("QuestUICog")
        if quest_cog:
            await quest_cog.send_daily_quests(discord_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(StartCog(bot))
