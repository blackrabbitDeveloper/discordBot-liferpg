from datetime import datetime, date, timezone, timedelta
from core.time_utils import get_game_date, KST


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


def test_utc_server_morning_8am_kst():
    """Railway(UTC) 서버에서 KST 8am 발동 시 올바른 게임 날짜 반환.
    KST 4/19 8:00 = UTC 4/18 23:00 → 게임 날짜는 4/19이어야 함."""
    utc_now = datetime(2026, 4, 18, 23, 0, tzinfo=timezone.utc)
    kst_now = utc_now.astimezone(KST)  # 4/19 8:00 KST
    assert get_game_date(kst_now) == date(2026, 4, 19)


def test_utc_server_expire_4am_kst():
    """Railway(UTC) 서버에서 KST 4am 발동 시 올바른 게임 날짜 반환.
    KST 4/19 4:00 = UTC 4/18 19:00 → 게임 날짜는 4/19이어야 함."""
    utc_now = datetime(2026, 4, 18, 19, 0, tzinfo=timezone.utc)
    kst_now = utc_now.astimezone(KST)  # 4/19 4:00 KST
    assert get_game_date(kst_now) == date(2026, 4, 19)
