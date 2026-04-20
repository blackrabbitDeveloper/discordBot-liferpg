# bot/cogs/quest_ui.py
import discord
from discord.ext import commands
from core.database import get_session
from core.models import User
from core.quest_engine import generate_daily_quests, get_today_quests
from core.quest_loader import load_quests
from core.time_utils import get_game_date
from bot.views.quest_views import QuestActionView, MorningFlowView
from core.activity_logger import log_activity


class QuestUICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quest_pool = load_quests("data/quests.yaml")

    async def cog_load(self):
        pass  # 동적 custom_id 사용 → main.py on_interaction에서 처리

    async def send_daily_quests(self, user_discord_id: str, skip_flow: bool = False):
        """특정 유저에게 DM으로 오늘 퀘스트를 보낸다.
        skip_flow=True면 플로우 선택 없이 바로 퀘스트 발송 (온보딩 직후 등).
        """
        with get_session() as session:
            user = session.query(User).filter_by(discord_id=user_discord_id).first()
            if not user or user.status != "active":
                return

            game_date = get_game_date()

            # 이미 오늘 퀘스트가 있으면 발송만
            existing = get_today_quests(session, user, game_date)
            if existing:
                await self._send_quest_dms(user_discord_id, existing, session)
                return

            try:
                discord_user = await self.bot.fetch_user(int(user_discord_id))
            except Exception:
                return

            energy_override = None
            category_override = None

            if not skip_flow:
                # 아침 플로우 선택 메시지
                embed = discord.Embed(
                    title="좋은 아침이에요!",
                    description="오늘은 어떤 흐름으로 가볼까요?",
                    color=discord.Color.blue(),
                )
                flow_view = MorningFlowView()
                try:
                    flow_msg = await discord_user.send(embed=embed, view=flow_view)
                except discord.Forbidden:
                    return

                await flow_view.wait()

                # 플로우 선택 로그
                log_activity(session, "morning_flow_choice", "flow",
                            user_id=user.id, detail={"choice": flow_view.choice or "timeout"})
                session.commit()

                if flow_view.choice == "rest":
                    await discord_user.send("오늘은 쉬어가는 턴이에요. 내일 다시 이어가면 됩니다. 푹 쉬세요!")
                    return
                elif flow_view.choice == "light":
                    energy_override = "low"
                elif flow_view.choice == "recovery":
                    category_override = "회복"
                    energy_override = "low"
                elif flow_view.choice is None:
                    # 타임아웃: 기본값으로 진행
                    pass

                # 플로우 메시지 정리 (버튼 제거)
                try:
                    choice_text = {
                        "normal": "이대로 할래요",
                        "light": "오늘은 가볍게",
                        "recovery": "회복 모드",
                        None: "기본 모드 (자동)",
                    }.get(flow_view.choice, "이대로 할래요")
                    await flow_msg.edit(
                        embed=discord.Embed(
                            title="좋은 아침이에요!",
                            description=f"오늘의 선택: **{choice_text}**",
                            color=discord.Color.green(),
                        ),
                        view=None,
                    )
                except Exception:
                    pass

            # 퀘스트 생성
            quests = generate_daily_quests(
                session, user, self.quest_pool, game_date,
                energy_override=energy_override,
                category_override=category_override,
            )

            await self._send_quest_dms(user_discord_id, quests, session)

    async def _send_quest_dms(self, user_discord_id: str, quests: list, session):
        """퀘스트를 개별 DM으로 발송."""
        try:
            discord_user = await self.bot.fetch_user(int(user_discord_id))
        except Exception:
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

            view = QuestActionView(quest_id=quest.id)
            try:
                msg = await discord_user.send(embed=embed, view=view)
                quest.message_id = str(msg.id)
            except discord.Forbidden:
                pass

        session.commit()


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestUICog(bot))
