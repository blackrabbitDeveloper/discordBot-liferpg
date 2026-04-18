# bot/cogs/start.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.onboarding import create_user, is_onboarded, reset_user
from bot.views.onboarding_views import (
    CategoryView, GoalInputView, TimeBudgetView, EnergyView, DifficultyView, ResetConfirmView,
)


class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="Life RPG 모험을 시작합니다")
    async def start(self, interaction: discord.Interaction):
        session = get_session()
        try:
            discord_id = str(interaction.user.id)

            if is_onboarded(session, discord_id):
                confirm_view = ResetConfirmView()
                await interaction.response.send_message(
                    "이미 진행 중인 데이터가 있어요. 처음부터 다시 시작하면 **모든 진행이 초기화**됩니다.\n정말 다시 시작할까요?",
                    view=confirm_view, ephemeral=True,
                )
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    await interaction.followup.send("취소했어요. 기존 진행이 유지됩니다.", ephemeral=True)
                    return
                reset_user(session, discord_id)
                await interaction.followup.send("모험을 시작할게요! 몇 가지 질문에 답해주세요.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "모험을 시작할게요! 몇 가지 질문에 답해주세요.",
                    ephemeral=True,
                )

            cat_view = CategoryView()
            await interaction.followup.send(
                "**Step 1/5** 가장 바꾸고 싶은 영역은?",
                view=cat_view, ephemeral=True,
            )
            await cat_view.wait()
            if cat_view.goal_category is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return

            # Step 2: 목표 자유 입력 (Modal)
            goal_button_view = GoalInputView()
            await interaction.followup.send(
                f"**Step 2/5** '{cat_view.goal_category}' 영역에서 이루고 싶은 목표는?",
                view=goal_button_view, ephemeral=True,
            )
            await goal_button_view.wait()
            goal_text = goal_button_view.goal_text or f"{cat_view.goal_category} 개선하기"

            time_view = TimeBudgetView()
            await interaction.followup.send(
                "**Step 3/5** 하루 여유 시간은?",
                view=time_view, ephemeral=True,
            )
            await time_view.wait()
            if time_view.time_budget is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return

            energy_view = EnergyView()
            await interaction.followup.send(
                "**Step 4/5** 현재 에너지 상태는?",
                view=energy_view, ephemeral=True,
            )
            await energy_view.wait()
            if energy_view.energy is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return

            diff_view = DifficultyView()
            await interaction.followup.send(
                "**Step 5/5** 원하는 플레이 강도는?",
                view=diff_view, ephemeral=True,
            )
            await diff_view.wait()
            if diff_view.difficulty is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
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
        finally:
            session.close()

        # 온보딩 직후 첫 퀘스트 DM 발송
        quest_cog = self.bot.get_cog("QuestUICog")
        if quest_cog:
            await quest_cog.send_daily_quests(discord_id, skip_flow=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StartCog(bot))
