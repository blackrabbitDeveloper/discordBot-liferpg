# bot/cogs/status.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="현재 상태를 확인합니다")
    async def status(self, interaction: discord.Interaction):
        with get_session() as session:
            user = session.query(User).filter_by(
                discord_id=str(interaction.user.id)
            ).first()

            if not user:
                await interaction.response.send_message(
                    "`/start`로 먼저 시작해주세요.", ephemeral=True
                )
                return

            s = user.stats
            embed = discord.Embed(
                title=f"{user.nickname} | Lv.{user.level}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="XP", value=f"{user.xp} / {user.level * 100}", inline=True)
            embed.add_field(name="스트릭", value=f"{user.streak}일", inline=True)
            embed.add_field(name="상태", value=user.status, inline=True)
            embed.add_field(name="목표", value=f"{user.goal_category}: {user.goal_text}", inline=False)
            embed.add_field(
                name="스탯",
                value=(
                    f"체력: {s.health} | 집중: {s.focus} | 실행: {s.execution}\n"
                    f"지식: {s.knowledge} | 재정: {s.finance}"
                ),
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
