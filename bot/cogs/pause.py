# bot/cogs/pause.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User


class PauseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pause", description="쉬기 모드를 전환합니다")
    async def pause(self, interaction: discord.Interaction):
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

        if user.status == "active":
            user.status = "paused"
            session.commit()
            await interaction.response.send_message(
                "쉬기 모드로 전환했어요. 알림이 줄어들고, 회복 퀘스트 위주로 추천돼요.\n"
                "다시 `/pause`를 누르면 복귀할 수 있어요.",
                ephemeral=True,
            )
        else:
            user.status = "active"
            session.commit()
            await interaction.response.send_message(
                "다시 활성 모드로 돌아왔어요! 내일 아침부터 퀘스트가 다시 도착해요.",
                ephemeral=True,
            )

        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(PauseCog(bot))
