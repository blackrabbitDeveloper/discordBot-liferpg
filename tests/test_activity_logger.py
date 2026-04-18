import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, UserActivityLog
from core.activity_logger import log_activity, get_logs


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db_session):
    u = User(discord_id="log_test", nickname="로그테스트", goal_category="건강", goal_text="운동")
    db_session.add(u)
    db_session.commit()
    stats = UserStats(user_id=u.id)
    db_session.add(stats)
    db_session.commit()
    return u


def test_log_activity(db_session, user):
    log_activity(db_session, "quest_completed", "quest", user_id=user.id, detail={
        "quest_id": 1, "title": "물 마시기", "category": "건강",
    })
    logs = db_session.query(UserActivityLog).all()
    assert len(logs) == 1
    assert logs[0].action == "quest_completed"
    assert logs[0].category == "quest"
    d = json.loads(logs[0].detail)
    assert d["title"] == "물 마시기"


def test_log_without_user(db_session):
    log_activity(db_session, "onboarding_start", "onboarding", detail={"discord_id": "123"})
    logs = db_session.query(UserActivityLog).all()
    assert len(logs) == 1
    assert logs[0].user_id is None


def test_get_logs_filtered(db_session, user):
    log_activity(db_session, "quest_completed", "quest", user_id=user.id)
    log_activity(db_session, "level_up", "growth", user_id=user.id)
    log_activity(db_session, "quest_skipped", "quest", user_id=user.id)

    quest_logs = get_logs(db_session, user_id=user.id, category="quest")
    assert len(quest_logs) == 2

    growth_logs = get_logs(db_session, user_id=user.id, category="growth")
    assert len(growth_logs) == 1
