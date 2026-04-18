import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest
from core.streak_engine import update_streak



@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db_session):
    u = User(discord_id="500", nickname="스트릭유저", goal_category="건강", goal_text="운동")
    db_session.add(u)
    db_session.commit()
    stats = UserStats(user_id=u.id)
    db_session.add(stats)
    db_session.commit()
    return u


def _add_quest(session, user, quest_date, state):
    q = DailyQuest(
        user_id=user.id, quest_date=quest_date, category="건강",
        title="테스트", description="", estimated_minutes=5,
        difficulty="easy", reward_xp=5, reward_stat_type="health",
        reward_stat_value=1, state=state,
    )
    session.add(q)
    session.commit()
    return q


def test_streak_increases_on_completion(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED")
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 1
    assert user.streak_protected is False


def test_streak_continues(db_session, user):
    user.streak = 3
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 20), "COMPLETED")
    update_streak(db_session, user, date(2026, 4, 20))
    assert user.streak == 4


def test_streak_protected_on_first_miss(db_session, user):
    user.streak = 5
    user.streak_protected = False
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 19), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 5
    assert user.streak_protected is True


def test_streak_decreases_on_second_miss(db_session, user):
    user.streak = 5
    user.streak_protected = True
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 20), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 20))
    assert user.streak == 4
    assert user.streak_protected is True


def test_streak_resets_at_zero(db_session, user):
    user.streak = 1
    user.streak_protected = True
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 20), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 20))
    assert user.streak == 0


def test_streak_recovery_clears_protection(db_session, user):
    user.streak = 3
    user.streak_protected = True
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 20), "COMPLETED")
    update_streak(db_session, user, date(2026, 4, 20))
    assert user.streak == 4
    assert user.streak_protected is False


def test_streak_resets_after_3_consecutive_misses(db_session, user):
    user.streak = 10
    user.streak_protected = True
    db_session.commit()
    # 3일 연속 미완료: game_date=2026-04-19, so range(1,4) checks Apr 18, 17, 16
    # Apr 19 must have a quest so it's not treated as a rest day
    _add_quest(db_session, user, date(2026, 4, 16), "EXPIRED")
    _add_quest(db_session, user, date(2026, 4, 17), "EXPIRED")
    _add_quest(db_session, user, date(2026, 4, 18), "EXPIRED")
    _add_quest(db_session, user, date(2026, 4, 19), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 0


def test_streak_idempotent(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED")
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 1
    # 같은 날 다시 호출해도 streak 변화 없음
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 1


def test_streak_preserved_on_rest_day(db_session, user):
    user.streak = 5
    db_session.commit()
    # 퀘스트가 없는 날 = 쉬는 날 → 스트릭 유지
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 5
