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


def _is_rest_day(session: Session, user: User, game_date: date) -> bool:
    """해당 날짜에 퀘스트가 하나도 없으면 쉬는 날로 간주."""
    has_quests = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .first() is not None
    )
    return not has_quests


def _count_consecutive_misses(session: Session, user: User, game_date: date) -> int:
    """최근 연속 미완료 일수를 계산. 어제부터 역순으로 체크."""
    misses = 0
    for days_ago in range(1, 4):
        check_date = game_date - timedelta(days=days_ago)
        has_quests = (
            session.query(DailyQuest)
            .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == check_date)
            .first() is not None
        )
        if not has_quests:
            continue  # 쉬는 날은 건너뜀 (미스로 카운트 안 함)
        if not _has_completed_quest(session, user, check_date):
            misses += 1
        else:
            break
    return misses


def update_streak(session: Session, user: User, game_date: date) -> dict:
    """스트릭 업데이트. 같은 날짜에 여러 번 호출해도 1번만 적용."""
    # DB 기반 멱등성 체크
    if user.last_streak_date == game_date:
        return {"streak": user.streak, "status": "already_updated"}

    # 쉬는 날 (퀘스트 없음) → 스트릭 유지, 변경 없음
    if _is_rest_day(session, user, game_date):
        user.last_streak_date = game_date
        session.commit()
        return {"streak": user.streak, "status": "resting"}

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

    user.last_streak_date = game_date
    session.commit()
    return {"streak": user.streak, "status": status}
