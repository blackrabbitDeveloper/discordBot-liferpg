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
