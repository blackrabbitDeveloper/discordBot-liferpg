import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest, QuestLog
from core.quest_engine import (
    generate_daily_quests,
    complete_quest,
    skip_quest,
    replace_quest,
    expire_pending_quests,
    late_log_quest,
    get_today_quests,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db_session):
    u = User(
        discord_id="700", nickname="퀘스트유저",
        goal_category="건강", goal_text="운동",
        time_budget="medium", energy_preference="normal",
        difficulty_preference="moderate",
    )
    db_session.add(u)
    db_session.commit()
    stats = UserStats(user_id=u.id)
    db_session.add(stats)
    db_session.commit()
    return u


@pytest.fixture
def sample_quests():
    return {
        "건강": [
            {"title": "물 마시기", "description": "물 한 잔", "estimated_minutes": 1,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "건강"},
            {"title": "스트레칭", "description": "전신 스트레칭", "estimated_minutes": 5,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "건강"},
            {"title": "10분 걷기", "description": "동네 걷기", "estimated_minutes": 10,
             "difficulty": "normal", "energy": ["normal", "high"],
             "time_budget": ["medium", "long"], "_category": "건강"},
            {"title": "유산소", "description": "달리기", "estimated_minutes": 20,
             "difficulty": "hard", "energy": ["high"],
             "time_budget": ["long"], "_category": "건강"},
        ],
        "회복": [
            {"title": "심호흡", "description": "3분 호흡", "estimated_minutes": 3,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "회복"},
        ],
    }


def test_generate_daily_quests_returns_3(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    assert len(quests) == 3


def test_generate_daily_quests_saves_to_db(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    saved = db_session.query(DailyQuest).filter_by(user_id=user.id).all()
    assert len(saved) == 3
    assert all(q.state == "PENDING" for q in saved)


def test_generate_daily_quests_no_duplicates_same_day(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    quests2 = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    assert len(quests2) == 3


def test_complete_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    result = complete_quest(db_session, user, quests[0].id, date(2026, 4, 19))
    assert result["success"] is True
    assert quests[0].state == "COMPLETED"
    assert quests[0].completed_at is not None
    log = db_session.query(QuestLog).filter_by(quest_id=quests[0].id).first()
    assert log.action_type == "completed"


def test_complete_quest_past_date_rejected(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    result = complete_quest(db_session, user, quests[0].id, date(2026, 4, 19))
    assert result["success"] is False
    assert result["reason"] == "past_quest"


def test_skip_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    result = skip_quest(db_session, user, quests[0].id)
    assert result["success"] is True
    assert quests[0].state == "SKIPPED"


def test_expire_pending_quests(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    count = expire_pending_quests(db_session, date(2026, 4, 18))
    assert count > 0
    expired = db_session.query(DailyQuest).filter_by(state="EXPIRED").all()
    assert len(expired) == 3


def test_late_log_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    expire_pending_quests(db_session, date(2026, 4, 18))
    result = late_log_quest(db_session, user, quests[0].id)
    assert result["success"] is True
    assert quests[0].state == "LATE_LOGGED"


def test_get_today_quests(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    today = get_today_quests(db_session, user, date(2026, 4, 19))
    assert len(today) == 3


def test_replace_quest(db_session, user, sample_quests):
    # 후보가 충분하도록 추가
    sample_quests["건강"].append(
        {"title": "계단 오르기", "description": "계단 2층", "estimated_minutes": 5,
         "difficulty": "normal", "energy": ["normal", "high"],
         "time_budget": ["medium", "long"], "_category": "건강"},
    )
    sample_quests["건강"].append(
        {"title": "팔굽혀펴기", "description": "10회", "estimated_minutes": 3,
         "difficulty": "easy", "energy": ["normal", "high"],
         "time_budget": ["short", "medium", "long"], "_category": "건강"},
    )
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    old_title = quests[0].title
    result = replace_quest(db_session, user, quests[0].id, sample_quests, date(2026, 4, 19))
    assert result["success"] is True
    assert result["quest"].title != old_title


def test_replace_quest_not_pending(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    complete_quest(db_session, user, quests[0].id, date(2026, 4, 19))
    result = replace_quest(db_session, user, quests[0].id, sample_quests, date(2026, 4, 19))
    assert result["success"] is False
    assert result["reason"] == "not_pending"


def test_replace_quest_past_date(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    result = replace_quest(db_session, user, quests[0].id, sample_quests, date(2026, 4, 19))
    assert result["success"] is False
    assert result["reason"] == "past_quest"
