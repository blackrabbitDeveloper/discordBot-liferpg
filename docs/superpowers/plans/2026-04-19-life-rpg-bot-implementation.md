# Life RPG Discord Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discord 봇 기반의 일일 퀘스트 운영 시스템을 구현하고, 콘솔 어댑터로 배포 전 테스트할 수 있게 한다.

**Architecture:** core/bot/console 3계층 분리. core는 순수 Python+SQLAlchemy 비즈니스 로직, bot은 Discord UI 변환, console은 터미널 테스트 어댑터. 모든 핵심 로직은 core에서 처리되어 Discord 없이 테스트 가능.

**Tech Stack:** Python 3.11+, discord.py 2.3+, SQLAlchemy 2.0+, PyYAML, python-dotenv, pytest

---

## Task 1: 프로젝트 세팅 + 의존성

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `core/__init__.py`
- Create: `bot/__init__.py`
- Create: `bot/cogs/__init__.py`
- Create: `bot/views/__init__.py`
- Create: `console/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/` (directory)

- [ ] **Step 1: requirements.txt 생성**

```
discord.py>=2.3
SQLAlchemy>=2.0
PyYAML>=6.0
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: .gitignore 생성**

```
__pycache__/
*.pyc
.env
*.db
data/life_rpg.db
.venv/
.superpowers/
```

- [ ] **Step 3: .env.example 생성**

```
DISCORD_TOKEN=your_token_here
DATABASE_URL=sqlite:///data/life_rpg.db
```

- [ ] **Step 4: config.py 생성**

```python
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/life_rpg.db")

DAY_BOUNDARY_HOUR = 4
MORNING_QUEST_HOUR = 8
EVENING_REPORT_HOUR = 21
WEEKLY_REPORT_DAY = 6  # 일요일 (0=월요일)

CATEGORY_STAT_MAP = {
    "건강": "health",
    "회복": "health",
    "집중": "focus",
    "일/커리어": "execution",
    "정리/생활": "execution",
    "공부": "knowledge",
    "창작": "knowledge",
    "돈관리": "finance",
}

DIFFICULTY_REWARDS = {
    "easy": {"xp": 5, "stat": 1},
    "normal": {"xp": 10, "stat": 2},
    "hard": {"xp": 20, "stat": 3},
}
```

- [ ] **Step 5: 패키지 디렉터리 __init__.py 생성**

`core/__init__.py`, `bot/__init__.py`, `bot/cogs/__init__.py`, `bot/views/__init__.py`, `console/__init__.py`, `tests/__init__.py` — 모두 빈 파일.

- [ ] **Step 6: data 디렉터리 생성 확인**

```bash
mkdir -p data
```

- [ ] **Step 7: 가상환경 생성 및 의존성 설치**

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
```

- [ ] **Step 8: Commit**

```bash
git init
git add requirements.txt config.py .env.example .gitignore core/__init__.py bot/__init__.py bot/cogs/__init__.py bot/views/__init__.py console/__init__.py tests/__init__.py
git commit -m "chore: initial project setup with dependencies and config"
```

---

## Task 2: SQLAlchemy 모델 정의

**Files:**
- Create: `core/database.py`
- Create: `core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 모델 테스트 작성**

```python
# tests/test_models.py
import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest, QuestLog, DailyReport, WeeklyReport


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_user(db_session):
    user = User(
        discord_id="123456",
        nickname="테스터",
        goal_category="건강",
        goal_text="매일 운동하기",
        time_budget="medium",
        energy_preference="normal",
        difficulty_preference="moderate",
    )
    db_session.add(user)
    db_session.commit()

    saved = db_session.query(User).filter_by(discord_id="123456").first()
    assert saved is not None
    assert saved.nickname == "테스터"
    assert saved.level == 1
    assert saved.xp == 0
    assert saved.streak == 0
    assert saved.streak_protected is False
    assert saved.status == "active"


def test_create_user_stats(db_session):
    user = User(discord_id="111", nickname="유저1", goal_category="건강", goal_text="운동")
    db_session.add(user)
    db_session.commit()

    stats = UserStats(user_id=user.id)
    db_session.add(stats)
    db_session.commit()

    saved = db_session.query(UserStats).filter_by(user_id=user.id).first()
    assert saved.health == 0
    assert saved.focus == 0
    assert saved.execution == 0
    assert saved.knowledge == 0
    assert saved.finance == 0


def test_create_daily_quest(db_session):
    user = User(discord_id="222", nickname="유저2", goal_category="집중", goal_text="공부")
    db_session.add(user)
    db_session.commit()

    quest = DailyQuest(
        user_id=user.id,
        quest_date=date(2026, 4, 19),
        category="집중",
        title="25분 집중 작업",
        description="타이머를 맞추고 한 가지 일에 집중하세요",
        estimated_minutes=25,
        difficulty="normal",
        reward_xp=10,
        reward_stat_type="focus",
        reward_stat_value=2,
    )
    db_session.add(quest)
    db_session.commit()

    saved = db_session.query(DailyQuest).filter_by(user_id=user.id).first()
    assert saved.state == "PENDING"
    assert saved.title == "25분 집중 작업"
    assert saved.completed_at is None


def test_create_quest_log(db_session):
    user = User(discord_id="333", nickname="유저3", goal_category="건강", goal_text="운동")
    db_session.add(user)
    db_session.commit()

    quest = DailyQuest(
        user_id=user.id, quest_date=date(2026, 4, 19),
        category="건강", title="스트레칭", description="테스트",
        estimated_minutes=5, difficulty="easy",
        reward_xp=5, reward_stat_type="health", reward_stat_value=1,
    )
    db_session.add(quest)
    db_session.commit()

    log = QuestLog(
        quest_id=quest.id, user_id=user.id,
        action_type="completed",
    )
    db_session.add(log)
    db_session.commit()

    saved = db_session.query(QuestLog).filter_by(quest_id=quest.id).first()
    assert saved.action_type == "completed"


def test_user_stats_relationship(db_session):
    user = User(discord_id="444", nickname="유저4", goal_category="공부", goal_text="독서")
    db_session.add(user)
    db_session.commit()

    stats = UserStats(user_id=user.id, knowledge=5)
    db_session.add(stats)
    db_session.commit()

    assert user.stats.knowledge == 5
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `core.models` 모듈이 없음

- [ ] **Step 3: core/database.py 구현**

```python
# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None
_SessionLocal = None


def init_db(database_url: str) -> None:
    global _engine, _SessionLocal
    _engine = create_engine(database_url, echo=False)
    _SessionLocal = sessionmaker(bind=_engine)


def get_engine():
    return _engine


def get_session() -> Session:
    return _SessionLocal()
```

- [ ] **Step 4: core/models.py 구현**

```python
# core/models.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Date, DateTime,
    ForeignKey, create_engine,
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
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stats = relationship("UserStats", uselist=False, back_populates="user")
    quests = relationship("DailyQuest", back_populates="user")


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
    message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="quests")
    logs = relationship("QuestLog", back_populates="quest")


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
```

- [ ] **Step 5: 테스트 실행하여 통과 확인**

```bash
pytest tests/test_models.py -v
```

Expected: 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add core/database.py core/models.py tests/test_models.py
git commit -m "feat: add SQLAlchemy models and database setup"
```

---

## Task 3: 게임 날짜 유틸리티 (새벽 4시 기준)

**Files:**
- Create: `core/time_utils.py`
- Create: `tests/test_time_utils.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_time_utils.py
from datetime import datetime, date
from core.time_utils import get_game_date


def test_after_4am_returns_today():
    # 2026-04-19 10:00 → game date = 2026-04-19
    now = datetime(2026, 4, 19, 10, 0)
    assert get_game_date(now) == date(2026, 4, 19)


def test_before_4am_returns_yesterday():
    # 2026-04-19 03:59 → game date = 2026-04-18
    now = datetime(2026, 4, 19, 3, 59)
    assert get_game_date(now) == date(2026, 4, 18)


def test_exactly_4am_returns_today():
    # 2026-04-19 04:00 → game date = 2026-04-19
    now = datetime(2026, 4, 19, 4, 0)
    assert get_game_date(now) == date(2026, 4, 19)


def test_midnight_returns_yesterday():
    # 2026-04-19 00:00 → game date = 2026-04-18
    now = datetime(2026, 4, 19, 0, 0)
    assert get_game_date(now) == date(2026, 4, 18)


def test_just_before_midnight_returns_today():
    # 2026-04-19 23:59 → game date = 2026-04-19
    now = datetime(2026, 4, 19, 23, 59)
    assert get_game_date(now) == date(2026, 4, 19)
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_time_utils.py -v
```

Expected: FAIL — `core.time_utils` 없음

- [ ] **Step 3: 구현**

```python
# core/time_utils.py
from datetime import datetime, date, time, timedelta

from config import DAY_BOUNDARY_HOUR

