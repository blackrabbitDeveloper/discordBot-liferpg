# Life RPG Discord Bot - 기술 설계서

## 1. 개요

`life_rpg_discord_bot_mvp_design.md`(제품 설계서) 기반으로 구현에 필요한 기술적 결정사항과 상세 설계를 정의한다.

---

## 2. 확정된 기술 결정사항

| 항목 | 결정 |
|------|------|
| 메시지 방식 | 하이브리드 (퀘스트/리포트 = DM, 소셜/공지 = 서버 채널) |
| 프레임워크 | discord.py |
| DB | SQLite + SQLAlchemy ORM (→ PostgreSQL 전환 대비) |
| 스케줄러 | discord.ext.tasks |
| 퀘스트 템플릿 | YAML 파일 우선 → 이후 DB(quest_templates) 전환 |
| 스탯 체계 | 5개: Health, Focus, Execution, Knowledge, Finance |
| 보상 체계 | 난이도별 고정 보상 + 레벨업 필요 XP 증가 (Lv x 100) |
| 하루 기준 시각 | 새벽 4시 (게임 업계 표준) |
| 온보딩 이탈 | 항상 처음부터 (`/start` 재실행 시 리셋) |
| 동시 퀘스트 | 3개 독립 선택/완료 가능 |
| 테스트 방식 | 콘솔 어댑터로 Discord 없이 핵심 로직 테스트 가능 |

---

## 3. 프로젝트 구조

```
discordBot-routine-tracker/
├── main.py                    # 진입점 (Discord 봇 실행)
├── console_main.py            # 콘솔 테스트 진입점
├── config.py                  # 환경 설정 (토큰, DB 경로 등)
├── requirements.txt
├── data/
│   └── quests.yaml            # 퀘스트 템플릿 데이터
├── core/                      # 순수 비즈니스 로직 (Discord 의존성 없음)
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy 모델 정의
│   ├── database.py            # DB 세션 관리
│   ├── quest_engine.py        # 퀘스트 추천/상태 관리
│   ├── reward_engine.py       # XP/스탯/레벨업 계산
│   ├── streak_engine.py       # 스트릭 로직
│   ├── report_engine.py       # 일일/주간 리포트 생성
│   └── onboarding.py          # 온보딩 플로우 로직
├── bot/                       # Discord 인터페이스
│   ├── __init__.py
│   ├── cogs/
│   │   ├── __init__.py
│   │   ├── start.py           # /start 명령어 + 온보딩 UI
│   │   ├── status.py          # /status 명령어
│   │   ├── goal.py            # /goal 명령어
│   │   ├── pause.py           # /pause 명령어
│   │   └── quest_ui.py        # 퀘스트 버튼 인터랙션
│   ├── views/                 # discord.ui.View 컴포넌트
│   │   ├── __init__.py
│   │   ├── onboarding_views.py
│   │   ├── quest_views.py     # Persistent View 포함
│   │   └── report_views.py
│   └── scheduler.py           # 자동 발송 스케줄러
├── console/                   # 콘솔 테스트 어댑터
│   ├── __init__.py
│   └── adapter.py             # 터미널 기반 인터랙션
└── tests/
    ├── __init__.py
    ├── test_quest_engine.py
    ├── test_reward_engine.py
    ├── test_streak_engine.py
    └── test_report_engine.py
```

### 3.1 계층 분리 원칙

- `core/` — Discord에 대한 의존성이 전혀 없다. 순수 Python + SQLAlchemy만 사용.
- `bot/` — `core/`를 호출하고 결과를 Discord UI(Embed, Button, View)로 변환한다.
- `console/` — `core/`를 호출하고 결과를 터미널 텍스트로 변환한다.

이 구조 덕분에 `core/`의 모든 로직을 Discord 없이 단위 테스트하고, 콘솔에서 직접 실행할 수 있다.

---

## 4. 데이터 모델 (SQLAlchemy)

### 4.1 users

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | 내부 ID |
| discord_id | String, unique | Discord 유저 ID |
| nickname | String | 표시 이름 |
| goal_category | String | 목표 카테고리 |
| goal_text | String | 목표 텍스트 |
| time_budget | String | 하루 여유 시간 (short/medium/long) |
| energy_preference | String | 에너지 상태 (low/normal/high) |
| difficulty_preference | String | 플레이 강도 (light/moderate/hard) |
| level | Integer, default=1 | 현재 레벨 |
| xp | Integer, default=0 | 현재 누적 XP |
| streak | Integer, default=0 | 현재 스트릭 |
| streak_protected | Boolean, default=False | 스트릭 보호 상태 (1일 유예) |
| status | String, default='active' | active / paused |
| created_at | DateTime | 생성 시각 |
| updated_at | DateTime | 수정 시각 |

