import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, GuildConfig
from core.guild_config import set_channel, get_channel, remove_channel


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_set_channel_creates_new(db_session):
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="222")
    result = db_session.query(GuildConfig).filter_by(guild_id="111", config_type="welcome").first()
    assert result is not None
    assert result.channel_id == "222"


def test_set_channel_updates_existing(db_session):
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="222")
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="333")
    count = db_session.query(GuildConfig).filter_by(guild_id="111", config_type="welcome").count()
    assert count == 1
    result = db_session.query(GuildConfig).filter_by(guild_id="111", config_type="welcome").first()
    assert result.channel_id == "333"


def test_get_channel_exists(db_session):
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="222")
    assert get_channel(db_session, guild_id="111", config_type="welcome") == "222"


def test_get_channel_not_exists(db_session):
    assert get_channel(db_session, guild_id="111", config_type="welcome") is None


def test_remove_channel(db_session):
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="222")
    removed = remove_channel(db_session, guild_id="111", config_type="welcome")
    assert removed is True
    assert get_channel(db_session, guild_id="111", config_type="welcome") is None


def test_remove_channel_not_exists(db_session):
    removed = remove_channel(db_session, guild_id="111", config_type="welcome")
    assert removed is False


def test_multiple_config_types(db_session):
    set_channel(db_session, guild_id="111", config_type="welcome", channel_id="222")
    set_channel(db_session, guild_id="111", config_type="report", channel_id="333")
    assert get_channel(db_session, guild_id="111", config_type="welcome") == "222"
    assert get_channel(db_session, guild_id="111", config_type="report") == "333"