_BOUNDARY = time(DAY_BOUNDARY_HOUR, 0)


def get_game_date(now: datetime | None = None) -> date:
    """새벽 4시 기준 게임 날짜 반환. 4시 이전이면 전날로 취급."""
    if now is None:
        now = datetime.now()
    if now.time() < _BOUNDARY:
        return (now - timedelta(days=1)).date()
    return now.date()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_time_utils.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/time_utils.py tests/test_time_utils.py
git commit -m "feat: add game date utility with 4am day boundary"
```

---

## Task 4: 보상 엔진

**Files:**
- Create: `core/reward_engine.py`
- Create: `tests/test_reward_engine.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_reward_engine.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats
from core.reward_engine import apply_reward, check_level_up


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user_with_stats(db_session):
    user = User(
        discord_id="100", nickname="보상테스트",
        goal_category="건강", goal_text="운동",
    )
    db_session.add(user)
    db_session.commit()
    stats = UserStats(user_id=user.id)
    db_session.add(stats)
    db_session.commit()
    return user


def test_apply_reward_easy(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["xp_gained"] == 5
    assert result["stat_gained"] == 1
    assert result["stat_type"] == "health"
    assert user_with_stats.xp == 5
    assert user_with_stats.stats.health == 1


def test_apply_reward_normal(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "normal", "focus")
    assert result["xp_gained"] == 10
    assert result["stat_gained"] == 2
    assert user_with_stats.stats.focus == 2


def test_apply_reward_hard(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "hard", "execution")
    assert result["xp_gained"] == 20
    assert result["stat_gained"] == 3
    assert user_with_stats.stats.execution == 3


def test_level_up_at_100xp(db_session, user_with_stats):
    user_with_stats.xp = 95
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["leveled_up"] is True
    assert result["new_level"] == 2
    assert user_with_stats.level == 2
    assert user_with_stats.xp == 0  # 100 - 100 = 0


def test_level_up_with_overflow(db_session, user_with_stats):
    user_with_stats.xp = 95
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "normal", "focus")
    # 95 + 10 = 105, 필요 100 → Lv2, 잔여 5
    assert result["leveled_up"] is True
    assert user_with_stats.level == 2
    assert user_with_stats.xp == 5


def test_no_level_up(db_session, user_with_stats):
    result = apply_reward(db_session, user_with_stats, "easy", "health")
    assert result["leveled_up"] is False
    assert user_with_stats.level == 1


def test_level2_needs_200xp(db_session, user_with_stats):
    user_with_stats.level = 2
    user_with_stats.xp = 190
    db_session.commit()
    result = apply_reward(db_session, user_with_stats, "normal", "knowledge")
    # 190 + 10 = 200, 필요 200 → Lv3, 잔여 0
    assert result["leveled_up"] is True
    assert user_with_stats.level == 3
    assert user_with_stats.xp == 0


def test_check_level_up_utility():
    assert check_level_up(100, 1) == (True, 2, 0)
    assert check_level_up(50, 1) == (False, 1, 50)
    assert check_level_up(250, 2) == (True, 3, 50)
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_reward_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 구현**

```python
# core/reward_engine.py
from sqlalchemy.orm import Session
from core.models import User
from config import DIFFICULTY_REWARDS


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

    # XP 추가
    user.xp += xp_gained

    # 스탯 추가
    current_stat = getattr(user.stats, stat_type)
    setattr(user.stats, stat_type, current_stat + stat_gained)

    # 레벨업 체크
    leveled_up, new_level, remaining_xp = check_level_up(user.xp, user.level)
    if leveled_up:
        user.level = new_level
        user.xp = remaining_xp

    session.commit()

    return {
        "xp_gained": xp_gained,
        "stat_type": stat_type,
        "stat_gained": stat_gained,
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else user.level,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_reward_engine.py -v
```

Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/reward_engine.py tests/test_reward_engine.py
git commit -m "feat: add reward engine with XP, stat, and level-up logic"
```

---

## Task 5: 스트릭 엔진

**Files:**
- Create: `core/streak_engine.py`
- Create: `tests/test_streak_engine.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_streak_engine.py
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
    # 오늘 완료 퀘스트 없음 (EXPIRED만)
    _add_quest(db_session, user, date(2026, 4, 19), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 19))
    assert user.streak == 5  # 유지
    assert user.streak_protected is True


def test_streak_decreases_on_second_miss(db_session, user):
    user.streak = 5
    user.streak_protected = True  # 이미 1일 보호 사용
    db_session.commit()
    _add_quest(db_session, user, date(2026, 4, 20), "EXPIRED")
    update_streak(db_session, user, date(2026, 4, 20))
    assert user.streak == 4
    assert user.streak_protected is True  # 계속 보호 상태 유지


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
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_streak_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 구현**

```python
# core/streak_engine.py
from datetime import date
from sqlalchemy.orm import Session
from core.models import User, DailyQuest


def _has_completed_quest(session: Session, user: User, game_date: date) -> bool:
    """해당 날짜에 완료한 퀘스트가 있는지 확인."""
    return (
        session.query(DailyQuest)
        .filter(
            DailyQuest.user_id == user.id,
            DailyQuest.quest_date == game_date,
            DailyQuest.state == "COMPLETED",
        )
        .first()
        is not None
    )


def update_streak(session: Session, user: User, game_date: date) -> dict:
    """스트릭 업데이트. 완료 여부에 따라 유지/보호/감소/리셋."""
    completed = _has_completed_quest(session, user, game_date)

    if completed:
        user.streak += 1
        user.streak_protected = False
        status = "increased"
    elif not user.streak_protected:
        # 첫 미완료: 보호
        user.streak_protected = True
        status = "protected"
    else:
        # 보호 상태에서 또 미완료: 감소
        user.streak = max(0, user.streak - 1)
        status = "decreased"

    session.commit()
    return {"streak": user.streak, "status": status}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_streak_engine.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/streak_engine.py tests/test_streak_engine.py
git commit -m "feat: add streak engine with protection and gradual decrease"
```

---

## Task 6: 퀘스트 템플릿 YAML + 로더

**Files:**
- Create: `data/quests.yaml`
- Create: `core/quest_loader.py`
- Create: `tests/test_quest_loader.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_quest_loader.py
import pytest
import tempfile
import os
from core.quest_loader import load_quests, filter_quests


@pytest.fixture
def sample_yaml(tmp_path):
    content = """
categories:
  건강:
    quests:
      - title: "물 한 잔 마시기"
        description: "물 한 잔을 마셔보세요"
        estimated_minutes: 1
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "20분 유산소 운동"
        description: "걷기나 달리기를 해보세요"
        estimated_minutes: 20
        difficulty: hard
        energy: [normal, high]
        time_budget: [medium, long]
  집중:
    quests:
      - title: "25분 집중 작업"
        description: "타이머를 맞추고 집중하세요"
        estimated_minutes: 25
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
"""
    path = tmp_path / "quests.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_load_quests(sample_yaml):
    quests = load_quests(sample_yaml)
    assert "건강" in quests
    assert "집중" in quests
    assert len(quests["건강"]) == 2
    assert len(quests["집중"]) == 1


def test_quest_has_required_fields(sample_yaml):
    quests = load_quests(sample_yaml)
    q = quests["건강"][0]
    assert q["title"] == "물 한 잔 마시기"
    assert q["difficulty"] == "easy"
    assert q["estimated_minutes"] == 1


def test_filter_by_category(sample_yaml):
    quests = load_quests(sample_yaml)
    filtered = filter_quests(quests, category="건강")
    assert len(filtered) == 2
    assert all(q["_category"] == "건강" for q in filtered)


def test_filter_by_energy(sample_yaml):
    quests = load_quests(sample_yaml)
    filtered = filter_quests(quests, category="건강", energy="low")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "물 한 잔 마시기"


def test_filter_by_time_budget(sample_yaml):
    quests = load_quests(sample_yaml)
    filtered = filter_quests(quests, category="건강", time_budget="short")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "물 한 잔 마시기"


def test_filter_combined(sample_yaml):
    quests = load_quests(sample_yaml)
    filtered = filter_quests(quests, category="건강", energy="high", time_budget="long")
    assert len(filtered) == 2
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_quest_loader.py -v
```

Expected: FAIL

- [ ] **Step 3: quest_loader.py 구현**

