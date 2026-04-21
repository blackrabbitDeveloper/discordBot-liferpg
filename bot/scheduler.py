import logging
import discord
from discord.ext import commands, tasks
from datetime import time, datetime, timedelta
from core.database import get_session
from core.models import User, DailyQuest, DailyReport, WeeklyReport
from core.quest_engine import expire_pending_quests
from core.streak_engine import update_streak
from core.report_engine import generate_daily_report, generate_weekly_report
from core.time_utils import get_game_date, KST
from config import DAY_BOUNDARY_HOUR, MORNING_QUEST_HOUR, EVENING_REPORT_HOUR, WEEKLY_REPORT_DAY

log = logging.getLogger(__name__)


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._catchup_done = False

    async def cog_load(self):
        self.morning_task.start()
        self.evening_task.start()
        self.weekly_task.start()
        self.expire_task.start()
        self.catchup_loop.start()

    async def cog_unload(self):
        self.morning_task.cancel()
        self.evening_task.cancel()
        self.weekly_task.cancel()
        self.expire_task.cancel()
        self.catchup_loop.cancel()

    @tasks.loop(time=time(hour=DAY_BOUNDARY_HOUR, minute=0, tzinfo=KST))
    async def expire_task(self):
        """새벽 4시 KST: 전날 PENDING 퀘스트 만료 + 스트릭 업데이트."""
        with get_session() as session:
            yesterday = get_game_date() - timedelta(days=1)
            expire_pending_quests(session, yesterday)

            users = session.query(User).filter_by(status="active").all()
            for user in users:
                update_streak(session, user, yesterday)

    @tasks.loop(time=time(hour=MORNING_QUEST_HOUR, minute=0, tzinfo=KST))
    async def morning_task(self):
        """아침 8시 KST: 퀘스트 발송."""
        log.info("morning_task triggered")
        print("[Scheduler] morning_task triggered", flush=True)
        quest_cog = self.bot.get_cog("QuestUICog")
        if not quest_cog:
            print("[Scheduler] WARNING: QuestUICog not found", flush=True)
            return

        try:
            with get_session() as session:
                users = session.query(User).filter_by(status="active").all()
                discord_ids = [user.discord_id for user in users]

            print(f"[Scheduler] morning quests: {len(discord_ids)} users", flush=True)
            for discord_id in discord_ids:
                await quest_cog.send_daily_quests(discord_id, skip_flow=True)
                print(f"[Scheduler] quests sent to {discord_id}", flush=True)
        except Exception:
            log.exception("morning_task failed")
            print("[Scheduler] morning_task ERROR — see log", flush=True)

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0, tzinfo=KST))
    async def evening_task(self):
        """저녁 9시 KST: 일일 리포트 발송."""
        log.info("evening_task triggered")
        print("[Scheduler] evening_task triggered", flush=True)
        try:
            with get_session() as session:
                game_date = get_game_date()
                users = session.query(User).filter_by(status="active").all()
                print(f"[Scheduler] daily report: {len(users)} active users, game_date={game_date}", flush=True)

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
                        print(f"[Scheduler] daily report sent to {user.discord_id}", flush=True)
                    except discord.Forbidden:
                        log.warning("Cannot DM user %s (Forbidden)", user.discord_id)
        except Exception:
            log.exception("evening_task failed")
            print("[Scheduler] evening_task ERROR — see log", flush=True)

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0, tzinfo=KST))
    async def weekly_task(self):
        """일요일 저녁 9시 KST: 주간 리포트 발송."""
        game_date = get_game_date()
        if game_date.weekday() != WEEKLY_REPORT_DAY:
            return

        with get_session() as session:
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

    @tasks.loop(minutes=30)
    async def catchup_loop(self):
        """30분마다 오늘 퀘스트/리포트 누락 여부를 확인하고 보충 발송."""
        if not self._catchup_done:
            return  # on_ready catch-up이 아직 안 끝났으면 스킵

        now = datetime.now(KST)
        game_date = get_game_date(now)

        # 아침 8시 이후: 퀘스트 미발송 체크
        if now.hour >= MORNING_QUEST_HOUR:
            quest_cog = self.bot.get_cog("QuestUICog")
            if quest_cog:
                with get_session() as session:
                    users = session.query(User).filter_by(status="active").all()
                    for user in users:
                        has_quests = (
                            session.query(DailyQuest)
                            .filter_by(user_id=user.id, quest_date=game_date)
                            .first()
                        )
                        if not has_quests:
                            print(f"[Catchup-loop] sending quests to {user.discord_id}", flush=True)
                            await quest_cog.send_daily_quests(user.discord_id, skip_flow=True)

    @catchup_loop.before_loop
    async def before_catchup_loop(self):
        await self.bot.wait_until_ready()

    async def _catch_up(self):
        """봇 시작 시 놓친 스케줄 작업을 보충 실행."""
        now = datetime.now(KST)
        game_date = get_game_date(now)
        print(f"[Catch-up] start at {now.strftime('%H:%M')} KST (game_date={game_date})", flush=True)
        log.info("Catch-up check at %s (game_date=%s)", now.strftime("%H:%M"), game_date)

        try:
            await self._do_catch_up(now, game_date)
        except Exception:
            log.exception("Catch-up failed")
            print("[Catch-up] ERROR — see log above", flush=True)

        print("[Catch-up] done", flush=True)
        log.info("Catch-up complete")

    async def _do_catch_up(self, now: datetime, game_date):
        """catch-up 실제 로직."""
        # 1) 새벽 4시 지났으면: 전날 만료 처리
        if now.hour >= DAY_BOUNDARY_HOUR:
            with get_session() as session:
                yesterday = game_date - timedelta(days=1)
                expire_pending_quests(session, yesterday)
                users = session.query(User).filter_by(status="active").all()
                for user in users:
                    update_streak(session, user, yesterday)
            print("[Catch-up] expire task done", flush=True)

        # 2) 아침 8시 지났으면: 오늘 퀘스트 미발송 유저에게 발송
        if now.hour >= MORNING_QUEST_HOUR:
            quest_cog = self.bot.get_cog("QuestUICog")
            if quest_cog:
                with get_session() as session:
                    users = session.query(User).filter_by(status="active").all()
                    no_quest_ids = []
                    for user in users:
                        has_quests = (
                            session.query(DailyQuest)
                            .filter_by(user_id=user.id, quest_date=game_date)
                            .first()
                        )
                        if not has_quests:
                            no_quest_ids.append(user.discord_id)

                print(f"[Catch-up] quest catch-up: {len(no_quest_ids)} users need quests", flush=True)
                for discord_id in no_quest_ids:
                    print(f"[Catch-up] sending quests to {discord_id}", flush=True)
                    await quest_cog.send_daily_quests(discord_id, skip_flow=True)
            else:
                print("[Catch-up] WARNING: QuestUICog not found", flush=True)

        # 3) 저녁 9시 지났으면: 일일 리포트 미발송 유저에게 발송
        if now.hour >= EVENING_REPORT_HOUR:
            with get_session() as session:
                users = session.query(User).filter_by(status="active").all()
                for user in users:
                    existing = (
                        session.query(DailyReport)
                        .filter_by(user_id=user.id, report_date=game_date)
                        .first()
                    )
                    if existing:
                        continue
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
                        log.info("Catch-up: daily report sent to %s", user.discord_id)
                    except discord.Forbidden:
                        pass

            # 4) 일요일이면: 주간 리포트
            if game_date.weekday() == WEEKLY_REPORT_DAY:
                with get_session() as session:
                    week_start = game_date - timedelta(days=6)
                    week_end = game_date
                    users = session.query(User).filter_by(status="active").all()
                    for user in users:
                        existing = (
                            session.query(WeeklyReport)
                            .filter_by(user_id=user.id, week_start=week_start, week_end=week_end)
                            .first()
                        )
                        if existing:
                            continue
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
                            log.info("Catch-up: weekly report sent to %s", user.discord_id)
                        except discord.Forbidden:
                            pass

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._catchup_done:
            self._catchup_done = True
            print("[Scheduler] on_ready → running catch-up", flush=True)
            await self._catch_up()
            # 디버그: 각 task의 다음 실행 예정 시각 출력
            for name, task in [
                ("expire_task", self.expire_task),
                ("morning_task", self.morning_task),
                ("evening_task", self.evening_task),
            ]:
                nxt = task.next_iteration
                print(f"[Scheduler] {name} next_iteration={nxt}", flush=True)

    @expire_task.before_loop
    @morning_task.before_loop
    @evening_task.before_loop
    @weekly_task.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
