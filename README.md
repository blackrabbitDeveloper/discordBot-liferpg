# Life RPG Discord Bot

현실의 행동을 일일 퀘스트로 변환하여 삶을 게임처럼 운영하게 만드는 Discord Bot.

## 핵심 기능

- **온보딩** — `/start`로 목표/에너지/난이도 설정, 즉시 첫 퀘스트 수령
- **일일 퀘스트** — 매일 아침 DM으로 오늘 플로우 선택(이대로/가볍게/회복/쉬기) → 맞춤 퀘스트 3개
- **성장 시스템** — XP, 레벨, 5개 스탯(체력/집중/실행/지식/재정), 스트릭
- **리포트** — 일일(저녁 9시)/주간(일요일) 자동 DM
- **행동 분석** — `/analyze`로 AI 분석용 데이터 JSON export

## 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| 프레임워크 | discord.py 2.3+ |
| ORM | SQLAlchemy 2.0+ |
| DB | SQLite(로컬) / PostgreSQL(배포) |
| 스케줄러 | discord.ext.tasks (KST) |
| 퀘스트 데이터 | YAML |
| 배포 | Railway |

## 프로젝트 구조

```
├── main.py              # Discord 봇 진입점
├── console_main.py      # 콘솔 테스트 진입점
├── config.py            # 환경 설정
├── data/
│   └── quests.yaml      # 퀘스트 템플릿 (8카테고리 49개)
├── core/                # 순수 비즈니스 로직 (Discord 의존 없음)
│   ├── models.py        # SQLAlchemy 모델
│   ├── database.py      # DB 세션 관리
│   ├── quest_engine.py  # 퀘스트 추천/완료/교체/만료
│   ├── quest_loader.py  # YAML 로더 + 필터
│   ├── reward_engine.py # XP/스탯/레벨업
│   ├── streak_engine.py # 스트릭 (보호/감소/리셋)
│   ├── onboarding.py    # 유저 생성/리셋
│   ├── report_engine.py # 일일/주간 리포트
│   ├── time_utils.py    # 새벽 4시 기준 게임 날짜
│   ├── activity_logger.py # 행동 로그
│   └── analytics.py     # AI 분석 데이터 생성
├── bot/                 # Discord 인터페이스
│   ├── cogs/            # 슬래시 명령어
│   │   ├── start.py     # /start 온보딩
│   │   ├── status.py    # /status
│   │   ├── goal.py      # /goal
│   │   ├── pause.py     # /pause
│   │   ├── quest_ui.py  # 퀘스트 DM 발송
│   │   └── admin.py     # /analyze (개발자 전용)
│   ├── views/           # UI 컴포넌트
│   │   ├── onboarding_views.py
│   │   └── quest_views.py
│   └── scheduler.py     # 자동 스케줄 (KST)
├── console/             # 콘솔 테스트 어댑터
│   └── adapter.py
└── tests/               # 단위 테스트 (67개)
```

## 로컬 개발

### 설치

```bash
git clone https://github.com/blackrabbitDeveloper/discordBot-liferpg.git
cd discordBot-liferpg
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Mac/Linux
pip install -r requirements.txt
```

### 환경변수

`.env` 파일 생성:

```
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///data/life_rpg.db
```

### 콘솔 테스트 (Discord 없이)

```bash
python console_main.py
```

```
> start          # 온보딩
> quests         # 오늘 퀘스트 (플로우 선택 포함)
> complete 1     # 1번 퀘스트 완료
> skip 2         # 건너뛰기
> replace 3      # 다른 걸로 교체
> status         # 상태 확인
> report         # 일일 리포트
> weekly         # 주간 리포트
> next-day       # 다음 날 시뮬레이션
> logs           # 활동 로그
> analyze        # AI 분석 데이터
> reset          # 데이터 초기화
> quit           # 종료
```

### Discord 봇 실행

```bash
python main.py
```

### 테스트

```bash
pytest tests/ -v
```

## 배포 (Railway)

1. Railway에서 GitHub repo 연결
2. PostgreSQL 플러그인 추가 (DATABASE_URL 자동 주입)
3. 환경변수에 `DISCORD_TOKEN` 추가
4. 자동 빌드 & 배포

`railway.json`과 `Procfile`이 포함되어 있어 설정 없이 바로 배포됩니다.

## Discord 봇 권한

봇 초대 시 필요한 권한:

- Send Messages
- Embed Links
- Use Slash Commands
- Send Messages in Threads

## 게임 메커닉

### 보상

| 난이도 | XP | 스탯 |
|--------|-----|------|
| easy | +5 | +1 |
| normal | +10 | +2 |
| hard | +20 | +3 |

### 레벨업

필요 XP = 현재 레벨 x 100 (Lv1→2: 100XP, Lv2→3: 200XP ...)

### 스트릭

- 1개 이상 완료 → 스트릭 +1
- 1일 미완료 → 보호 (유지)
- 2일 연속 → 감소 (-1)
- 3일 연속 → 리셋 (0)
- "쉬어갈래요" 선택 → 보호 (유지)

### 하루 기준

새벽 4시 KST (게임 업계 표준)

## 라이선스

Private
