# console/adapter.py
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from core.models import Base, User, DailyQuest
from core.database import get_session, init_db, get_engine
from core.onboarding import (
    GOAL_CATEGORIES, TIME_BUDGETS, ENERGY_LEVELS, DIFFICULTY_LEVELS,
    create_user, is_onboarded, reset_user,
)
from core.quest_engine import (
    generate_daily_quests, complete_quest, skip_quest, replace_quest,
    expire_pending_quests, get_today_quests, late_log_quest,
)
from core.quest_loader import load_quests
from core.reward_engine import apply_reward
from core.streak_engine import update_streak
from core.report_engine import generate_daily_report, generate_weekly_report
from core.time_utils import get_game_date
from core.activity_logger import log_activity, get_logs
from core.analytics import generate_analytics
from config import DATABASE_URL


class ConsoleAdapter:
    def __init__(self, db_url: str = DATABASE_URL, quest_yaml: str = "data/quests.yaml"):
        init_db(db_url)
        Base.metadata.create_all(get_engine())
        self.session = get_session()
        self.quest_pool = load_quests(quest_yaml)
        self._simulated_date: date | None = None
        self._discord_id = "console_user"
        self._user: User | None = None

    @property
    def game_date(self) -> date:
        if self._simulated_date:
            return self._simulated_date
        return get_game_date()

    def _load_user(self):
        self._user = (
            self.session.query(User)
            .filter_by(discord_id=self._discord_id)
            .first()
        )

    def run(self):
        print("=" * 50)
        print("  Life RPG Console")
        print("=" * 50)
        print(f"  게임 날짜: {self.game_date}")
        print("  'help'를 입력하면 명령어 목록을 볼 수 있어요")
        print("=" * 50)

        self._load_user()

        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n안녕히 가세요!")
                break

            if not cmd:
                continue

            parts = cmd.split()
            command = parts[0]
            args = parts[1:]

            if command == "quit":
                print("안녕히 가세요!")
                break
            elif command == "help":
                self._help()
            elif command == "start":
                self._start()
            elif command == "quests":
                self._quests()
            elif command == "complete":
                self._complete(args)
            elif command == "skip":
                self._skip(args)
            elif command == "replace":
                self._replace(args)
            elif command == "status":
                self._status()
            elif command == "report":
                self._report()
            elif command == "weekly":
                self._weekly()
            elif command == "next-day":
                self._next_day()
            elif command == "expire":
                self._expire()
            elif command == "reset":
                self._reset()
            elif command == "logs":
                self._logs()
            elif command == "analyze":
                self._analyze()
            else:
                print(f"알 수 없는 명령어: {command}. 'help'를 입력해보세요.")

    def _help(self):
        print("""
명령어 목록:
  start          온보딩 시작
  quests         오늘 퀘스트 보기
  complete <N>   N번 퀘스트 완료
  skip <N>       N번 퀘스트 건너뛰기
  replace <N>    N번 퀘스트 다른 걸로 교체
  status         현재 상태 확인
  report         일일 리포트 보기
  weekly         주간 리포트 보기
  next-day       다음 날로 이동 (테스트용)
  expire         만료 처리 실행 (테스트용)
  reset          데이터 초기화
  logs           최근 활동 로그 보기
  analyze        AI 분석용 데이터 출력
  quit           종료
""")

    def _start(self):
        if self._user:
            print("이미 온보딩을 완료했어요. 'reset' 후 다시 시작할 수 있어요.")
            return

        print("\n모험을 시작할게요!\n")

        print("가장 바꾸고 싶은 영역을 선택하세요:")
        for i, cat in enumerate(GOAL_CATEGORIES, 1):
            print(f"  {i}. {cat}")
        choice = self._get_choice(len(GOAL_CATEGORIES))
        goal_category = GOAL_CATEGORIES[choice - 1]

        print(f"\n'{goal_category}' 영역에서 이루고 싶은 목표를 입력하세요:")
        goal_text = input("> ").strip()
        if not goal_text:
            goal_text = f"{goal_category} 개선하기"

        print("\n하루 여유 시간은 얼마나 되나요?")
        budget_keys = list(TIME_BUDGETS.keys())
        for i, (key, label) in enumerate(TIME_BUDGETS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(budget_keys))
        time_budget = budget_keys[choice - 1]

        print("\n현재 에너지 상태는?")
        energy_keys = list(ENERGY_LEVELS.keys())
        for i, (key, label) in enumerate(ENERGY_LEVELS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(energy_keys))
        energy_preference = energy_keys[choice - 1]

        print("\n원하는 플레이 강도는?")
        diff_keys = list(DIFFICULTY_LEVELS.keys())
        for i, (key, label) in enumerate(DIFFICULTY_LEVELS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(diff_keys))
        difficulty_preference = diff_keys[choice - 1]

        self._user = create_user(
            self.session,
            discord_id=self._discord_id,
            nickname="모험가",
            goal_category=goal_category,
            goal_text=goal_text,
            time_budget=time_budget,
            energy_preference=energy_preference,
            difficulty_preference=difficulty_preference,
        )

        print(f"\n온보딩 완료! Lv.{self._user.level} 모험가로 시작합니다.")
        print("'quests'를 입력해서 첫 퀘스트를 받아보세요!")

    def _get_choice(self, max_val: int) -> int:
        while True:
            try:
                val = int(input("> ").strip())
                if 1 <= val <= max_val:
                    return val
            except ValueError:
                pass
            print(f"  1~{max_val} 사이의 숫자를 입력하세요.")

    def _quests(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        if not quests:
            # 오늘 플로우 선택
            print("\n오늘은 어떤 흐름으로 가볼까요?")
            print("  1. 이대로 할래요")
            print("  2. 오늘은 가볍게")
            print("  3. 회복 모드")
            print("  4. 오늘은 쉬어갈래요")
            choice = self._get_choice(4)

            if choice == 4:
                print("\n오늘은 쉬어가는 턴이에요. 내일 다시 이어가면 됩니다.")
                return

            # 플로우 선택 로그
            flow_names = {1: "normal", 2: "light", 3: "recovery", 4: "rest"}
            log_activity(self.session, "morning_flow_choice", "flow",
                        user_id=self._user.id, detail={"choice": flow_names[choice]})

            energy_override = None
            category_override = None
            if choice == 2:
                energy_override = "low"
            elif choice == 3:
                category_override = "회복"
                energy_override = "low"

            quests = generate_daily_quests(
                self.session, self._user, self.quest_pool, self.game_date,
                energy_override=energy_override,
                category_override=category_override,
            )

        print(f"\n오늘의 퀘스트 ({self.game_date})")
        print("-" * 40)
        for i, q in enumerate(quests, 1):
            state_icon = {"PENDING": " ", "COMPLETED": "V", "SKIPPED": "-", "EXPIRED": "X", "LATE_LOGGED": "~"}
            icon = state_icon.get(q.state, "?")
            print(f"  [{icon}] {i}. {q.title} ({q.difficulty}, {q.estimated_minutes}분)")
            print(f"      보상: +{q.reward_xp}XP, {q.reward_stat_type} +{q.reward_stat_value}")
        print("-" * 40)
        print("  'complete N', 'skip N', 'replace N'으로 처리하세요")

    def _complete(self, args):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        if not args:
            print("퀘스트 번호를 입력하세요. 예: complete 1")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        try:
            idx = int(args[0]) - 1
            quest = quests[idx]
        except (ValueError, IndexError):
            print("잘못된 번호입니다.")
            return

        result = complete_quest(self.session, self._user, quest.id, self.game_date)
        if result["success"]:
            reward = apply_reward(
                self.session, self._user, quest.difficulty, quest.reward_stat_type
            )
            print(f"\n퀘스트 완료! '{quest.title}'")
            print(f"  +{reward['xp_gained']} XP")
            print(f"  {reward['stat_type']} +{reward['stat_gained']}")
            if reward["leveled_up"]:
                print(f"  레벨 업! Lv.{reward['new_level']}!")
            update_streak(self.session, self._user, self.game_date)
            print(f"  스트릭: {self._user.streak}일")
        elif result.get("reason") == "past_quest":
            print("이 퀘스트는 과거 기록이에요. 회고 기록만 남길 수 있어요.")
            ans = input("  기록할까요? (y/n) > ").strip().lower()
            if ans == "y":
                late_log_quest(self.session, self._user, quest.id)
                print("  회고 기록으로 남겼어요.")

    def _skip(self, args):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        if not args:
            print("퀘스트 번호를 입력하세요. 예: skip 1")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        try:
            idx = int(args[0]) - 1
            quest = quests[idx]
        except (ValueError, IndexError):
            print("잘못된 번호입니다.")
            return

        skip_quest(self.session, self._user, quest.id)
        print(f"  '{quest.title}' 건너뛰었어요. 괜찮아요, 다른 걸 해봐요.")

    def _replace(self, args):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        if not args:
            print("퀘스트 번호를 입력하세요. 예: replace 1")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        try:
            idx = int(args[0]) - 1
            quest = quests[idx]
        except (ValueError, IndexError):
            print("잘못된 번호입니다.")
            return

        result = replace_quest(
            self.session, self._user, quest.id, self.quest_pool, self.game_date
        )
        if result["success"]:
            new_q = result["quest"]
            print(f"\n  퀘스트를 교체했어요!")
            print(f"  새 퀘스트: {new_q.title} ({new_q.difficulty}, {new_q.estimated_minutes}분)")
            print(f"  보상: +{new_q.reward_xp}XP, {new_q.reward_stat_type} +{new_q.reward_stat_value}")
        elif result.get("reason") == "no_alternatives":
            print("  바꿀 수 있는 다른 퀘스트가 없어요.")
        elif result.get("reason") == "not_pending":
            print("  이미 처리된 퀘스트예요.")

    def _status(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        self.session.refresh(self._user)
        u = self._user
        s = u.stats

        print(f"\n{'=' * 40}")
        print(f"  {u.nickname} | Lv.{u.level}")
        print(f"  XP: {u.xp} / {u.level * 100}")
        print(f"  스트릭: {u.streak}일")
        print(f"  목표: {u.goal_text} ({u.goal_category})")
        print(f"{'=' * 40}")
        print(f"  체력(Health):    {s.health}")
        print(f"  집중(Focus):     {s.focus}")
        print(f"  실행(Execution): {s.execution}")
        print(f"  지식(Knowledge): {s.knowledge}")
        print(f"  재정(Finance):   {s.finance}")
        print(f"{'=' * 40}")

    def _report(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        report = generate_daily_report(self.session, self._user, self.game_date)
        print(f"\n오늘 결과 ({report.report_date})")
        print("-" * 40)
        print(f"  완료: {report.completed_count}개")
        print(f"  건너뜀: {report.skipped_count}개")
        print(f"  만료: {report.expired_count}개")
        if report.main_growth_stat:
            print(f"  가장 성장한 영역: {report.main_growth_stat}")
        print(f"  스트릭: {self._user.streak}일")
        print(f"  오늘의 흐름: {report.summary_text}")

    def _weekly(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        today = self.game_date
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        report = generate_weekly_report(self.session, self._user, week_start, week_end)
        print(f"\n이번 주 요약 ({report.week_start} ~ {report.week_end})")
        print("-" * 40)
        print(f"  완료율: {report.completion_rate}%")
        if report.best_stat:
            print(f"  가장 성장한 영역: {report.best_stat}")
        if report.risk_pattern:
            print(f"  어려웠던 패턴: {report.risk_pattern}")
        print(f"  추천: {report.suggestion_text}")

    def _next_day(self):
        if self._simulated_date is None:
            self._simulated_date = self.game_date
        self._simulated_date += timedelta(days=1)
        print(f"\n다음 날로 이동했어요. 현재 게임 날짜: {self._simulated_date}")
        yesterday = self._simulated_date - timedelta(days=1)
        count = expire_pending_quests(self.session, yesterday)
        if count > 0:
            print(f"  어제 미완료 퀘스트 {count}개가 만료되었어요.")
        if self._user:
            update_streak(self.session, self._user, yesterday)

    def _expire(self):
        count = expire_pending_quests(self.session, self.game_date)
        print(f"  {self.game_date}의 PENDING 퀘스트 {count}개를 만료 처리했어요.")

    def _reset(self):
        if self._user:
            reset_user(self.session, self._discord_id)
            self._user = None
            self._simulated_date = None
            print("데이터를 초기화했어요. 'start'로 다시 시작할 수 있어요.")
        else:
            print("초기화할 데이터가 없어요.")

    def _logs(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        logs = get_logs(self.session, user_id=self._user.id, limit=20)
        print(f"\n최근 활동 로그 (최대 20건)")
        print("-" * 60)
        for l in logs:
            import json
            detail = json.loads(l.detail) if l.detail else {}
            detail_str = ", ".join(f"{k}={v}" for k, v in detail.items()) if detail else ""
            print(f"  [{l.created_at.strftime('%m/%d %H:%M')}] {l.category}/{l.action} {detail_str}")
        if not logs:
            print("  기록이 없어요.")
        print("-" * 60)

    def _analyze(self):
        import json
        data = generate_analytics(self.session, period_days=7)
        print(f"\n{'=' * 60}")
        print(f"  AI 분석 데이터 ({data['period']})")
        print(f"{'=' * 60}")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        print(f"{'=' * 60}")
        print("\n위 JSON을 AI에게 전달하면 리밸런싱/리뉴얼 제안을 받을 수 있습니다.")
