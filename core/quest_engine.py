import random
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from core.models import User, DailyQuest, QuestLog
from core.quest_loader import filter_quests
from config import CATEGORY_STAT_MAP, DIFFICULTY_REWARDS


def _get_recent_completion_rate(session: Session, user: User, game_date: date) -> float:
    """최근 3일 완료율 계산. 퀘스트가 없으면 1.0 반환."""
    total = 0
    completed = 0
    for days_ago in range(1, 4):
        past_date = game_date - timedelta(days=days_ago)
        past_quests = (
            session.query(DailyQuest)
            .filter(
                DailyQuest.user_id == user.id,
                DailyQuest.quest_date == past_date,
            )
            .all()
        )
        for pq in past_quests:
            total += 1
            if pq.state == "COMPLETED":
                completed += 1
    if total == 0:
        return 1.0
    return completed / total


def generate_daily_quests(
    session: Session,
    user: User,
    quest_pool: dict[str, list[dict]],
    game_date: date,
    energy_override: str | None = None,
    category_override: str | None = None,
) -> list[DailyQuest]:
    existing = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .all()
    )
    if existing:
        return existing

    energy = energy_override or user.energy_preference
    category = category_override or user.goal_category

    if energy_override == "low":
        difficulty = "light"
    else:
        difficulty = user.difficulty_preference

    filtered = filter_quests(
        quest_pool,
        category=category,
        energy=energy,
        time_budget=user.time_budget,
        difficulty=difficulty,
    )

    if len(filtered) < 3:
        all_filtered = filter_quests(
            quest_pool,
            energy=energy,
            time_budget=user.time_budget,
            difficulty=difficulty,
        )
        for q in all_filtered:
            if q not in filtered:
                filtered.append(q)

    # 최근 3일 완료 퀘스트 제외
    recent_titles = set()
    for days_ago in range(1, 4):
        past_date = game_date - timedelta(days=days_ago)
        past_quests = (
            session.query(DailyQuest)
            .filter(
                DailyQuest.user_id == user.id,
                DailyQuest.quest_date == past_date,
                DailyQuest.state == "COMPLETED",
            )
            .all()
        )
        for pq in past_quests:
            recent_titles.add(pq.title)

    filtered = [q for q in filtered if q["title"] not in recent_titles]

    # 최근 완료율 낮으면 easy 위주로
    completion_rate = _get_recent_completion_rate(session, user, game_date)
    if completion_rate < 0.5 and filtered:
        easy_quests = [q for q in filtered if q["difficulty"] == "easy"]
        if len(easy_quests) >= 3:
            filtered = easy_quests

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
    if quest.state != "PENDING":
        return {"success": False, "reason": "already_processed"}

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


def replace_quest(
    session: Session,
    user: User,
    quest_id: int,
    quest_pool: dict[str, list[dict]],
    game_date: date,
) -> dict:
    """PENDING 퀘스트를 다른 퀘스트로 교체. 오늘 날짜만 가능."""
    quest = session.get(DailyQuest, quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}
    if quest.quest_date != game_date:
        return {"success": False, "reason": "past_quest"}
    if quest.state != "PENDING":
        return {"success": False, "reason": "not_pending"}

    MAX_REPLACE_PER_DAY = 3
    # 오늘 해당 유저의 전체 교체 횟수 확인
    today_quests = get_today_quests(session, user, game_date)
    total_replaces = sum(q.replace_count for q in today_quests)
    if total_replaces >= MAX_REPLACE_PER_DAY:
        return {"success": False, "reason": "replace_limit"}

    # 오늘 이미 있는 퀘스트 제목 수집 (중복 방지)
    existing_titles = {q.title for q in today_quests}

    # 후보 필터링
    filtered = filter_quests(
        quest_pool,
        category=user.goal_category,
        energy=user.energy_preference,
        time_budget=user.time_budget,
        difficulty=user.difficulty_preference,
    )
    if len(filtered) < 2:
        filtered = filter_quests(
            quest_pool,
            energy=user.energy_preference,
            time_budget=user.time_budget,
            difficulty=user.difficulty_preference,
        )

    candidates = [q for q in filtered if q["title"] not in existing_titles]
    if not candidates:
        return {"success": False, "reason": "no_alternatives"}

    new_q = random.choice(candidates)
    category = new_q["_category"]
    stat_type = CATEGORY_STAT_MAP.get(category, "health")
    reward = DIFFICULTY_REWARDS[new_q["difficulty"]]

    # 기존 퀘스트 업데이트
    quest.category = category
    quest.title = new_q["title"]
    quest.description = new_q["description"]
    quest.estimated_minutes = new_q["estimated_minutes"]
    quest.difficulty = new_q["difficulty"]
    quest.reward_xp = reward["xp"]
    quest.reward_stat_type = stat_type
    quest.reward_stat_value = reward["stat"]
    quest.replace_count += 1

    session.commit()
    return {"success": True, "quest": quest}


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
