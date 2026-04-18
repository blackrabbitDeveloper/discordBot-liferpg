from datetime import datetime, date
from core.time_utils import get_game_date


def test_after_4am_returns_today():
    now = datetime(2026, 4, 19, 10, 0)
    assert get_game_date(now) == date(2026, 4, 19)


def test_before_4am_returns_yesterday():
    now = datetime(2026, 4, 19, 3, 59)
    assert get_game_date(now) == date(2026, 4, 18)


def test_exactly_4am_returns_today():
    now = datetime(2026, 4, 19, 4, 0)
    assert get_game_date(now) == date(2026, 4, 19)


def test_midnight_returns_yesterday():
    now = datetime(2026, 4, 19, 0, 0)
    assert get_game_date(now) == date(2026, 4, 18)


def test_just_before_midnight_returns_today():
    now = datetime(2026, 4, 19, 23, 59)
    assert get_game_date(now) == date(2026, 4, 19)
