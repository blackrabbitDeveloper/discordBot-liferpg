from sqlalchemy.orm import Session
from core.models import GuildConfig


def set_channel(session: Session, guild_id: str, config_type: str, channel_id: str) -> GuildConfig:
    """채널 설정을 생성하거나 업데이트한다."""
    config = session.query(GuildConfig).filter_by(
        guild_id=guild_id, config_type=config_type
    ).first()
    if config:
        config.channel_id = channel_id
    else:
        config = GuildConfig(guild_id=guild_id, config_type=config_type, channel_id=channel_id)
        session.add(config)
    session.commit()
    return config


def get_channel(session: Session, guild_id: str, config_type: str) -> str | None:
    """설정된 채널 ID를 반환한다. 없으면 None."""
    config = session.query(GuildConfig).filter_by(
        guild_id=guild_id, config_type=config_type
    ).first()
    return config.channel_id if config else None


def remove_channel(session: Session, guild_id: str, config_type: str) -> bool:
    """채널 설정을 삭제한다. 삭제 성공 시 True."""
    config = session.query(GuildConfig).filter_by(
        guild_id=guild_id, config_type=config_type
    ).first()
    if config:
        session.delete(config)
        session.commit()
        return True
    return False
