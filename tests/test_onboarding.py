import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats
from core.onboarding import (
    GOAL_CATEGORIES,
    TIME_BUDGETS,
    ENERGY_LEVELS,
    DIFFICULTY_LEVELS,
    create_user,
    reset_user,
    is_onboarded,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_constants():
    assert len(GOAL_CATEGORIES) == 7
    assert "건강" in GOAL_CATEGORIES
    assert len(TIME_BUDGETS) == 3
    assert len(ENERGY_LEVELS) == 3
    assert len(DIFFICULTY_LEVELS) == 3


def test_create_user(db_session):
    user = create_user(
        db_session,
        discord_id="900",
        nickname="온보딩유저",
        goal_category="건강",
        goal_text="매일 운동",
        time_budget="medium",
        energy_preference="normal",
        difficulty_preference="moderate",
    )
    assert user.id is not None
    assert user.level == 1
    assert user.stats is not None
    assert user.stats.health == 0


def test_create_user_duplicate_resets(db_session):
    create_user(db_session, "900", "유저A", "건강", "운동", "medium", "normal", "moderate")
    user2 = create_user(db_session, "900", "유저B", "공부", "독서", "long", "high", "hard")
    assert user2.nickname == "유저B"
    assert user2.goal_category == "공부"
    count = db_session.query(User).filter_by(discord_id="900").count()
    assert count == 1


def test_is_onboarded(db_session):
    assert is_onboarded(db_session, "900") is False
    create_user(db_session, "900", "유저", "건강", "운동", "medium", "normal", "moderate")
    assert is_onboarded(db_session, "900") is True


def test_reset_user(db_session):
    create_user(db_session, "900", "유저", "건강", "운동", "medium", "normal", "moderate")
    reset_user(db_session, "900")
    assert is_onboarded(db_session, "900") is False