```python
# core/quest_loader.py
import yaml
from typing import Any


def load_quests(yaml_path: str) -> dict[str, list[dict]]:
    """YAML 파일에서 카테고리별 퀘스트 목록을 로드한다."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result = {}
    for category, info in data["categories"].items():
        quests = []
        for q in info["quests"]:
            q["_category"] = category
            quests.append(q)
        result[category] = quests
    return result


def filter_quests(
    quests: dict[str, list[dict]],
    category: str | None = None,
    energy: str | None = None,
    time_budget: str | None = None,
) -> list[dict]:
    """카테고리, 에너지, 시간 예산으로 퀘스트를 필터링한다."""
    pool = []
    if category:
        pool = list(quests.get(category, []))
    else:
        for cat_quests in quests.values():
            pool.extend(cat_quests)

    if energy:
        pool = [q for q in pool if energy in q.get("energy", [])]
    if time_budget:
        pool = [q for q in pool if time_budget in q.get("time_budget", [])]

    return pool
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_quest_loader.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: data/quests.yaml 전체 퀘스트 템플릿 작성**

```yaml
# data/quests.yaml
categories:
  건강:
    quests:
      - title: "물 한 잔 마시기"
        description: "일어나서 물 한 잔을 마셔보세요"
        estimated_minutes: 1
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "5분 스트레칭"
        description: "간단한 전신 스트레칭을 해보세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "10분 걷기"
        description: "가볍게 동네를 걸어보세요"
        estimated_minutes: 10
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "20분 유산소 운동"
        description: "걷기, 달리기, 자전거 중 하나를 선택하세요"
        estimated_minutes: 20
        difficulty: hard
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "수면 준비 체크"
        description: "잠자기 30분 전 전자기기를 멀리 두세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]

  회복:
    quests:
      - title: "심호흡 3분"
        description: "편안한 자세로 깊게 호흡하세요"
        estimated_minutes: 3
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "5분 명상"
        description: "조용한 곳에서 눈을 감고 쉬세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "좋아하는 음악 1곡 듣기"
        description: "좋아하는 노래를 하나 골라 편하게 들으세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]

  집중:
    quests:
      - title: "5분 정리"
        description: "책상 위 또는 주변을 5분간 정리하세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "15분 집중 작업"
        description: "타이머를 맞추고 한 가지 일에 집중하세요"
        estimated_minutes: 15
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "25분 뽀모도로"
        description: "25분 집중 + 5분 휴식 한 세트를 해보세요"
        estimated_minutes: 30
        difficulty: hard
        energy: [high]
        time_budget: [long]

  "일/커리어":
    quests:
      - title: "오늘 할 일 3개 적기"
        description: "오늘 해야 할 가장 중요한 일 3개를 적으세요"
        estimated_minutes: 3
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "업무 관련 10분 행동"
        description: "미루던 업무 하나를 10분만 시작하세요"
        estimated_minutes: 10
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "30분 프로젝트 작업"
        description: "진행 중인 프로젝트에 30분을 투자하세요"
        estimated_minutes: 30
        difficulty: hard
        energy: [high]
        time_budget: [long]

  "정리/생활":
    quests:
      - title: "설거지하기"
        description: "싱크대에 쌓인 설거지를 해치우세요"
        estimated_minutes: 10
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "빨래 돌리기"
        description: "빨래를 모아서 세탁기를 돌리세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "방 정리 15분"
        description: "방 한 곳을 골라 15분간 정리하세요"
        estimated_minutes: 15
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]

  공부:
    quests:
      - title: "단어 5개 외우기"
        description: "공부 중인 분야의 핵심 단어 5개를 복습하세요"
        estimated_minutes: 5
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "10분 독서"
        description: "읽고 있는 책을 10분간 읽으세요"
        estimated_minutes: 10
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "강의 1개 시청"
        description: "학습 중인 강의를 1개 들으세요"
        estimated_minutes: 30
        difficulty: hard
        energy: [high]
        time_budget: [long]

  창작:
    quests:
      - title: "아이디어 3줄 정리"
        description: "떠오르는 아이디어를 3줄로 메모하세요"
        estimated_minutes: 3
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "초안 10분 쓰기"
        description: "완벽하지 않아도 좋으니 10분만 써보세요"
        estimated_minutes: 10
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
      - title: "25분 집중 창작"
        description: "작업물에 25분을 온전히 투자하세요"
        estimated_minutes: 25
        difficulty: hard
        energy: [high]
        time_budget: [long]

  돈관리:
    quests:
      - title: "오늘 지출 기록"
        description: "오늘 쓴 돈을 한 곳에 기록하세요"
        estimated_minutes: 3
        difficulty: easy
        energy: [low, normal, high]
        time_budget: [short, medium, long]
      - title: "불필요한 구독 1개 확인"
        description: "쓰지 않는 구독 서비스가 있는지 확인하세요"
        estimated_minutes: 5
        difficulty: normal
        energy: [normal, high]
        time_budget: [short, medium, long]
      - title: "주간 예산 점검"
        description: "이번 주 예산 대비 지출을 확인하세요"
        estimated_minutes: 10
        difficulty: normal
        energy: [normal, high]
        time_budget: [medium, long]
```

- [ ] **Step 6: Commit**

```bash
git add core/quest_loader.py tests/test_quest_loader.py data/quests.yaml
git commit -m "feat: add quest template YAML and loader with filtering"
```

---

## Task 7: 퀘스트 엔진

**Files:**
- Create: `core/quest_engine.py`
- Create: `tests/test_quest_engine.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_quest_engine.py
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats, DailyQuest, QuestLog
from core.quest_engine import (
    generate_daily_quests,
    complete_quest,
    skip_quest,
    expire_pending_quests,
    late_log_quest,
    get_today_quests,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db_session):
    u = User(
        discord_id="700", nickname="퀘스트유저",
        goal_category="건강", goal_text="운동",
        time_budget="medium", energy_preference="normal",
        difficulty_preference="moderate",
    )
    db_session.add(u)
    db_session.commit()
    stats = UserStats(user_id=u.id)
    db_session.add(stats)
    db_session.commit()
    return u


@pytest.fixture
def sample_quests():
    return {
        "건강": [
            {"title": "물 마시기", "description": "물 한 잔", "estimated_minutes": 1,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "건강"},
            {"title": "스트레칭", "description": "전신 스트레칭", "estimated_minutes": 5,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "건강"},
            {"title": "10분 걷기", "description": "동네 걷기", "estimated_minutes": 10,
             "difficulty": "normal", "energy": ["normal", "high"],
             "time_budget": ["medium", "long"], "_category": "건강"},
            {"title": "유산소", "description": "달리기", "estimated_minutes": 20,
             "difficulty": "hard", "energy": ["high"],
             "time_budget": ["long"], "_category": "건강"},
        ],
        "회복": [
            {"title": "심호흡", "description": "3분 호흡", "estimated_minutes": 3,
             "difficulty": "easy", "energy": ["low", "normal", "high"],
             "time_budget": ["short", "medium", "long"], "_category": "회복"},
        ],
    }


