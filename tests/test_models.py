# tests/test_models.py
import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest, QuestLog, DailyReport, WeeklyReport


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_user(db_session):
    user = User(
        discord_id="123456",
        nickname="테스터",
        goal_category="건강",
        goal_text="매일 운동하기",
        time_budget="medium",
        energy_preference="normal",
        difficulty_preference="moderate",
    )
    db_session.add(user)
    db_session.commit()

    saved = db_session.query(User).filter_by(discord_id="123456").first()
    assert saved is not None
    assert saved.nickname == "테스터"
    assert saved.level == 1
    assert saved.xp == 0
    assert saved.streak == 0
    assert saved.streak_protected is False
    assert saved.status == "active"


def test_create_user_stats(db_session):
    user = User(discord_id="111", nickname="유저1", goal_category="건강", goal_text="운동")
    db_session.add(user)
    db_session.commit()

    stats = UserStats(user_id=user.id)
    db_session.add(stats)
    db_session.commit()

    saved = db_session.query(UserStats).filter_by(user_id=user.id).first()
    assert saved.health == 0
    assert saved.focus == 0
    assert saved.execution == 0
    assert saved.knowledge == 0
    assert saved.finance == 0


def test_create_daily_quest(db_session):
    user = User(discord_id="222", nickname="유저2", goal_category="집중", goal_text="공부")
    db_session.add(user)
    db_session.commit()

    quest = DailyQuest(
        user_id=user.id,
        quest_date=date(2026, 4, 19),
        category="집중",
        title="25분 집중 작업",
        description="타이머를 맞추고 한 가지 일에 집중하세요",
        estimated_minutes=25,
        difficulty="normal",
        reward_xp=10,
        reward_stat_type="focus",
        reward_stat_value=2,
    )
    db_session.add(quest)
    db_session.commit()

    saved = db_session.query(DailyQuest).filter_by(user_id=user.id).first()
    assert saved.state == "PENDING"
    assert saved.title == "25분 집중 작업"
    assert saved.completed_at is None


def test_create_quest_log(db_session):
    user = User(discord_id="333", nickname="유저3", goal_category="건강", goal_text="운동")
    db_session.add(user)
    db_session.commit()

    quest = DailyQuest(
        user_id=user.id, quest_date=date(2026, 4, 19),
        category="건강", title="스트레칭", description="테스트",
        estimated_minutes=5, difficulty="easy",
        reward_xp=5, reward_stat_type="health", reward_stat_value=1,
    )
    db_session.add(quest)
    db_session.commit()

    log = QuestLog(
        quest_id=quest.id, user_id=user.id,
        action_type="completed",
    )
    db_session.add(log)
    db_session.commit()

    saved = db_session.query(QuestLog).filter_by(quest_id=quest.id).first()
    assert saved.action_type == "completed"


def test_user_stats_relationship(db_session):
    user = User(discord_id="444", nickname="유저4", goal_category="공부", goal_text="독서")
    db_session.add(user)
    db_session.commit()

    stats = UserStats(user_id=user.id, knowledge=5)
    db_session.add(stats)
    db_session.commit()

    assert user.stats.knowledge == 5
