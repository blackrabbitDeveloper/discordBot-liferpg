import discord
from discord.ext import commands
from core.database import get_session
from core.guild_config import get_channel


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"[WELCOME] on_member_join fired: {member.display_name} (bot={member.bot})")
        if member.bot:
            return

        session = get_session()
        try:
            channel_id = get_channel(session, str(member.guild.id), "welcome")
            print(f"[WELCOME] guild={member.guild.id}, channel_id={channel_id}")
        finally:
            session.close()

        if channel_id is None:
            print("[WELCOME] No welcome channel configured, skipping")
            return

        channel = member.guild.get_channel(int(channel_id))
        print(f"[WELCOME] Resolved channel: {channel}")
        if channel is None:
            print("[WELCOME] Channel not found in cache, skipping")
            return

        embed = discord.Embed(
            title=f"{member.display_name}님, 환영해요!",
            description=(
                "이곳은 매일 작은 퀘스트를 통해 성장하는 **Life RPG** 서버예요.\n\n"
                "운동, 공부, 정리 같은 일상 루틴이 퀘스트가 되고,\n"
                "경험치와 스탯으로 나의 성장을 확인할 수 있어요.\n\n"
                "`/start` 명령어로 나만의 모험을 시작해보세요!"
            ),
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Life RPG · 매일 조금씩 성장하기")

        await channel.send(content=member.mention, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
