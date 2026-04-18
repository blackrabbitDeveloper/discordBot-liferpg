import discord
from discord.ext import commands, tasks
from datetime import time, datetime, timedelta
from core.database import get_session
from core.models import User
from core.quest_engine import expire_pending_quests
from core.streak_engine import update_streak
from core.report_engine import generate_daily_report, generate_weekly_report
from core.time_utils import get_game_date
from config import DAY_BOUNDARY_HOUR, MORNING_QUEST_HOUR, EVENING_REPORT_HOUR, WEEKLY_REPORT_DAY


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.morning_task.start()
        self.evening_task.start()
        self.weekly_task.start()
        self.expire_task.start()

    async def cog_unload(self):
        self.morning_task.cancel()
        self.evening_task.cancel()
        self.weekly_task.cancel()
        self.expire_task.cancel()

    @tasks.loop(time=time(hour=DAY_BOUNDARY_HOUR, minute=0))
    async def expire_task(self):
        session = get_session()
        yesterday = get_game_date() - timedelta(days=1)
        expire_pending_quests(session, yesterday)

        users = session.query(User).filter_by(status="active").all()
        for user in users:
            update_streak(session, user, yesterday)

        session.close()

    @tasks.loop(time=time(hour=MORNING_QUEST_HOUR, minute=0))
    async def morning_task(self):
        quest_cog = self.bot.get_cog("QuestUICog")
        if not quest_cog:
            return

        session = get_session()
        users = session.query(User).filter_by(status="active").all()
        for user in users:
            await quest_cog.send_daily_quests(user.discord_id)
        session.close()

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0))
    async def evening_task(self):
        session = get_session()
        game_date = get_game_date()
        users = session.query(User).filter_by(status="active").all()

        for user in users:
            report = generate_daily_report(session, user, game_date)
            try:
                discord_user = await self.bot.fetch_user(int(user.discord_id))
                embed = discord.Embed(
                    title=f"오늘 결과 ({report.report_date})",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="완료", value=f"{report.completed_count}개", inline=True)
                embed.add_field(name="건너뜀", value=f"{report.skipped_count}개", inline=True)
                embed.add_field(name="만료", value=f"{report.expired_count}개", inline=True)
                if report.main_growth_stat:
                    embed.add_field(name="가장 성장한 영역", value=report.main_growth_stat)
                embed.add_field(name="스트릭", value=f"{user.streak}일")
                embed.set_footer(text=report.summary_text)
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass

        session.close()

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0))
    async def weekly_task(self):
        game_date = get_game_date()
        if game_date.weekday() != WEEKLY_REPORT_DAY:
            return

        session = get_session()
        week_start = game_date - timedelta(days=6)
        week_end = game_date

        users = session.query(User).filter_by(status="active").all()
        for user in users:
            report = generate_weekly_report(session, user, week_start, week_end)
            try:
                discord_user = await self.bot.fetch_user(int(user.discord_id))
                embed = discord.Embed(
                    title=f"이번 주 요약 ({report.week_start} ~ {report.week_end})",
                    color=discord.Color.purple(),
                )
                embed.add_field(name="완료율", value=f"{report.completion_rate}%")
                if report.best_stat:
                    embed.add_field(name="가장 성장한 영역", value=report.best_stat)
                if report.risk_pattern:
                    embed.add_field(name="어려웠던 패턴", value=report.risk_pattern)
                embed.set_footer(text=report.suggestion_text)
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass

        session.close()

    @expire_task.before_loop
    @morning_task.before_loop
    @evening_task.before_loop
    @weekly_task.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
