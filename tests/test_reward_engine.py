import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats
from core.reward_engine import apply_reward, check_level_up


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user_with_stats(db_session):
    user = User(
        discord_id="100", nickname="보상테스트",
        goal_category="건강", goal_text="운동",
    )
    db_session.add(user)
    db_session.commit()
    stats = UserStats(user_id=user.id)
    db_session.add(stats)
    db_session.commit()
    return user


def test_apply_reward_easy(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["xp_gained"] == 5
    assert result["stat_gained"] == 1
    assert result["stat_type"] == "health"
    assert user_with_stats.xp == 5
    assert user_with_stats.stats.health == 1


def test_apply_reward_normal(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "normal", "focus")
    assert result["xp_gained"] == 10
    assert result["stat_gained"] == 2
    assert user_with_stats.stats.focus == 2


def test_apply_reward_hard(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "hard", "execution")
    assert result["xp_gained"] == 20
    assert result["stat_gained"] == 3
    assert user_with_stats.stats.execution == 3


def test_level_up_at_100xp(db_session, user_with_stats):
    user_with_stats.xp = 95
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["leveled_up"] is True
    assert result["new_level"] == 2
    assert user_with_stats.level == 2
    assert user_with_stats.xp == 0


def test_level_up_with_overflow(db_session, user_with_stats):
    user_with_stats.xp = 95
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "normal", "focus")
    assert result["leveled_up"] is True
    assert user_with_stats.level == 2
    assert user_with_stats.xp == 5


def test_no_level_up(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["leveled_up"] is False
    assert user_with_stats.level == 1


def test_level2_needs_200xp(db_session, user_with_stats):
    user_with_stats.level = 2
    user_with_stats.xp = 190
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "normal", "knowledge")
    assert result["leveled_up"] is True
    assert user_with_stats.level == 3
    assert user_with_stats.xp == 0


def test_check_level_up_utility():
    assert check_level_up(100, 1) == (True, 2, 0)
    assert check_level_up(50, 1) == (False, 1, 50)
    assert check_level_up(250, 2) == (True, 3, 50)
