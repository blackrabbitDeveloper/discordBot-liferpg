import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest, DailyReport, WeeklyReport
from core.report_engine import generate_daily_report, generate_weekly_report


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db_session):
    u = User(
        discord_id="800", nickname="리포트유저",
        goal_category="건강", goal_text="운동",
        level=3, xp=50, streak=5,
    )
    db_session.add(u)
    db_session.commit()
    stats = UserStats(user_id=u.id, health=10, focus=5, execution=3, knowledge=2, finance=1)
    db_session.add(stats)
    db_session.commit()
    return u


def _add_quest(session, user, quest_date, state, stat_type="health", stat_value=1):
    q = DailyQuest(
        user_id=user.id, quest_date=quest_date, category="건강",
        title="테스트", description="", estimated_minutes=5,
        difficulty="easy", reward_xp=5, reward_stat_type=stat_type,
        reward_stat_value=stat_value, state=state,
    )
    session.add(q)
    session.commit()
    return q


def test_daily_report_counts(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED")
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED", "focus", 2)
    _add_quest(db_session, user, date(2026, 4, 19), "SKIPPED")

    report = generate_daily_report(db_session, user, date(2026, 4, 19))
    assert report.completed_count == 2
    assert report.skipped_count == 1
    assert report.expired_count == 0


def test_daily_report_main_growth_stat(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED", "focus", 2)
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED", "health", 1)

    report = generate_daily_report(db_session, user, date(2026, 4, 19))
    assert report.main_growth_stat == "focus"


def test_daily_report_saved_to_db(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 19), "COMPLETED")
    generate_daily_report(db_session, user, date(2026, 4, 19))

    saved = db_session.query(DailyReport).filter_by(user_id=user.id).first()
    assert saved is not None
    assert saved.report_date == date(2026, 4, 19)


def test_weekly_report(db_session, user):
    for day_offset in range(5):
        d = date(2026, 4, 13 + day_offset)
        _add_quest(db_session, user, d, "COMPLETED")
        _add_quest(db_session, user, d, "COMPLETED", "focus", 2)
        _add_quest(db_session, user, d, "EXPIRED")

    report = generate_weekly_report(
        db_session, user,
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
    )
    assert report is not None
    assert 60 < report.completion_rate < 70
    assert report.best_stat is not None


def test_weekly_report_saved_to_db(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 13), "COMPLETED")

    generate_weekly_report(db_session, user, date(2026, 4, 13), date(2026, 4, 19))

    saved = db_session.query(WeeklyReport).filter_by(user_id=user.id).first()
    assert saved is not None
