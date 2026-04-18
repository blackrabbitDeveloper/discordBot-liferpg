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
    """최근 연속 미완료 일수를 계산."""
    misses = 0
    for days_ago in range(0, 3):
        check_date = game_date - timedelta(days=days_ago)
        has_completed = _has_completed_quest(session, user, check_date)
        has_quests = (
            session.query(DailyQuest)
            .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == check_date)
            .first() is not None
        )
        if has_quests and not has_completed:
            misses += 1
        else:
            break
    return misses


def update_streak(session: Session, user: User, game_date: date) -> dict:
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

    session.commit()
    return {"streak": user.streak, "status": status}
