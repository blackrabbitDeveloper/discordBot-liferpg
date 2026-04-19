from datetime import datetime, date, time, timedelta, timezone

from config import DAY_BOUNDARY_HOUR

KST = timezone(timedelta(hours=9))
_BOUNDARY = time(DAY_BOUNDARY_HOUR, 0)


def get_game_date(now: datetime | None = None) -> date:
    """새벽 4시 KST 기준 게임 날짜 반환. 4시 이전이면 전날로 취급."""
    if now is None:
        now = datetime.now(KST)
    if now.time() < _BOUNDARY:
        return (now - timedelta(days=1)).date()
    return now.date()
