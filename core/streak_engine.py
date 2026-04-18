from datetime import date
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
        user.streak = max(0, user.streak - 1)
        status = "decreased"

    session.commit()
    return {"streak": user.streak, "status": status}