### 4.2 user_stats

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | |
| user_id | Integer, FK(users.id) | |
| health | Integer, default=0 | 건강 + 회복 |
| focus | Integer, default=0 | 집중 |
| execution | Integer, default=0 | 일/커리어 + 정리/생활 |
| knowledge | Integer, default=0 | 공부 + 창작 |
| finance | Integer, default=0 | 돈관리 |

### 4.3 daily_quests

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | |
| user_id | Integer, FK(users.id) | |
| quest_date | Date | 퀘스트 날짜 |
| category | String | 카테고리 |
| title | String | 퀘스트 제목 |
| description | String | 설명 |
| estimated_minutes | Integer | 예상 소요 시간 |
| difficulty | String | easy/normal/hard |
| reward_xp | Integer | XP 보상 |
| reward_stat_type | String | 보상 스탯 종류 |
| reward_stat_value | Integer | 보상 스탯 수치 |
| state | String, default='PENDING' | PENDING/COMPLETED/SKIPPED/EXPIRED/LATE_LOGGED |
| message_id | String, nullable | Discord 메시지 ID (버튼 추적용) |
| created_at | DateTime | |
| completed_at | DateTime, nullable | |

### 4.4 quest_logs

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | |
| quest_id | Integer, FK(daily_quests.id) | |
| user_id | Integer, FK(users.id) | |
| action_type | String | completed/skipped/expired/late_logged |
| action_time | DateTime | |
| note | String, nullable | |

### 4.5 daily_reports

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | |
| user_id | Integer, FK(users.id) | |
| report_date | Date | |
| completed_count | Integer | |
| skipped_count | Integer | |
| expired_count | Integer | |
| main_growth_stat | String | |
| summary_text | String | |
| created_at | DateTime | |

### 4.6 weekly_reports

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer, PK | |
| user_id | Integer, FK(users.id) | |
| week_start | Date | |
| week_end | Date | |
| completion_rate | Float | |
| best_stat | String | |
| risk_pattern | String | |
| suggestion_text | String | |
| created_at | DateTime | |

---

## 5. 스탯-카테고리 매핑

```python
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
```

---

## 6. 보상 체계

### 6.1 난이도별 보상

| 난이도 | XP | 스탯 |
|--------|-----|------|
| easy | 5 | +1 |
| normal | 10 | +2 |
| hard | 20 | +3 |

### 6.2 레벨업 공식

```
필요 XP = 현재 레벨 x 100
```

- Lv1 → Lv2: 100 XP
- Lv2 → Lv3: 200 XP
- Lv3 → Lv4: 300 XP
- ...

레벨업 시 XP는 초과분을 이월한다.
예: Lv1에서 XP 120 획득 → Lv2로 레벨업, 잔여 XP = 20

---

## 7. 스트릭 로직

### 7.1 하루 기준

새벽 4시를 하루 경계로 사용한다.

```python
from datetime import datetime, timedelta, time

def get_game_date(now: datetime) -> date:
    """새벽 4시 기준 게임 날짜 반환"""
    boundary = time(4, 0)
    if now.time() < boundary:
        return (now - timedelta(days=1)).date()
    return now.date()
```

### 7.2 스트릭 규칙

- 당일 1개 이상 완료 → 스트릭 유지/증가
- 1일 미완료 → 스트릭 보호 (streak_protected = True)
- 2일 연속 미완료 → 스트릭 감소 (streak -= 1, 최소 0)
- 3일 연속 미완료 → 스트릭 리셋 (streak = 0)

---

## 8. 퀘스트 추천 로직

### 8.1 입력

- 사용자의 goal_category
- time_budget (short: 10분 이하 / medium: 10~30분 / long: 30분 이상)
- energy_preference (low / normal / high)
- difficulty_preference (light / moderate / hard)
- 최근 3일 완료율

### 8.2 로직

1. YAML에서 goal_category에 해당하는 퀘스트 필터링
2. time_budget에 맞는 estimated_minutes 필터링
3. energy/difficulty에 따라 난이도 조정
4. 최근 완료율이 낮으면 (< 50%) 난이도 자동 완화
5. 필터링된 목록에서 3개 랜덤 선택 (최근 완료한 퀘스트 제외)

### 8.3 출력

3개의 퀘스트 (각각: 제목, 설명, 예상 시간, 난이도, 예상 보상)

---

## 9. 자동 스케줄러

모든 시각은 새벽 4시 기준 하루 경계를 따른다.

| 작업 | 시각 | 내용 |
|------|------|------|
| 퀘스트 만료 처리 | 매일 04:00 | 전날 PENDING 퀘스트 → EXPIRED |
| 아침 퀘스트 발송 | 매일 08:00 | 각 유저에게 DM으로 오늘 퀘스트 3개 전송 |
| 일일 리포트 | 매일 21:00 | 각 유저에게 DM으로 일일 리포트 전송 |
| 주간 리포트 | 매주 일요일 21:00 | 각 유저에게 DM으로 주간 리포트 전송 |