def test_generate_daily_quests_returns_3(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    assert len(quests) == 3


def test_generate_daily_quests_saves_to_db(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    saved = db_session.query(DailyQuest).filter_by(user_id=user.id).all()
    assert len(saved) == 3
    assert all(q.state == "PENDING" for q in saved)


def test_generate_daily_quests_no_duplicates_same_day(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    quests2 = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    # 이미 오늘 퀘스트가 있으면 기존 것 반환
    assert len(quests2) == 3


def test_complete_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    result = complete_quest(db_session, user, quests[0].id, date(2026, 4, 19))
    assert result["success"] is True
    assert quests[0].state == "COMPLETED"
    assert quests[0].completed_at is not None
    log = db_session.query(QuestLog).filter_by(quest_id=quests[0].id).first()
    assert log.action_type == "completed"


def test_complete_quest_past_date_rejected(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    result = complete_quest(db_session, user, quests[0].id, date(2026, 4, 19))
    assert result["success"] is False
    assert result["reason"] == "past_quest"


def test_skip_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    result = skip_quest(db_session, user, quests[0].id)
    assert result["success"] is True
    assert quests[0].state == "SKIPPED"


def test_expire_pending_quests(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    count = expire_pending_quests(db_session, date(2026, 4, 18))
    assert count > 0
    expired = db_session.query(DailyQuest).filter_by(state="EXPIRED").all()
    assert len(expired) == 3


def test_late_log_quest(db_session, user, sample_quests):
    quests = generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 18))
    # 만료 처리
    expire_pending_quests(db_session, date(2026, 4, 18))
    result = late_log_quest(db_session, user, quests[0].id)
    assert result["success"] is True
    assert quests[0].state == "LATE_LOGGED"


def test_get_today_quests(db_session, user, sample_quests):
    generate_daily_quests(db_session, user, sample_quests, date(2026, 4, 19))
    today = get_today_quests(db_session, user, date(2026, 4, 19))
    assert len(today) == 3
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_quest_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 구현**

```python
# core/quest_engine.py
import random
from datetime import date, datetime
from sqlalchemy.orm import Session
from core.models import User, DailyQuest, QuestLog
from core.quest_loader import filter_quests
from config import CATEGORY_STAT_MAP, DIFFICULTY_REWARDS


def generate_daily_quests(
    session: Session,
    user: User,
    quest_pool: dict[str, list[dict]],
    game_date: date,
) -> list[DailyQuest]:
    """오늘의 퀘스트 3개 생성. 이미 있으면 기존 것 반환."""
    existing = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .all()
    )
    if existing:
        return existing

    # 필터링
    filtered = filter_quests(
        quest_pool,
        category=user.goal_category,
        energy=user.energy_preference,
        time_budget=user.time_budget,
    )

    # 목표 카테고리에서 부족하면 관련 카테고리(회복 등)도 추가
    if len(filtered) < 3:
        all_filtered = filter_quests(
            quest_pool,
            energy=user.energy_preference,
            time_budget=user.time_budget,
        )
        for q in all_filtered:
            if q not in filtered:
                filtered.append(q)

    # 3개 선택 (부족하면 있는 만큼)
    count = min(3, len(filtered))
    selected = random.sample(filtered, count)

    quests = []
    for q in selected:
        category = q["_category"]
        stat_type = CATEGORY_STAT_MAP.get(category, "health")
        reward = DIFFICULTY_REWARDS[q["difficulty"]]

        quest = DailyQuest(
            user_id=user.id,
            quest_date=game_date,
            category=category,
            title=q["title"],
            description=q["description"],
            estimated_minutes=q["estimated_minutes"],
            difficulty=q["difficulty"],
            reward_xp=reward["xp"],
            reward_stat_type=stat_type,
            reward_stat_value=reward["stat"],
        )
        session.add(quest)
        quests.append(quest)

    session.commit()
    return quests


def get_today_quests(
    session: Session, user: User, game_date: date
) -> list[DailyQuest]:
    """오늘의 퀘스트 목록 조회."""
    return (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == game_date)
        .all()
    )


def complete_quest(
    session: Session, user: User, quest_id: int, game_date: date
) -> dict:
    """퀘스트 완료 처리. 과거 퀘스트는 거부."""
    quest = session.query(DailyQuest).get(quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}
    if quest.quest_date != game_date:
        return {"success": False, "reason": "past_quest", "quest": quest}

    quest.state = "COMPLETED"
    quest.completed_at = datetime.utcnow()

    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="completed",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}


def skip_quest(session: Session, user: User, quest_id: int) -> dict:
    """퀘스트 건너뛰기."""
    quest = session.query(DailyQuest).get(quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}

    quest.state = "SKIPPED"
    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="skipped",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}


def expire_pending_quests(session: Session, game_date: date) -> int:
    """해당 날짜의 PENDING 퀘스트를 EXPIRED로 변경."""
    pending = (
        session.query(DailyQuest)
        .filter(
            DailyQuest.quest_date == game_date,
            DailyQuest.state == "PENDING",
        )
        .all()
    )
    for quest in pending:
        quest.state = "EXPIRED"
        log = QuestLog(
            quest_id=quest.id,
            user_id=quest.user_id,
            action_type="expired",
        )
        session.add(log)

    session.commit()
    return len(pending)


def late_log_quest(session: Session, user: User, quest_id: int) -> dict:
    """과거 퀘스트를 회고 기록으로 남김."""
    quest = session.query(DailyQuest).get(quest_id)
    if quest is None:
        return {"success": False, "reason": "not_found"}

    quest.state = "LATE_LOGGED"
    log = QuestLog(
        quest_id=quest.id,
        user_id=user.id,
        action_type="late_logged",
    )
    session.add(log)
    session.commit()

    return {"success": True, "quest": quest}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_quest_engine.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/quest_engine.py tests/test_quest_engine.py
git commit -m "feat: add quest engine with generation, completion, skip, and expiry"
```

---

## Task 8: 온보딩 로직

**Files:**
- Create: `core/onboarding.py`
- Create: `tests/test_onboarding.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_onboarding.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.models import Base, User, UserStats
from core.onboarding import (
    GOAL_CATEGORIES,
    TIME_BUDGETS,
    ENERGY_LEVELS,
    DIFFICULTY_LEVELS,
    create_user,
    reset_user,
    is_onboarded,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_constants():
    assert len(GOAL_CATEGORIES) == 7
    assert "건강" in GOAL_CATEGORIES
    assert len(TIME_BUDGETS) == 3
    assert len(ENERGY_LEVELS) == 3
    assert len(DIFFICULTY_LEVELS) == 3


def test_create_user(db_session):
    user = create_user(
        db_session,
        discord_id="900",
        nickname="온보딩유저",
        goal_category="건강",
        goal_text="매일 운동",
        time_budget="medium",
        energy_preference="normal",
        difficulty_preference="moderate",
    )
    assert user.id is not None
    assert user.level == 1
    assert user.stats is not None
    assert user.stats.health == 0


def test_create_user_duplicate_resets(db_session):
    create_user(db_session, "900", "유저A", "건강", "운동", "medium", "normal", "moderate")
    user2 = create_user(db_session, "900", "유저B", "공부", "독서", "long", "high", "hard")
    assert user2.nickname == "유저B"
    assert user2.goal_category == "공부"
    # 같은 discord_id로 재생성하면 기존 유저 리셋
    count = db_session.query(User).filter_by(discord_id="900").count()
    assert count == 1


def test_is_onboarded(db_session):
    assert is_onboarded(db_session, "900") is False
    create_user(db_session, "900", "유저", "건강", "운동", "medium", "normal", "moderate")
    assert is_onboarded(db_session, "900") is True


def test_reset_user(db_session):
    create_user(db_session, "900", "유저", "건강", "운동", "medium", "normal", "moderate")
    reset_user(db_session, "900")
    assert is_onboarded(db_session, "900") is False
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_onboarding.py -v
```

Expected: FAIL

- [ ] **Step 3: 구현**

```python
# core/onboarding.py
from sqlalchemy.orm import Session
from core.models import User, UserStats

GOAL_CATEGORIES = ["건강", "집중", "일/커리어", "공부", "창작", "돈관리", "정리/생활"]

TIME_BUDGETS = {
    "short": "10분 이하",
    "medium": "10~30분",
    "long": "30분 이상",
}

ENERGY_LEVELS = {
    "low": "낮음",
    "normal": "보통",
    "high": "높음",
}

DIFFICULTY_LEVELS = {
    "light": "아주 가볍게",
    "moderate": "적당히",
    "hard": "조금 빡세게",
}


def is_onboarded(session: Session, discord_id: str) -> bool:
    """해당 discord_id의 유저가 온보딩을 완료했는지 확인."""
    return session.query(User).filter_by(discord_id=discord_id).first() is not None


def create_user(
    session: Session,
    discord_id: str,
    nickname: str,
    goal_category: str,
    goal_text: str,
    time_budget: str,
    energy_preference: str,
    difficulty_preference: str,
) -> User:
    """유저 생성. 이미 존재하면 리셋 후 재생성."""
    existing = session.query(User).filter_by(discord_id=discord_id).first()
    if existing:
        # 관련 데이터 삭제 후 업데이트
        if existing.stats:
            session.delete(existing.stats)
        existing.nickname = nickname
        existing.goal_category = goal_category
        existing.goal_text = goal_text
        existing.time_budget = time_budget
        existing.energy_preference = energy_preference
        existing.difficulty_preference = difficulty_preference
        existing.level = 1
        existing.xp = 0
        existing.streak = 0
        existing.streak_protected = False
        existing.status = "active"
        session.commit()

        stats = UserStats(user_id=existing.id)
        session.add(stats)
        session.commit()
        return existing

    user = User(
        discord_id=discord_id,
        nickname=nickname,
        goal_category=goal_category,
        goal_text=goal_text,
        time_budget=time_budget,
        energy_preference=energy_preference,
        difficulty_preference=difficulty_preference,
    )
    session.add(user)
    session.commit()

    stats = UserStats(user_id=user.id)
    session.add(stats)
    session.commit()

    return user


def reset_user(session: Session, discord_id: str) -> bool:
    """유저 데이터 완전 삭제."""
    user = session.query(User).filter_by(discord_id=discord_id).first()
    if not user:
        return False
    if user.stats:
        session.delete(user.stats)
    session.delete(user)
    session.commit()
    return True
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_onboarding.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/onboarding.py tests/test_onboarding.py
git commit -m "feat: add onboarding logic with user creation and reset"
```

---

## Task 9: 리포트 엔진

**Files:**
- Create: `core/report_engine.py`
- Create: `tests/test_report_engine.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_report_engine.py
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
    # 월~금 퀘스트 생성 (5일, 각 3개, 일부 완료)
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
    # 15개 중 10개 완료 = 66.7%
    assert 60 < report.completion_rate < 70
    assert report.best_stat is not None


def test_weekly_report_saved_to_db(db_session, user):
    _add_quest(db_session, user, date(2026, 4, 13), "COMPLETED")

    generate_weekly_report(db_session, user, date(2026, 4, 13), date(2026, 4, 19))

    saved = db_session.query(WeeklyReport).filter_by(user_id=user.id).first()
    assert saved is not None
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/test_report_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 구현**

```python
# core/report_engine.py
from datetime import date
from collections import defaultdict
from sqlalchemy.orm import Session
from core.models import User, DailyQuest, DailyReport, WeeklyReport


def generate_daily_report(
    session: Session, user: User, report_date: date
) -> DailyReport:
    """일일 리포트 생성."""
    quests = (
        session.query(DailyQuest)
        .filter(DailyQuest.user_id == user.id, DailyQuest.quest_date == report_date)
        .all()
    )

    completed = [q for q in quests if q.state == "COMPLETED"]
    skipped = [q for q in quests if q.state == "SKIPPED"]
    expired = [q for q in quests if q.state == "EXPIRED"]

    # 가장 성장한 스탯 계산
    stat_gains = defaultdict(int)
    for q in completed:
        stat_gains[q.reward_stat_type] += q.reward_stat_value

    main_stat = max(stat_gains, key=stat_gains.get) if stat_gains else None

    # 요약 텍스트
    total = len(quests)
    if total == 0:
        flow = "오늘은 퀘스트가 없었어요"
    elif len(completed) == total:
        flow = "완벽한 하루였어요!"
    elif len(completed) > 0:
        flow = "안정적인 흐름이에요"
    else:
        flow = "내일 다시 이어가면 돼요"

    report = DailyReport(
        user_id=user.id,
        report_date=report_date,
        completed_count=len(completed),
        skipped_count=len(skipped),
        expired_count=len(expired),
        main_growth_stat=main_stat,
        summary_text=flow,
    )
    session.add(report)
    session.commit()
    return report


def generate_weekly_report(
    session: Session,
    user: User,
    week_start: date,
    week_end: date,
) -> WeeklyReport:
    """주간 리포트 생성."""
    quests = (
        session.query(DailyQuest)
        .filter(
            DailyQuest.user_id == user.id,
            DailyQuest.quest_date >= week_start,
            DailyQuest.quest_date <= week_end,
        )
        .all()
    )

    total = len(quests)
    completed = [q for q in quests if q.state == "COMPLETED"]

    completion_rate = (len(completed) / total * 100) if total > 0 else 0.0

    # 가장 성장한 스탯
    stat_gains = defaultdict(int)
    for q in completed:
        stat_gains[q.reward_stat_type] += q.reward_stat_value

    best_stat = max(stat_gains, key=stat_gains.get) if stat_gains else None

    # 위험 패턴 분석 (요일별 완료율)
    from collections import Counter
    expired_days = Counter()
    for q in quests:
        if q.state in ("EXPIRED", "SKIPPED"):
            expired_days[q.quest_date.strftime("%A")] += 1

    risk_pattern = None
    if expired_days:
        worst_day = max(expired_days, key=expired_days.get)
        risk_pattern = worst_day

    # 추천 전략
    if completion_rate >= 80:
        suggestion = "좋은 흐름이에요. 난이도를 조금 올려봐도 좋겠어요"
    elif completion_rate >= 50:
        suggestion = "안정적이에요. 비슷한 강도로 이어가세요"
    else:
        suggestion = "가벼운 퀘스트 비중을 늘려보는 건 어떨까요"

    report = WeeklyReport(
        user_id=user.id,
        week_start=week_start,
        week_end=week_end,
        completion_rate=round(completion_rate, 1),
        best_stat=best_stat,
        risk_pattern=risk_pattern,
        suggestion_text=suggestion,
    )
    session.add(report)
    session.commit()
    return report
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_report_engine.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/report_engine.py tests/test_report_engine.py
git commit -m "feat: add daily and weekly report engine"
```

---

## Task 10: 콘솔 어댑터

**Files:**
- Create: `console/adapter.py`
- Create: `console_main.py`

- [ ] **Step 1: console/adapter.py 구현**

```python
# console/adapter.py
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from core.models import Base, User, DailyQuest
from core.database import get_session, init_db, get_engine
from core.onboarding import (
    GOAL_CATEGORIES, TIME_BUDGETS, ENERGY_LEVELS, DIFFICULTY_LEVELS,
    create_user, is_onboarded, reset_user,
)
from core.quest_engine import (
    generate_daily_quests, complete_quest, skip_quest,
    expire_pending_quests, get_today_quests, late_log_quest,
)
from core.quest_loader import load_quests
from core.reward_engine import apply_reward
from core.streak_engine import update_streak
from core.report_engine import generate_daily_report, generate_weekly_report
from core.time_utils import get_game_date
from config import DATABASE_URL


class ConsoleAdapter:
    def __init__(self, db_url: str = DATABASE_URL, quest_yaml: str = "data/quests.yaml"):
        init_db(db_url)
        Base.metadata.create_all(get_engine())
        self.session = get_session()
        self.quest_pool = load_quests(quest_yaml)
        self._simulated_date: date | None = None
        self._discord_id = "console_user"
        self._user: User | None = None

    @property
    def game_date(self) -> date:
        if self._simulated_date:
            return self._simulated_date
        return get_game_date()

    def _load_user(self):
        self._user = (
            self.session.query(User)
            .filter_by(discord_id=self._discord_id)
            .first()
        )

    def run(self):
        print("=" * 50)
        print("  Life RPG Console")
        print("=" * 50)
        print(f"  게임 날짜: {self.game_date}")
        print("  'help'를 입력하면 명령어 목록을 볼 수 있어요")
        print("=" * 50)

        self._load_user()

        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n안녕히 가세요!")
                break

            if not cmd:
                continue

            parts = cmd.split()
            command = parts[0]
            args = parts[1:]

            if command == "quit":
                print("안녕히 가세요!")
                break
            elif command == "help":
                self._help()
            elif command == "start":
                self._start()
            elif command == "quests":
                self._quests()
            elif command == "complete":
                self._complete(args)
            elif command == "skip":
                self._skip(args)
            elif command == "status":
                self._status()
            elif command == "report":
                self._report()
            elif command == "weekly":
                self._weekly()
            elif command == "next-day":
                self._next_day()
            elif command == "expire":
                self._expire()
            elif command == "reset":
                self._reset()
            else:
                print(f"알 수 없는 명령어: {command}. 'help'를 입력해보세요.")

    def _help(self):
        print("""
명령어 목록:
  start          온보딩 시작
  quests         오늘 퀘스트 보기
  complete <N>   N번 퀘스트 완료
  skip <N>       N번 퀘스트 건너뛰기
  status         현재 상태 확인
  report         일일 리포트 보기
  weekly         주간 리포트 보기
  next-day       다음 날로 이동 (테스트용)
  expire         만료 처리 실행 (테스트용)
  reset          데이터 초기화
  quit           종료
""")

    def _start(self):
        if self._user:
            print("이미 온보딩을 완료했어요. 'reset' 후 다시 시작할 수 있어요.")
            return

        print("\n모험을 시작할게요!\n")

        # Step 1: 목표 카테고리
        print("가장 바꾸고 싶은 영역을 선택하세요:")
        for i, cat in enumerate(GOAL_CATEGORIES, 1):
            print(f"  {i}. {cat}")
        choice = self._get_choice(len(GOAL_CATEGORIES))
        goal_category = GOAL_CATEGORIES[choice - 1]

        # Step 2: 주요 목표
        print(f"\n'{goal_category}' 영역에서 이루고 싶은 목표를 입력하세요:")
        goal_text = input("> ").strip()
        if not goal_text:
            goal_text = f"{goal_category} 개선하기"

        # Step 3: 하루 여유 시간
        print("\n하루 여유 시간은 얼마나 되나요?")
        budget_keys = list(TIME_BUDGETS.keys())
        for i, (key, label) in enumerate(TIME_BUDGETS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(budget_keys))
        time_budget = budget_keys[choice - 1]

        # Step 4: 에너지 상태
        print("\n현재 에너지 상태는?")
        energy_keys = list(ENERGY_LEVELS.keys())
        for i, (key, label) in enumerate(ENERGY_LEVELS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(energy_keys))
        energy_preference = energy_keys[choice - 1]

        # Step 5: 플레이 성향
        print("\n원하는 플레이 강도는?")
        diff_keys = list(DIFFICULTY_LEVELS.keys())
        for i, (key, label) in enumerate(DIFFICULTY_LEVELS.items(), 1):
            print(f"  {i}. {label}")
        choice = self._get_choice(len(diff_keys))
        difficulty_preference = diff_keys[choice - 1]

        self._user = create_user(
            self.session,
            discord_id=self._discord_id,
            nickname="모험가",
            goal_category=goal_category,
            goal_text=goal_text,
            time_budget=time_budget,
            energy_preference=energy_preference,
            difficulty_preference=difficulty_preference,
        )

        print(f"\n온보딩 완료! Lv.{self._user.level} 모험가로 시작합니다.")
        print("'quests'를 입력해서 첫 퀘스트를 받아보세요!")

    def _get_choice(self, max_val: int) -> int:
        while True:
            try:
                val = int(input("> ").strip())
                if 1 <= val <= max_val:
                    return val
            except ValueError:
                pass
            print(f"  1~{max_val} 사이의 숫자를 입력하세요.")

    def _quests(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        if not quests:
            quests = generate_daily_quests(
                self.session, self._user, self.quest_pool, self.game_date
            )

        print(f"\n오늘의 퀘스트 ({self.game_date})")
        print("-" * 40)
        for i, q in enumerate(quests, 1):
            state_icon = {"PENDING": " ", "COMPLETED": "V", "SKIPPED": "-", "EXPIRED": "X", "LATE_LOGGED": "~"}
            icon = state_icon.get(q.state, "?")
            print(f"  [{icon}] {i}. {q.title} ({q.difficulty}, {q.estimated_minutes}분)")
            print(f"      보상: +{q.reward_xp}XP, {q.reward_stat_type} +{q.reward_stat_value}")
        print("-" * 40)
        print("  'complete N' 또는 'skip N'으로 처리하세요")

    def _complete(self, args):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        if not args:
            print("퀘스트 번호를 입력하세요. 예: complete 1")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        try:
            idx = int(args[0]) - 1
            quest = quests[idx]
        except (ValueError, IndexError):
            print("잘못된 번호입니다.")
            return

        result = complete_quest(self.session, self._user, quest.id, self.game_date)
        if result["success"]:
            reward = apply_reward(
                self.session, self._user, quest.difficulty, quest.reward_stat_type
            )
            print(f"\n퀘스트 완료! '{quest.title}'")
            print(f"  +{reward['xp_gained']} XP")
            print(f"  {reward['stat_type']} +{reward['stat_gained']}")
            if reward["leveled_up"]:
                print(f"  레벨 업! Lv.{reward['new_level']}!")
            update_streak(self.session, self._user, self.game_date)
            print(f"  스트릭: {self._user.streak}일")
        elif result.get("reason") == "past_quest":
            print("이 퀘스트는 과거 기록이에요. 회고 기록만 남길 수 있어요.")
            ans = input("  기록할까요? (y/n) > ").strip().lower()
            if ans == "y":
                late_log_quest(self.session, self._user, quest.id)
                print("  회고 기록으로 남겼어요.")

    def _skip(self, args):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return
        if not args:
            print("퀘스트 번호를 입력하세요. 예: skip 1")
            return

        quests = get_today_quests(self.session, self._user, self.game_date)
        try:
            idx = int(args[0]) - 1
            quest = quests[idx]
        except (ValueError, IndexError):
            print("잘못된 번호입니다.")
            return

        skip_quest(self.session, self._user, quest.id)
        print(f"  '{quest.title}' 건너뛰었어요. 괜찮아요, 다른 걸 해봐요.")

    def _status(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        self.session.refresh(self._user)
        u = self._user
        s = u.stats

        print(f"\n{'=' * 40}")
        print(f"  {u.nickname} | Lv.{u.level}")
        print(f"  XP: {u.xp} / {u.level * 100}")
        print(f"  스트릭: {u.streak}일")
        print(f"  목표: {u.goal_text} ({u.goal_category})")
        print(f"{'=' * 40}")
        print(f"  체력(Health):    {s.health}")
        print(f"  집중(Focus):     {s.focus}")
        print(f"  실행(Execution): {s.execution}")
        print(f"  지식(Knowledge): {s.knowledge}")
        print(f"  재정(Finance):   {s.finance}")
        print(f"{'=' * 40}")

    def _report(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        report = generate_daily_report(self.session, self._user, self.game_date)
        print(f"\n오늘 결과 ({report.report_date})")
        print("-" * 40)
        print(f"  완료: {report.completed_count}개")
        print(f"  건너뜀: {report.skipped_count}개")
        print(f"  만료: {report.expired_count}개")
        if report.main_growth_stat:
            print(f"  가장 성장한 영역: {report.main_growth_stat}")
        print(f"  스트릭: {self._user.streak}일")
        print(f"  오늘의 흐름: {report.summary_text}")

    def _weekly(self):
        if not self._user:
            print("먼저 'start'로 온보딩을 완료하세요.")
            return

        today = self.game_date
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        report = generate_weekly_report(self.session, self._user, week_start, week_end)
        print(f"\n이번 주 요약 ({report.week_start} ~ {report.week_end})")
        print("-" * 40)
        print(f"  완료율: {report.completion_rate}%")
        if report.best_stat:
            print(f"  가장 성장한 영역: {report.best_stat}")
        if report.risk_pattern:
            print(f"  어려웠던 패턴: {report.risk_pattern}")
        print(f"  추천: {report.suggestion_text}")

    def _next_day(self):
        if self._simulated_date is None:
            self._simulated_date = self.game_date
        self._simulated_date += timedelta(days=1)
        print(f"\n다음 날로 이동했어요. 현재 게임 날짜: {self._simulated_date}")
        # 전날 만료 처리
        yesterday = self._simulated_date - timedelta(days=1)
        count = expire_pending_quests(self.session, yesterday)
        if count > 0:
            print(f"  어제 미완료 퀘스트 {count}개가 만료되었어요.")
        if self._user:
            update_streak(self.session, self._user, yesterday)

    def _expire(self):
        count = expire_pending_quests(self.session, self.game_date)
        print(f"  {self.game_date}의 PENDING 퀘스트 {count}개를 만료 처리했어요.")

    def _reset(self):
        if self._user:
            reset_user(self.session, self._discord_id)
            self._user = None
            self._simulated_date = None
            print("데이터를 초기화했어요. 'start'로 다시 시작할 수 있어요.")
        else:
            print("초기화할 데이터가 없어요.")
```

- [ ] **Step 2: console_main.py 구현**

```python
# console_main.py
from console.adapter import ConsoleAdapter


def main():
    adapter = ConsoleAdapter()
    adapter.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 콘솔 실행 테스트**

```bash
python console_main.py
```

Expected: REPL 시작, `help` 입력 시 명령어 목록 출력, `quit`로 종료 가능

- [ ] **Step 4: 온보딩 → 퀘스트 → 완료 → 리포트 수동 플로우 확인**

```
> start
  (카테고리 선택, 목표 입력, 시간/에너지/강도 선택)
> quests
  (3개 퀘스트 표시 확인)
> complete 1
  (완료 메시지 + XP/스탯 보상 확인)
> status
  (레벨, XP, 스탯 반영 확인)
> report
  (일일 리포트 확인)
> next-day
  (날짜 변경, 만료 처리 확인)
> quests
  (새 날짜 퀘스트 생성 확인)
> quit
```

- [ ] **Step 5: Commit**

```bash
git add console/adapter.py console_main.py
git commit -m "feat: add console adapter for testing without Discord"
```

---

## Task 11: Discord 봇 기본 세팅 + /start 명령어

**Files:**
- Create: `main.py`
- Create: `bot/cogs/start.py`
- Create: `bot/views/onboarding_views.py`

- [ ] **Step 1: main.py 구현**

```python
# main.py
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, DATABASE_URL
from core.database import init_db, get_engine
from core.models import Base

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced.")


async def setup():
    init_db(DATABASE_URL)
    Base.metadata.create_all(get_engine())
    await bot.load_extension("bot.cogs.start")


def main():
    import asyncio
    asyncio.run(setup())
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: bot/views/onboarding_views.py 구현**

```python
# bot/views/onboarding_views.py
import discord
from core.onboarding import (
    GOAL_CATEGORIES, TIME_BUDGETS, ENERGY_LEVELS, DIFFICULTY_LEVELS,
    create_user,
)
from core.database import get_session


class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat, value=cat)
            for cat in GOAL_CATEGORIES
        ]
        super().__init__(
            placeholder="가장 바꾸고 싶은 영역을 선택하세요",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.goal_category = self.values[0]
        await interaction.response.send_message(
            f"'{self.values[0]}' 선택! 이 영역에서 이루고 싶은 목표를 입력해주세요.",
            ephemeral=True,
        )
        self.view.stop()


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.goal_category = None
        self.add_item(CategorySelect())


class TimeBudgetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.time_budget = None

    @discord.ui.button(label="10분 이하", style=discord.ButtonStyle.secondary)
    async def short(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "short"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="10~30분", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "medium"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="30분 이상", style=discord.ButtonStyle.success)
    async def long(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "long"
        await interaction.response.defer()
        self.stop()


class EnergyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.energy = None

    @discord.ui.button(label="낮음", style=discord.ButtonStyle.secondary)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "low"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="보통", style=discord.ButtonStyle.primary)
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "normal"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="높음", style=discord.ButtonStyle.success)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "high"
        await interaction.response.defer()
        self.stop()


class DifficultyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.difficulty = None

    @discord.ui.button(label="아주 가볍게", style=discord.ButtonStyle.secondary)
    async def light(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "light"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="적당히", style=discord.ButtonStyle.primary)
    async def moderate(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "moderate"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="조금 빡세게", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "hard"
        await interaction.response.defer()
        self.stop()
```

- [ ] **Step 3: bot/cogs/start.py 구현**

```python
# bot/cogs/start.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.onboarding import create_user, is_onboarded, reset_user
from bot.views.onboarding_views import (
    CategoryView, TimeBudgetView, EnergyView, DifficultyView,
)


class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="Life RPG 모험을 시작합니다")
    async def start(self, interaction: discord.Interaction):
        session = get_session()
        discord_id = str(interaction.user.id)

        # 이미 등록된 유저면 리셋
        if is_onboarded(session, discord_id):
            reset_user(session, discord_id)

        await interaction.response.send_message(
            "모험을 시작할게요! 몇 가지 질문에 답해주세요.",
            ephemeral=True,
        )

        # Step 1: 카테고리
        cat_view = CategoryView()
        await interaction.followup.send(
            "**Step 1/4** 가장 바꾸고 싶은 영역은?",
            view=cat_view, ephemeral=True,
        )
        await cat_view.wait()
        if cat_view.goal_category is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        # Step 2: 목표 텍스트 (간단히 기본값 사용, Modal은 추후)
        goal_text = f"{cat_view.goal_category} 개선하기"

        # Step 3: 시간
        time_view = TimeBudgetView()
        await interaction.followup.send(
            "**Step 2/4** 하루 여유 시간은?",
            view=time_view, ephemeral=True,
        )
        await time_view.wait()
        if time_view.time_budget is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        # Step 4: 에너지
        energy_view = EnergyView()
        await interaction.followup.send(
            "**Step 3/4** 현재 에너지 상태는?",
            view=energy_view, ephemeral=True,
        )
        await energy_view.wait()
        if energy_view.energy is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        # Step 5: 난이도
        diff_view = DifficultyView()
        await interaction.followup.send(
            "**Step 4/4** 원하는 플레이 강도는?",
            view=diff_view, ephemeral=True,
        )
        await diff_view.wait()
        if diff_view.difficulty is None:
            await interaction.followup.send("시간 초과! `/start`로 다시 시작해주세요.", ephemeral=True)
            session.close()
            return

        # 유저 생성
        user = create_user(
            session,
            discord_id=discord_id,
            nickname=interaction.user.display_name,
            goal_category=cat_view.goal_category,
            goal_text=goal_text,
            time_budget=time_view.time_budget,
            energy_preference=energy_view.energy,
            difficulty_preference=diff_view.difficulty,
        )

        embed = discord.Embed(
            title="온보딩 완료!",
            description=f"Lv.{user.level} {user.nickname}으로 모험을 시작합니다!",
            color=discord.Color.green(),
        )
        embed.add_field(name="목표", value=f"{user.goal_category}: {user.goal_text}")
        embed.set_footer(text="곧 첫 퀘스트가 도착할 거예요!")

        await interaction.followup.send(embed=embed, ephemeral=True)
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(StartCog(bot))
```

- [ ] **Step 4: Commit**

```bash
git add main.py bot/cogs/start.py bot/views/onboarding_views.py
git commit -m "feat: add Discord bot setup with /start onboarding command"
```

---

## Task 12: Discord 퀘스트 UI (Persistent View)

**Files:**
- Create: `bot/views/quest_views.py`
- Create: `bot/cogs/quest_ui.py`

- [ ] **Step 1: bot/views/quest_views.py 구현**

```python
# bot/views/quest_views.py
import discord
from core.database import get_session
from core.models import User, DailyQuest
from core.quest_engine import complete_quest, skip_quest, late_log_quest
from core.reward_engine import apply_reward
from core.streak_engine import update_streak
from core.time_utils import get_game_date


class QuestActionView(discord.ui.View):
    """Persistent View — 봇 재시작 후에도 작동."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="완료했어요", style=discord.ButtonStyle.success,
        custom_id="quest:complete", emoji="\u2705",
    )
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "complete")

    @discord.ui.button(
        label="건너뛰기", style=discord.ButtonStyle.secondary,
        custom_id="quest:skip", emoji="\u23ed\ufe0f",
    )
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "skip")

    async def _handle_action(self, interaction: discord.Interaction, action: str):
        session = get_session()
        discord_id = str(interaction.user.id)
        game_date = get_game_date()

        user = session.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 온보딩을 완료해주세요.", ephemeral=True
            )
            session.close()
            return

        # 메시지 ID로 퀘스트 찾기
        message_id = str(interaction.message.id)
        quest = (
            session.query(DailyQuest)
            .filter_by(user_id=user.id, message_id=message_id)
            .first()
        )
        if not quest:
            await interaction.response.send_message(
                "이 퀘스트를 찾을 수 없어요.", ephemeral=True
            )
            session.close()
            return

        if action == "complete":
            result = complete_quest(session, user, quest.id, game_date)
            if result["success"]:
                reward = apply_reward(session, user, quest.difficulty, quest.reward_stat_type)
                update_streak(session, user, game_date)
                msg = f"퀘스트 완료! +{reward['xp_gained']}XP, {reward['stat_type']} +{reward['stat_gained']}"
                if reward["leveled_up"]:
                    msg += f"\n레벨 업! Lv.{reward['new_level']}!"
                msg += f"\n스트릭: {user.streak}일"
                await interaction.response.edit_message(
                    content=f"~~{quest.title}~~ **완료!**", view=None
                )
                await interaction.followup.send(msg, ephemeral=True)
            elif result.get("reason") == "past_quest":
                await interaction.response.send_message(
                    "이 퀘스트는 과거 기록이에요. 회고 기록으로만 남길 수 있어요.",
                    view=LateLogView(quest.id),
                    ephemeral=True,
                )
        elif action == "skip":
            skip_quest(session, user, quest.id)
            await interaction.response.edit_message(
                content=f"~~{quest.title}~~ 건너뜀", view=None
            )

        session.close()


class LateLogView(discord.ui.View):
    def __init__(self, quest_id: int):
        super().__init__(timeout=120)
        self.quest_id = quest_id

    @discord.ui.button(label="기록만 하기", style=discord.ButtonStyle.secondary)
    async def late_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = get_session()
        discord_id = str(interaction.user.id)
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if user:
            late_log_quest(session, user, self.quest_id)
            await interaction.response.edit_message(
                content="회고 기록으로 남겼어요.", view=None
            )
        session.close()

    @discord.ui.button(label="오늘 퀘스트 보기", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="곧 오늘 퀘스트가 도착할 거예요!", view=None
        )
```

- [ ] **Step 2: bot/cogs/quest_ui.py 구현**

```python
# bot/cogs/quest_ui.py
import discord
from discord.ext import commands
from core.database import get_session
from core.models import User
from core.quest_engine import generate_daily_quests, get_today_quests
from core.quest_loader import load_quests
from core.time_utils import get_game_date
from bot.views.quest_views import QuestActionView


class QuestUICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quest_pool = load_quests("data/quests.yaml")

    async def cog_load(self):
        self.bot.add_view(QuestActionView())

    async def send_daily_quests(self, user_discord_id: str):
        """특정 유저에게 DM으로 오늘 퀘스트를 보낸다."""
        session = get_session()
        user = session.query(User).filter_by(discord_id=user_discord_id).first()
        if not user or user.status != "active":
            session.close()
            return

        game_date = get_game_date()
        quests = get_today_quests(session, user, game_date)
        if not quests:
            quests = generate_daily_quests(session, user, self.quest_pool, game_date)

        discord_user = await self.bot.fetch_user(int(user_discord_id))
        if not discord_user:
            session.close()
            return

        for quest in quests:
            if quest.state != "PENDING":
                continue

            embed = discord.Embed(
                title=quest.title,
                description=quest.description,
                color=discord.Color.blue(),
            )
            embed.add_field(name="난이도", value=quest.difficulty, inline=True)
            embed.add_field(name="소요 시간", value=f"{quest.estimated_minutes}분", inline=True)
            embed.add_field(
                name="보상",
                value=f"+{quest.reward_xp}XP, {quest.reward_stat_type} +{quest.reward_stat_value}",
                inline=True,
            )

            view = QuestActionView()
            msg = await discord_user.send(embed=embed, view=view)
            quest.message_id = str(msg.id)

        session.commit()
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestUICog(bot))
```

- [ ] **Step 3: main.py에 quest_ui cog 추가**

`main.py`의 `setup()` 함수에 추가:

```python
await bot.load_extension("bot.cogs.quest_ui")
```

- [ ] **Step 4: Commit**

```bash
git add bot/views/quest_views.py bot/cogs/quest_ui.py main.py
git commit -m "feat: add quest UI with persistent views and DM delivery"
```

---

## Task 13: 자동 스케줄러

**Files:**
- Create: `bot/scheduler.py`

- [ ] **Step 1: 구현**

```python
# bot/scheduler.py
import discord
from discord.ext import commands, tasks
from datetime import time, datetime
from core.database import get_session
from core.models import User
from core.quest_engine import expire_pending_quests
from core.streak_engine import update_streak
from core.report_engine import generate_daily_report, generate_weekly_report
from core.time_utils import get_game_date
from config import DAY_BOUNDARY_HOUR, MORNING_QUEST_HOUR, EVENING_REPORT_HOUR, WEEKLY_REPORT_DAY
from datetime import timedelta


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.morning_task.start()
        self.evening_task.start()
        self.weekly_task.start()
        self.expire_task.start()

    async def cog_unload(self):
        self.morning_task.cancel()
        self.evening_task.cancel()
        self.weekly_task.cancel()
        self.expire_task.cancel()

    @tasks.loop(time=time(hour=DAY_BOUNDARY_HOUR, minute=0))
    async def expire_task(self):
        """새벽 4시: 전날 PENDING 퀘스트 만료 + 스트릭 업데이트."""
        session = get_session()
        yesterday = get_game_date() - timedelta(days=1)
        expire_pending_quests(session, yesterday)

        users = session.query(User).filter_by(status="active").all()
        for user in users:
            update_streak(session, user, yesterday)

        session.close()

    @tasks.loop(time=time(hour=MORNING_QUEST_HOUR, minute=0))
    async def morning_task(self):
        """아침 8시: 퀘스트 발송."""
        quest_cog = self.bot.get_cog("QuestUICog")
        if not quest_cog:
            return

        session = get_session()
        users = session.query(User).filter_by(status="active").all()
        for user in users:
            await quest_cog.send_daily_quests(user.discord_id)
        session.close()

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0))
    async def evening_task(self):
        """저녁 9시: 일일 리포트 발송."""
        session = get_session()
        game_date = get_game_date()
        users = session.query(User).filter_by(status="active").all()

        for user in users:
            report = generate_daily_report(session, user, game_date)
            try:
                discord_user = await self.bot.fetch_user(int(user.discord_id))
                embed = discord.Embed(
                    title=f"오늘 결과 ({report.report_date})",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="완료", value=f"{report.completed_count}개", inline=True)
                embed.add_field(name="건너뜀", value=f"{report.skipped_count}개", inline=True)
                embed.add_field(name="만료", value=f"{report.expired_count}개", inline=True)
                if report.main_growth_stat:
                    embed.add_field(name="가장 성장한 영역", value=report.main_growth_stat)
                embed.add_field(name="스트릭", value=f"{user.streak}일")
                embed.set_footer(text=report.summary_text)
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass

        session.close()

    @tasks.loop(time=time(hour=EVENING_REPORT_HOUR, minute=0))
    async def weekly_task(self):
        """일요일 저녁 9시: 주간 리포트 발송."""
        game_date = get_game_date()
        if game_date.weekday() != WEEKLY_REPORT_DAY:
            return

        session = get_session()
        week_start = game_date - timedelta(days=6)
        week_end = game_date

        users = session.query(User).filter_by(status="active").all()
        for user in users:
            report = generate_weekly_report(session, user, week_start, week_end)
            try:
                discord_user = await self.bot.fetch_user(int(user.discord_id))
                embed = discord.Embed(
                    title=f"이번 주 요약 ({report.week_start} ~ {report.week_end})",
                    color=discord.Color.purple(),
                )
                embed.add_field(name="완료율", value=f"{report.completion_rate}%")
                if report.best_stat:
                    embed.add_field(name="가장 성장한 영역", value=report.best_stat)
                if report.risk_pattern:
                    embed.add_field(name="어려웠던 패턴", value=report.risk_pattern)
                embed.set_footer(text=report.suggestion_text)
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass

        session.close()

    @expire_task.before_loop
    @morning_task.before_loop
    @evening_task.before_loop
    @weekly_task.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
```

- [ ] **Step 2: main.py에 scheduler cog 추가**

`main.py`의 `setup()` 함수에 추가:

```python
await bot.load_extension("bot.scheduler")
```

- [ ] **Step 3: Commit**

```bash
git add bot/scheduler.py main.py
git commit -m "feat: add automated scheduler for quests, reports, and expiry"
```

---

## Task 14: /status, /goal, /pause 명령어

**Files:**
- Create: `bot/cogs/status.py`
- Create: `bot/cogs/goal.py`
- Create: `bot/cogs/pause.py`

- [ ] **Step 1: bot/cogs/status.py 구현**

```python
# bot/cogs/status.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="현재 상태를 확인합니다")
    async def status(self, interaction: discord.Interaction):
        session = get_session()
        user = session.query(User).filter_by(
            discord_id=str(interaction.user.id)
        ).first()

        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 시작해주세요.", ephemeral=True
            )
            session.close()
            return

        s = user.stats
        embed = discord.Embed(
            title=f"{user.nickname} | Lv.{user.level}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="XP", value=f"{user.xp} / {user.level * 100}", inline=True)
        embed.add_field(name="스트릭", value=f"{user.streak}일", inline=True)
        embed.add_field(name="상태", value=user.status, inline=True)
        embed.add_field(name="목표", value=f"{user.goal_category}: {user.goal_text}", inline=False)
        embed.add_field(
            name="스탯",
            value=(
                f"체력: {s.health} | 집중: {s.focus} | 실행: {s.execution}\n"
                f"지식: {s.knowledge} | 재정: {s.finance}"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
```

- [ ] **Step 2: bot/cogs/goal.py 구현**

```python
# bot/cogs/goal.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User
from core.onboarding import GOAL_CATEGORIES


class GoalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="goal", description="목표를 변경합니다")
    @app_commands.describe(
        category="목표 카테고리",
        text="구체적인 목표 (선택)",
    )
    @app_commands.choices(category=[
        app_commands.Choice(name=cat, value=cat) for cat in GOAL_CATEGORIES
    ])
    async def goal(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        text: str | None = None,
    ):
        session = get_session()
        user = session.query(User).filter_by(
            discord_id=str(interaction.user.id)
        ).first()

        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 시작해주세요.", ephemeral=True
            )
            session.close()
            return

        user.goal_category = category.value
        if text:
            user.goal_text = text
        else:
            user.goal_text = f"{category.value} 개선하기"
        session.commit()

        await interaction.response.send_message(
            f"목표가 변경되었어요! → {user.goal_category}: {user.goal_text}",
            ephemeral=True,
        )
        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(GoalCog(bot))
```

- [ ] **Step 3: bot/cogs/pause.py 구현**

```python
# bot/cogs/pause.py
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.models import User


class PauseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pause", description="쉬기 모드를 전환합니다")
    async def pause(self, interaction: discord.Interaction):
        session = get_session()
        user = session.query(User).filter_by(
            discord_id=str(interaction.user.id)
        ).first()

        if not user:
            await interaction.response.send_message(
                "`/start`로 먼저 시작해주세요.", ephemeral=True
            )
            session.close()
            return

        if user.status == "active":
            user.status = "paused"
            session.commit()
            await interaction.response.send_message(
                "쉬기 모드로 전환했어요. 알림이 줄어들고, 회복 퀘스트 위주로 추천돼요.\n"
                "다시 `/pause`를 누르면 복귀할 수 있어요.",
                ephemeral=True,
            )
        else:
            user.status = "active"
            session.commit()
            await interaction.response.send_message(
                "다시 활성 모드로 돌아왔어요! 내일 아침부터 퀘스트가 다시 도착해요.",
                ephemeral=True,
            )

        session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(PauseCog(bot))
```

- [ ] **Step 4: main.py에 cog 추가**

`main.py`의 `setup()` 함수에 추가:

```python
await bot.load_extension("bot.cogs.status")
await bot.load_extension("bot.cogs.goal")
await bot.load_extension("bot.cogs.pause")
```

- [ ] **Step 5: Commit**

```bash
git add bot/cogs/status.py bot/cogs/goal.py bot/cogs/pause.py main.py
git commit -m "feat: add /status, /goal, /pause slash commands"
```

---

## Task 15: 전체 통합 테스트 (콘솔)

**Files:**
- No new files

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 2: 콘솔 통합 테스트 — 전체 루프 시나리오**

```bash
python console_main.py
```

다음 시나리오 수행:
1. `start` → 온보딩 완료
2. `quests` → 퀘스트 3개 확인
3. `complete 1` → 완료 + 보상 확인
4. `complete 2` → 완료 + 보상 확인
5. `skip 3` → 건너뛰기
6. `status` → 레벨/XP/스탯 반영 확인
7. `report` → 일일 리포트 확인 (완료 2, 건너뜀 1)
8. `next-day` → 다음 날 이동 + 만료 처리
9. `quests` → 새로운 퀘스트 3개 생성 확인
10. `next-day` 3회 → 스트릭 변화 확인
11. `weekly` → 주간 리포트 확인
12. `reset` → 초기화 확인

- [ ] **Step 3: Commit (테스트 결과 문제 없으면)**

```bash
git add -A
git commit -m "chore: verify full integration via console adapter"
```
