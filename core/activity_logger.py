# core/activity_logger.py
import json
from datetime import datetime
from sqlalchemy.orm import Session
from core.models import UserActivityLog


def log_activity(
    session: Session,
    action: str,
    category: str,
    user_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """사용자 행동을 기록한다."""
    log = UserActivityLog(
        user_id=user_id,
        action=action,
        category=category,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
    )
    session.add(log)
    session.flush()  # 호출자가 트랜잭션 관리 — commit은 호출자에서


def get_logs(
    session: Session,
    user_id: int | None = None,
    category: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[UserActivityLog]:
    """로그를 조회한다."""
    query = session.query(UserActivityLog)
    if user_id:
        query = query.filter(UserActivityLog.user_id == user_id)
    if category:
        query = query.filter(UserActivityLog.category == category)
    if action:
        query = query.filter(UserActivityLog.action == action)
    return query.order_by(UserActivityLog.created_at.desc()).limit(limit).all()