paused 상태 유저는 스케줄러에서 제외한다.

---

## 10. 퀘스트 템플릿 (YAML 구조)

```yaml
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

      - title: "20분 유산소 운동"
        description: "걷기, 달리기, 자전거 중 하나를 선택하세요"
        estimated_minutes: 20
        difficulty: hard
        energy: [normal, high]
        time_budget: [medium, long]

  # ... 나머지 카테고리도 동일 구조
```

---

## 11. 콘솔 어댑터

Discord 없이 `core/` 로직을 테스트하기 위한 터미널 인터페이스.

### 11.1 실행

```bash
python console_main.py
```

### 11.2 지원 기능

- 온보딩 플로우 (텍스트 입력으로 단계별 진행)
- 퀘스트 추천 확인
- 퀘스트 완료/건너뛰기
- 스탯/레벨/스트릭 확인
- 일일/주간 리포트 조회
- 시간 시뮬레이션 (날짜를 변경하여 다음 날 테스트)

### 11.3 콘솔 명령어

```
[Life RPG Console]
> start          # 온보딩 시작
> quests         # 오늘 퀘스트 보기
> complete 1     # 1번 퀘스트 완료
> skip 2         # 2번 퀘스트 건너뛰기
> status         # 현재 상태 확인
> report         # 일일 리포트 보기
> weekly         # 주간 리포트 보기
> next-day       # 다음 날로 이동 (테스트용)
> expire         # 만료 처리 실행 (테스트용)
> reset          # 데이터 초기화
> quit           # 종료
```

### 11.4 시간 시뮬레이션

콘솔 모드에서는 `next-day` 명령으로 가상 시간을 넘길 수 있다. 이를 통해:
- 스트릭 보호 → 감소 → 리셋 흐름 검증
- 퀘스트 만료 처리 검증
- 일일/주간 리포트 생성 검증

---

## 12. Discord 버튼 인터랙션

### 12.1 Persistent View

퀘스트 버튼은 봇 재시작 후에도 작동해야 하므로 `discord.ui.View`에 `timeout=None`을 설정하고, 봇 시작 시 `bot.add_view()`로 등록한다.

### 12.2 버튼 custom_id 규칙

```
quest:{quest_id}:{action}
```

예: `quest:42:complete`, `quest:42:skip`

### 12.3 과거 퀘스트 분기

버튼 클릭 시 `quest.quest_date`와 현재 게임 날짜를 비교하여:
- 같은 날 → 정상 처리
- 다른 날 → 회고 기록 안내 + 오늘 퀘스트 보기 버튼 제공

---

## 13. 메시지 전달 정책

| 내용 | 채널 |
|------|------|
| 퀘스트 추천/완료/건너뛰기 | DM |
| 일일 리포트 | DM |
| 주간 리포트 | DM |
| 레벨업 알림 | DM + 서버 채널 (축하 메시지) |
| 길드 진행도 (MVP 이후) | 서버 채널 |
| 공지사항 | 서버 채널 |

---

## 14. 환경 설정

```python
# config.py
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/life_rpg.db")
DAY_BOUNDARY_HOUR = 4  # 새벽 4시
MORNING_QUEST_HOUR = 8
EVENING_REPORT_HOUR = 21
WEEKLY_REPORT_DAY = 6  # 일요일 (0=월요일)
```

---

## 15. 의존성

```
discord.py>=2.3
SQLAlchemy>=2.0
PyYAML>=6.0
python-dotenv>=1.0
```

---

## 16. 개발 순서

### Phase 1: 기반 + 온보딩
- 프로젝트 세팅 (구조, 의존성, config)
- SQLAlchemy 모델 정의
- 온보딩 로직 (`core/onboarding.py`)
- 콘솔 어댑터 기본 (`console/adapter.py`)
- `/start` 명령어 + Discord 온보딩 UI

### Phase 2: 퀘스트 루프
- YAML 퀘스트 템플릿 작성
- 퀘스트 추천 엔진 (`core/quest_engine.py`)
- 보상 엔진 (`core/reward_engine.py`)
- 퀘스트 버튼 UI (Persistent View)
- 콘솔에서 퀘스트 플로우 테스트

### Phase 3: 스트릭 + 리포트
- 스트릭 엔진 (`core/streak_engine.py`)
- 과거 퀘스트 분기 처리
- 일일 리포트 엔진 (`core/report_engine.py`)
- 주간 리포트 엔진
- 자동 스케줄러 (`bot/scheduler.py`)

### Phase 4: 마무리
- `/status`, `/goal`, `/pause` 명령어
- 시간 시뮬레이션 테스트
- 엣지케이스 처리
- 배포 준비
