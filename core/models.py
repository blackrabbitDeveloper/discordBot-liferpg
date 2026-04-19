# core/models.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Date, DateTime,
    ForeignKey, create_engine, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True, nullable=False)
    nickname = Column(String, nullable=False)
    goal_category = Column(String)
    goal_text = Column(String)
    time_budget = Column(String)
    energy_preference = Column(String)
    difficulty_preference = Column(String)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    streak_protected = Column(Boolean, default=False)
    last_streak_date = Column(Date, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stats = relationship("UserStats", uselist=False, back_populates="user", cascade="all, delete-orphan")
    quests = relationship("DailyQuest", back_populates="user", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", cascade="all, delete-orphan")
    weekly_reports = relationship("WeeklyReport", cascade="all, delete-orphan")
    activity_logs = relationship("UserActivityLog", cascade="all, delete-orphan")


class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    health = Column(Integer, default=0)
    focus = Column(Integer, default=0)
    execution = Column(Integer, default=0)
    knowledge = Column(Integer, default=0)
    finance = Column(Integer, default=0)

    user = relationship("User", back_populates="stats")


class DailyQuest(Base):
    __tablename__ = "daily_quests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quest_date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    estimated_minutes = Column(Integer)
    difficulty = Column(String, nullable=False)
    reward_xp = Column(Integer, nullable=False)
    reward_stat_type = Column(String, nullable=False)
    reward_stat_value = Column(Integer, nullable=False)
    state = Column(String, default="PENDING")
    replace_count = Column(Integer, default=0)
    message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="quests")
    logs = relationship("QuestLog", back_populates="quest", cascade="all, delete-orphan")


class QuestLog(Base):
    __tablename__ = "quest_logs"

    id = Column(Integer, primary_key=True)
    quest_id = Column(Integer, ForeignKey("daily_quests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String, nullable=False)
    action_time = Column(DateTime, default=datetime.utcnow)
    note = Column(String, nullable=True)

    quest = relationship("DailyQuest", back_populates="logs")


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    completed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    expired_count = Column(Integer, default=0)
    main_growth_stat = Column(String)
    summary_text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    completion_rate = Column(Float, default=0.0)
    best_stat = Column(String)
    risk_pattern = Column(String)
    suggestion_text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for pre-onboarding
    action = Column(String, nullable=False)
    category = Column(String, nullable=False)  # onboarding, flow, quest, growth, system
    detail = Column(String, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False)
    config_type = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("guild_id", "config_type", name="uq_guild_config_type"),
    )
