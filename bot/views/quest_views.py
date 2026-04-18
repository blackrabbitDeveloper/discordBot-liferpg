# bot/views/quest_views.py
import discord
from core.database import get_session
from core.models import User, DailyQuest
from core.quest_engine import complete_quest, skip_quest, late_log_quest
from core.reward_engine import apply_reward
from core.streak_engine import update_streak
from core.time_utils import get_game_date


class QuestActionView(discord.ui.View):
    """Persistent View — 봇 재시작 후에도 작동."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="완료했어요", style=discord.ButtonStyle.success,
        custom_id="quest:complete", emoji="\u2705",
    )
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "complete")

    @discord.ui.button(
        label="건너뛰기", style=discord.ButtonStyle.secondary,
        custom_id="quest:skip", emoji="\u23ed\ufe0f",
    )
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "skip")

    async def _handle_action(self, interaction: discord.Interaction, action: str):
        session = get_session()
        discord_id = str(interaction.user.id)
        game_date = get_game_date()

        user = session.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 온보딩을 완료해주세요.", ephemeral=True
            )
            session.close()
            return

        message_id = str(interaction.message.id)
        quest = (
            session.query(DailyQuest)
            .filter_by(user_id=user.id, message_id=message_id)
            .first()
        )
        if not quest:
            await interaction.response.send_message(
                "이 퀘스트를 찾을 수 없어요.", ephemeral=True
            )
            session.close()
            return

        if action == "complete":
            result = complete_quest(session, user, quest.id, game_date)
            if result["success"]:
                reward = apply_reward(session, user, quest.difficulty, quest.reward_stat_type)
                update_streak(session, user, game_date)
                msg = f"퀘스트 완료! +{reward['xp_gained']}XP, {reward['stat_type']} +{reward['stat_gained']}"
                if reward["leveled_up"]:
                    msg += f"\n레벨 업! Lv.{reward['new_level']}!"
                msg += f"\n스트릭: {user.streak}일"
                await interaction.response.edit_message(
                    content=f"~~{quest.title}~~ **완료!**", view=None
                )
                await interaction.followup.send(msg, ephemeral=True)
            elif result.get("reason") == "past_quest":
                await interaction.response.send_message(
                    "이 퀘스트는 과거 기록이에요. 회고 기록으로만 남길 수 있어요.",
                    view=LateLogView(quest.id),
                    ephemeral=True,
                )
        elif action == "skip":
            skip_quest(session, user, quest.id)
            await interaction.response.edit_message(
                content=f"~~{quest.title}~~ 건너뜀", view=None
            )

        session.close()


class LateLogView(discord.ui.View):
    def __init__(self, quest_id: int):
        super().__init__(timeout=120)
        self.quest_id = quest_id

    @discord.ui.button(label="기록만 하기", style=discord.ButtonStyle.secondary)
    async def late_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = get_session()
        discord_id = str(interaction.user.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user:
            late_log_quest(session, user, self.quest_id)
            await interaction.response.edit_message(
                content="회고 기록으로 남겼어요.", view=None
            )
        session.close()

    @discord.ui.button(label="오늘 퀘스트 보기", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="곧 오늘 퀘스트가 도착할 거예요!", view=None
        )
