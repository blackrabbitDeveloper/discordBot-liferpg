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


async def _close_step(msg, step: str, value: str):
    """완료된 단계 메시지를 편집하여 결과만 남기고 버튼 제거."""
    try:
        await msg.edit(content=f"{step} **{value}**", view=None)
    except Exception:
        pass


class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="Life RPG 모험을 시작합니다")
    async def start(self, interaction: discord.Interaction):
        session = get_session()
        try:
            discord_id = str(interaction.user.id)
            log_activity(session, "onboarding_start", "onboarding", detail={"discord_id": discord_id})

            if is_onboarded(session, discord_id):
                confirm_view = ResetConfirmView()
                await interaction.response.send_message(
                    "이미 진행 중인 데이터가 있어요. 처음부터 다시 시작하면 **모든 진행이 초기화**됩니다.\n정말 다시 시작할까요?",
                    view=confirm_view, ephemeral=True,
                )
                await confirm_view.wait()
                # 확인 메시지 정리
                try:
                    if confirm_view.confirmed:
                        await interaction.edit_original_response(content="다시 시작합니다!", view=None)
                    else:
                        await interaction.edit_original_response(content="취소했어요. 기존 진행이 유지됩니다.", view=None)
                except Exception:
                    pass

                if not confirm_view.confirmed:
                    return
                reset_user(session, discord_id)
                await interaction.followup.send("모험을 시작할게요! 몇 가지 질문에 답해주세요.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "모험을 시작할게요! 몇 가지 질문에 답해주세요.",
                    ephemeral=True,
                )

            # Step 1: 카테고리
            cat_view = CategoryView()
            step1_msg = await interaction.followup.send(
                "**Step 1/5** 가장 바꾸고 싶은 영역은?",
                view=cat_view, ephemeral=True, wait=True,
            )
            await cat_view.wait()
            if cat_view.goal_category is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return
            await _close_step(step1_msg, "Step 1/5 완료:", cat_view.goal_category)

            # Step 2: 목표 자유 입력
            goal_button_view = GoalInputView()
            step2_msg = await interaction.followup.send(
                f"**Step 2/5** '{cat_view.goal_category}' 영역에서 이루고 싶은 목표는?",
                view=goal_button_view, ephemeral=True, wait=True,
            )
            await goal_button_view.wait()
            goal_text = goal_button_view.goal_text or f"{cat_view.goal_category} 개선하기"
            await _close_step(step2_msg, "Step 2/5 완료:", goal_text)

            # Step 3: 시간
            time_view = TimeBudgetView()
            step3_msg = await interaction.followup.send(
                "**Step 3/5** 하루 여유 시간은?",
                view=time_view, ephemeral=True, wait=True,
            )
            await time_view.wait()
            if time_view.time_budget is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return
            await _close_step(step3_msg, "Step 3/5 완료:", TIME_LABELS.get(time_view.time_budget, time_view.time_budget))

            # Step 4: 에너지
            energy_view = EnergyView()
            step4_msg = await interaction.followup.send(
                "**Step 4/5** 현재 에너지 상태는?",
                view=energy_view, ephemeral=True, wait=True,
            )
            await energy_view.wait()
            if energy_view.energy is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return
            await _close_step(step4_msg, "Step 4/5 완료:", ENERGY_LABELS.get(energy_view.energy, energy_view.energy))

            # Step 5: 난이도
            diff_view = DifficultyView()
            step5_msg = await interaction.followup.send(
                "**Step 5/5** 원하는 플레이 강도는?",
                view=diff_view, ephemeral=True, wait=True,
            )
            await diff_view.wait()
            if diff_view.difficulty is None:
                await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
                return
            await _close_step(step5_msg, "Step 5/5 완료:", DIFF_LABELS.get(diff_view.difficulty, diff_view.difficulty))

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
