# bot/views/quest_views.py
import discord
from core.database import get_session
from core.models import User, DailyQuest
from core.quest_engine import complete_quest, skip_quest, late_log_quest, replace_quest
from core.quest_loader import load_quests
from core.reward_engine import apply_reward
from core.streak_engine import update_streak
from core.time_utils import get_game_date


class QuestActionView(discord.ui.View):
    """Persistent View — 봇 재시작 후에도 작동.
    custom_id에 quest_id를 포함하여 퀘스트별로 구분."""

    def __init__(self, quest_id: int | None = None):
        super().__init__(timeout=None)
        qid = quest_id or 0
        # 동적 custom_id: quest:{quest_id}:{action}
        self.complete_btn.custom_id = f"quest:{qid}:complete"
        self.replace_btn.custom_id = f"quest:{qid}:replace"
        self.skip_btn.custom_id = f"quest:{qid}:skip"

    @discord.ui.button(label="완료했어요", style=discord.ButtonStyle.success, emoji="\u2705")
    async def complete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_quest_action(interaction, "complete")

    @discord.ui.button(label="다른 걸로", style=discord.ButtonStyle.primary, emoji="\U0001f504")
    async def replace_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_quest_action(interaction, "replace")

    @discord.ui.button(label="건너뛰기", style=discord.ButtonStyle.secondary, emoji="\u23ed\ufe0f")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _handle_quest_action(interaction, "skip")


async def handle_quest_interaction(bot: discord.Client, interaction: discord.Interaction):
    """봇의 on_interaction에서 호출. quest:로 시작하는 custom_id를 처리."""
    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("quest:"):
        return False

    parts = custom_id.split(":")
    if len(parts) != 3:
        return False

    _, quest_id_str, action = parts
    if action not in ("complete", "replace", "skip"):
        return False

    await _handle_quest_action(interaction, action)
    return True


async def _handle_quest_action(interaction: discord.Interaction, action: str):
    """퀘스트 버튼 액션 공통 처리."""
    session = get_session()
    discord_id = str(interaction.user.id)
    game_date = get_game_date()

    try:
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 온보딩을 완료해주세요.", ephemeral=True
            )
            return

        # message_id로 퀘스트 찾기
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
            return

        # 이중 클릭 방지: 이미 처리된 퀘스트
        if quest.state != "PENDING":
            await interaction.response.send_message(
                "이미 처리된 퀘스트예요.", ephemeral=True
            )
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
        elif action == "replace":
            quest_pool = load_quests("data/quests.yaml")
            result = replace_quest(session, user, quest.id, quest_pool, game_date)
            if result["success"]:
                new_quest = result["quest"]
                embed = discord.Embed(
                    title=new_quest.title,
                    description=new_quest.description,
                    color=discord.Color.blue(),
                )
                embed.add_field(name="난이도", value=new_quest.difficulty, inline=True)
                embed.add_field(name="소요 시간", value=f"{new_quest.estimated_minutes}분", inline=True)
                embed.add_field(
                    name="보상",
                    value=f"+{new_quest.reward_xp}XP, {new_quest.reward_stat_type} +{new_quest.reward_stat_value}",
                    inline=True,
                )
                await interaction.response.edit_message(
                    embed=embed, view=QuestActionView(new_quest.id)
                )
            elif result.get("reason") == "no_alternatives":
                await interaction.response.send_message(
                    "바꿀 수 있는 다른 퀘스트가 없어요.", ephemeral=True
                )
            elif result.get("reason") == "not_pending":
                await interaction.response.send_message(
                    "이미 처리된 퀘스트예요.", ephemeral=True
                )
            elif result.get("reason") == "replace_limit":
                await interaction.response.send_message(
                    "오늘 교체 횟수를 모두 사용했어요 (3/3).", ephemeral=True
                )
        elif action == "skip":
            skip_quest(session, user, quest.id)
            await interaction.response.edit_message(
                content=f"~~{quest.title}~~ 건너뜀", view=None
            )
    finally:
        session.close()


class LateLogView(discord.ui.View):
    def __init__(self, quest_id: int):
        super().__init__(timeout=120)
        self.quest_id = quest_id

    @discord.ui.button(label="기록만 하기", style=discord.ButtonStyle.secondary)
    async def late_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = get_session()
        try:
            discord_id = str(interaction.user.id)
            user = session.query(User).filter_by(discord_id=discord_id).first()
            if user:
                late_log_quest(session, user, self.quest_id)
                await interaction.response.edit_message(
                    content="회고 기록으로 남겼어요.", view=None
                )
        finally:
            session.close()

    @discord.ui.button(label="오늘 퀘스트 보기", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="곧 오늘 퀘스트가 도착할 거예요!", view=None
        )


class MorningFlowView(discord.ui.View):
    """아침 메시지: 오늘의 플로우를 선택하는 뷰."""

    def __init__(self):
        super().__init__(timeout=3600)
        self.choice = None

    @discord.ui.button(label="이대로 할래요", style=discord.ButtonStyle.primary, emoji="\u2705")
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "normal"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="오늘은 가볍게", style=discord.ButtonStyle.secondary, emoji="\U0001f33f")
    async def light(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "light"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="회복 모드", style=discord.ButtonStyle.secondary, emoji="\U0001f49a")
    async def recovery(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "recovery"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="오늘은 쉬어갈래요", style=discord.ButtonStyle.secondary, emoji="\U0001f634")
    async def rest(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "rest"
        await interaction.response.defer()
        self.stop()
