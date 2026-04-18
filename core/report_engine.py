from datetime import date
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from core.models import User, DailyQuest, DailyReport, WeeklyReport


def generate_daily_report(
    session: Session, user: User, report_date: date
) -> DailyReport:
    quests = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == report_date)
        .all()
    )

    completed = [q for q in quests if q.state == "COMPLETED"]
    skipped = [q for q in quests if q.state == "SKIPPED"]
    expired = [q for q in quests if q.state == "EXPIRED"]

    stat_gains = defaultdict(int)
    for q in completed:
        stat_gains[q.reward_stat_type] += q.reward_stat_value

    main_stat = max(stat_gains, key=stat_gains.get) if stat_gains else None

    total = len(quests)
    if total == 0:
        flow = "오늘은 퀘스트가 없었어요"
    elif len(completed) == total:
        flow = "완벽한 하루였어요!"
    elif len(completed) > 0:
        flow = "안정적인 흐름이에요"
    else:
        flow = "내일 다시 이어가면 돼요"

    report = DailyReport(
        user_id=user.id,
        report_date=report_date,
        completed_count=len(completed),
        skipped_count=len(skipped),
        expired_count=len(expired),
        main_growth_stat=main_stat,
        summary_text=flow,
    )
    session.add(report)
    session.commit()
    return report


def generate_weekly_report(
    session: Session,
    user: User,
    week_start: date,
    week_end: date,
) -> WeeklyReport:
    quests = (
        session.query(DailyQuest)
        .filter(
            DailyQuest.user_id == user.id,
            DailyQuest.quest_date >= week_start,
            DailyQuest.quest_date <= week_end,
        )
        .all()
    )

    total = len(quests)
    completed = [q for q in quests if q.state == "COMPLETED"]

    completion_rate = (len(completed) / total * 100) if total > 0 else 0.0

    stat_gains = defaultdict(int)
    for q in completed:
        stat_gains[q.reward_stat_type] += q.reward_stat_value

    best_stat = max(stat_gains, key=stat_gains.get) if stat_gains else None

    expired_days = Counter()
    for q in quests:
        if q.state in ("EXPIRED", "SKIPPED"):
            expired_days[q.quest_date.strftime("%A")] += 1

    risk_pattern = None
    if expired_days:
        worst_day = max(expired_days, key=expired_days.get)
        risk_pattern = worst_day

    if completion_rate >= 80:
        suggestion = "좋은 흐름이에요. 난이도를 조금 올려봐도 좋겠어요"
    elif completion_rate >= 50:
        suggestion = "안정적이에요. 비슷한 강도로 이어가세요"
    else:
        suggestion = "가벼운 퀘스트 비중을 늘려보는 건 어떨까요"

    report = WeeklyReport(
        user_id=user.id,
        week_start=week_start,
        week_end=week_end,
        completion_rate=round(completion_rate, 1),
        best_stat=best_stat,
        risk_pattern=risk_pattern,
        suggestion_text=suggestion,
    )
    session.add(report)
    session.commit()
    return report
