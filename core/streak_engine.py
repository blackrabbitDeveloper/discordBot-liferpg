from datetime import date, timedelta
from sqlalchemy.orm import Session
from core.models import User, DailyQuest


def _has_completed_quest(session: Session, user: User, game_date: date) -> bool:
    return (
        session.query(DailyQuest)
        .filter(
            DailyQuest.user_id == user.id,
            DailyQuest.quest_date == game_date,
            DailyQuest.state == "COMPLETED",
        )
        .first()
        is not None
    )


def _count_consecutive_misses(session: Session, user: User, game_date: date) -> int:
    """최근 연속 미완료 일수를 계산. 어제부터 역순으로 체크."""
    misses = 0
    for days_ago in range(1, 4):  # FIX: was range(0, 3)
        check_date = game_date - timedelta(days=days_ago)
        has_quests = (
            session.query(DailyQuest)
            .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == check_date)
            .first() is not None
        )
        if has_quests and not _has_completed_quest(session, user, check_date):
            misses += 1
        else:
            break
    return misses


# Track last streak update date to prevent double-counting
_streak_updated_dates: dict[int, date] = {}


def update_streak(session: Session, user: User, game_date: date) -> dict:
    """스트릭 업데이트. 같은 날짜에 여러 번 호출해도 1번만 적용."""
    # Idempotency check: 오늘 이미 업데이트했으면 현재 값 반환
    if _streak_updated_dates.get(user.id) == game_date:
        return {"streak": user.streak, "status": "already_updated"}

    completed = _has_completed_quest(session, user, game_date)

    if completed:
        user.streak += 1
        user.streak_protected = False
        status = "increased"
    elif not user.streak_protected:
        user.streak_protected = True
        status = "protected"
    else:
        consecutive = _count_consecutive_misses(session, user, game_date)
        if consecutive >= 3:
            user.streak = 0
            status = "reset"
        else:
            user.streak = max(0, user.streak - 1)
            status = "decreased"

    _streak_updated_dates[user.id] = game_date
    session.commit()
    return {"streak": user.streak, "status": status}
