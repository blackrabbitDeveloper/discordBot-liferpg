from sqlalchemy.orm import Session
from core.models import User
from config import DIFFICULTY_REWARDS
from core.activity_logger import log_activity


def check_level_up(xp: int, level: int) -> tuple[bool, int, int]:
    """레벨업 확인. (leveled_up, new_level, remaining_xp) 반환."""
    required = level * 100
    if xp >= required:
        return True, level + 1, xp - required
    return False, level, xp


def apply_reward(
    session: Session, user: User, difficulty: str, stat_type: str
) -> dict:
    """퀘스트 완료 보상 적용. XP/스탯 증가 + 레벨업 처리."""
    reward = DIFFICULTY_REWARDS[difficulty]
    xp_gained = reward["xp"]
    stat_gained = reward["stat"]

    user.xp += xp_gained

    current_stat = getattr(user.stats, stat_type)
    setattr(user.stats, stat_type, current_stat + stat_gained)

    leveled_up, new_level, remaining_xp = check_level_up(user.xp, user.level)
    if leveled_up:
        user.level = new_level
        user.xp = remaining_xp

    session.commit()

    if leveled_up:
        log_activity(session, "level_up", "growth", user_id=user.id, detail={
            "new_level": new_level, "total_xp": user.xp,
        })

    return {
        "xp_gained": xp_gained,
        "stat_type": stat_type,
        "stat_gained": stat_gained,
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else user.level,
    }
