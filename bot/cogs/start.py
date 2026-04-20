# bot/cogs/start.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.onboarding import create_user, is_onboarded, reset_user
from core.activity_logger import log_activity
from bot.views.onboarding_views import (
    CategoryView, GoalInputView, TimeBudgetView, EnergyView, DifficultyView, ResetConfirmView,
)

TIME_LABELS = {"short": "10분 이하", "medium": "10~30분", "long": "30분 이상"}
ENERGY_LABELS = {"low": "낮음", "normal": "보통", "high": "높음"}
DIFF_LABELS = {"light": "아주 가볍게", "moderate": "적당히", "hard": "조금 빡세게"}


class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="Life RPG 모험을 시작합니다")
    async def start(self, interaction: discord.Interaction):
        with get_session() as session:
            discord_id = str(interaction.user.id)
            log_activity(session, "onboarding_start", "onboarding", detail={"discord_id": discord_id})

            # 기존 유저 리셋 확인
            if is_onboarded(session, discord_id):
                confirm_view = ResetConfirmView()
                await interaction.response.send_message(
                    "이미 진행 중인 데이터가 있어요. 처음부터 다시 시작하면 **모든 진행이 초기화**됩니다.\n정말 다시 시작할까요?",
                    view=confirm_view, ephemeral=True,
                )
                await confirm_view.wait()
                if not confirm_view.confirmed:
                    await interaction.edit_original_response(
                        content="취소했어요. 기존 진행이 유지됩니다.", view=None
                    )
                    return
                reset_user(session, discord_id)
                # 리셋 확인 메시지를 Step 1로 전환
                cat_view = CategoryView()
                await interaction.edit_original_response(
                    content="**Step 1/5** 가장 바꾸고 싶은 영역은?",
                    view=cat_view,
                )
                step_msg = await interaction.original_response()
            else:
                # 새 유저: 첫 메시지가 곧 Step 1
                cat_view = CategoryView()
                await interaction.response.send_message(
                    "**Step 1/5** 가장 바꾸고 싶은 영역은?",
                    view=cat_view, ephemeral=True,
                )
                step_msg = await interaction.original_response()

            # Step 1: 카테고리
            await cat_view.wait()
            if cat_view.goal_category is None:
                await step_msg.edit(content="시간 초과! `/start`로 다시 시작해주세요.", view=None)
                return

            # Step 2: 목표 자유 입력
            goal_view = GoalInputView()
            await step_msg.edit(
                content=f"**Step 2/5** '{cat_view.goal_category}' 영역에서 이루고 싶은 목표는?",
                view=goal_view,
            )
            await goal_view.wait()
            goal_text = goal_view.goal_text or f"{cat_view.goal_category} 개선하기"

            # Step 3: 시간
            time_view = TimeBudgetView()
            await step_msg.edit(
                content="**Step 3/5** 하루 여유 시간은?",
                view=time_view,
            )
            await time_view.wait()
            if time_view.time_budget is None:
                await step_msg.edit(content="시간 초과! `/start`로 다시 시작해주세요.", view=None)
                return

            # Step 4: 에너지
            energy_view = EnergyView()
            await step_msg.edit(
                content="**Step 4/5** 현재 에너지 상태는?",
                view=energy_view,
            )
            await energy_view.wait()
            if energy_view.energy is None:
                await step_msg.edit(content="시간 초과! `/start`로 다시 시작해주세요.", view=None)
                return

            # Step 5: 난이도
            diff_view = DifficultyView()
            await step_msg.edit(
                content="**Step 5/5** 원하는 플레이 강도는?",
                view=diff_view,
            )
            await diff_view.wait()
            if diff_view.difficulty is None:
                await step_msg.edit(content="시간 초과! `/start`로 다시 시작해주세요.", view=None)
                return

            # 유저 생성
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

            # 완료 Embed로 최종 편집
            embed = discord.Embed(
                title="온보딩 완료!",
                description=f"Lv.{user.level} {user.nickname}으로 모험을 시작합니다!",
                color=discord.Color.green(),
            )
            embed.add_field(name="목표", value=f"{user.goal_category}: {user.goal_text}", inline=False)
            embed.add_field(name="시간", value=TIME_LABELS.get(user.time_budget, ""), inline=True)
            embed.add_field(name="에너지", value=ENERGY_LABELS.get(user.energy_preference, ""), inline=True)
            embed.add_field(name="강도", value=DIFF_LABELS.get(user.difficulty_preference, ""), inline=True)
            embed.set_footer(text="첫 퀘스트를 보내드릴게요!")

            await step_msg.edit(content=None, embed=embed, view=None)

        # 온보딩 직후 첫 퀘스트 DM 발송
        quest_cog = self.bot.get_cog("QuestUICog")
        if quest_cog:
            await quest_cog.send_daily_quests(discord_id, skip_flow=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StartCog(bot))
