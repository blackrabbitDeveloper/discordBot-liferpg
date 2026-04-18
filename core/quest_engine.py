import random
from datetime import date, datetime
from sqlalchemy.orm import Session
from core.models import User, DailyQuest, QuestLog
from core.quest_loader import filter_quests
from config import CATEGORY_STAT_MAP, DIFFICULTY_REWARDS


def generate_daily_quests(
    session: Session,
    user: User,
    quest_pool: dict[str, list[dict]],
    game_date: date,
) -> list[DailyQuest]:
    existing = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .all()
    )
    if existing:
        return existing

    filtered = filter_quests(
        quest_pool,
        category=user.goal_category,
        energy=user.energy_preference,
        time_budget=user.time_budget,
    )

    if len(filtered) < 3:
        all_filtered = filter_quests(
            quest_pool,
            energy=user.energy_preference,
            time_budget=user.time_budget,
        )
        for q in all_filtered:
            if q not in filtered:
                filtered.append(q)

    count = min(3, len(filtered))
    selected = random.sample(filtered, count)

    quests = []
    for q in selected:
        category = q["_category"]
        stat_type = CATEGORY_STAT_MAP.get(category, "health")
        reward = DIFFICULTY_REWARDS[q["difficulty"]]

        quest = DailyQuest(
            user_id=user.id,
            quest_date=game_date,
            category=category,
            title=q["title"],
            description=q["description"],
            estimated_minutes=q["estimated_minutes"],
            difficulty=q["difficulty"],
            reward_xp=reward["xp"],
            reward_stat_type=stat_type,
            reward_stat_value=reward["stat"],
        )
        session.add(quest)
        quests.append(quest)

    session.commit()
    return quests


def get_today_quests(
    session: Session, user: User, game_date: date
) -> list[DailyQuest]:
    return (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .all()
    )


def complete_quest(
    session: Session, user: User, quest_id: int, game_date: date
) -> dict:
    quest = session.get(DailyQuest, quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}
    if quest.quest_date != game_date:
        return {"success": False, "reason": "past_quest", "quest": quest}

    quest.state = "COMPLETED"
    quest.completed_at = datetime.utcnow()

    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="completed",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}


def skip_quest(session: Session, user: User, quest_id: int) -> dict:
    quest = session.get(DailyQuest, quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}

    quest.state = "SKIPPED"
    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="skipped",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}


def expire_pending_quests(session: Session, game_date: date) -> int:
    pending = (
        session.query(DailyQuest)
        .filter(
            DailyQuest.quest_date == game_date,
            DailyQuest.state == "PENDING",
        )
        .all()
    )
    for quest in pending:
        quest.state = "EXPIRED"
        log = QuestLog(
            quest_id=quest.id,
            user_id=quest.user_id,
            action_type="expired",
        )
        session.add(log)

    session.commit()
    return len(pending)


def late_log_quest(session: Session, user: User, quest_id: int) -> dict:
    quest = session.get(DailyQuest, quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}

    quest.state = "LATE_LOGGED"
    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="late_logged",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}
