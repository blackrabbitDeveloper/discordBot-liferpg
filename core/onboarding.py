from sqlalchemy.orm import Session
from core.models import User, UserStats, DailyQuest, QuestLog, DailyReport, WeeklyReport
from core.activity_logger import log_activity

GOAL_CATEGORIES = ["건강", "집중", "일/커리어", "공부", "창작", "돈관리", "정리/생활"]

TIME_BUDGETS = {
    "short": "10분 이하",
    "medium": "10~30분",
    "long": "30분 이상",
}

ENERGY_LEVELS = {
    "low": "낮음",
    "normal": "보통",
    "high": "높음",
}

DIFFICULTY_LEVELS = {
    "light": "아주 가볍게",
    "moderate": "적당히",
    "hard": "조금 빡세게",
}


def is_onboarded(session: Session, discord_id: str) -> bool:
    return session.query(User).filter_by(discord_id=discord_id).first() is not None


def create_user(
    session: Session,
    discord_id: str,
    nickname: str,
    goal_category: str,
    goal_text: str,
    time_budget: str,
    energy_preference: str,
    difficulty_preference: str,
) -> User:
    existing = session.query(User).filter_by(discord_id=discord_id).first()
    if existing:
        if existing.stats:
            session.delete(existing.stats)
        existing.nickname = nickname
        existing.goal_category = goal_category
        existing.goal_text = goal_text
        existing.time_budget = time_budget
        existing.energy_preference = energy_preference
        existing.difficulty_preference = difficulty_preference
        existing.level = 1
        existing.xp = 0
        existing.streak = 0
        existing.streak_protected = False
        existing.status = "active"
        session.commit()

        stats = UserStats(user_id=existing.id)
        session.add(stats)
        session.commit()
        return existing

    user = User(
        discord_id=discord_id,
        nickname=nickname,
        goal_category=goal_category,
        goal_text=goal_text,
        time_budget=time_budget,
        energy_preference=energy_preference,
        difficulty_preference=difficulty_preference,
    )
    session.add(user)
    session.commit()

    stats = UserStats(user_id=user.id)
    session.add(stats)
    session.commit()

    log_activity(session, "onboarding_complete", "onboarding", user_id=user.id, detail={
        "goal_category": goal_category,
        "goal_text": goal_text,
        "time_budget": time_budget,
        "energy_preference": energy_preference,
        "difficulty_preference": difficulty_preference,
    })

    return user


def reset_user(session: Session, discord_id: str) -> bool:
    user = session.query(User).filter_by(discord_id=discord_id).first()
    if not user:
        return False
    log_activity(session, "onboarding_reset", "onboarding", user_id=None, detail={
        "discord_id": discord_id,
        "prev_level": user.level,
        "prev_streak": user.streak,
    })
    # QuestLog는 DailyQuest cascade로 자동 삭제
    # DailyReport, WeeklyReport는 User cascade로 자동 삭제
    session.delete(user)
    session.commit()
    return True
