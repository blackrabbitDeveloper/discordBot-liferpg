# core/analytics.py
import json
from datetime import date, timedelta, datetime
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from core.models import User, UserActivityLog, DailyQuest


def generate_analytics(session: Session, period_days: int = 7) -> dict:
    """AI 분석용 데이터를 생성한다."""
    today = date.today()
    start_date = today - timedelta(days=period_days)

    logs = (
        session.query(UserActivityLog)
        .filter(UserActivityLog.created_at >= datetime.combine(start_date, datetime.min.time()))
        .all()
    )

    total_users = session.query(User).count()
    active_users = session.query(User).filter_by(status="active").count()

    # 온보딩 분석
    onboarding_starts = sum(1 for l in logs if l.action == "onboarding_start")
    onboarding_completes = sum(1 for l in logs if l.action == "onboarding_complete")
    onboarding_rate = (onboarding_completes / onboarding_starts * 100) if onboarding_starts > 0 else 0

    # 플로우 선택 분포
    flow_dist = Counter()
    for l in logs:
        if l.action == "morning_flow_choice" and l.detail:
            d = json.loads(l.detail)
            flow_dist[d.get("choice", "unknown")] += 1

    # 퀘스트 분석
    completed_cats = Counter()
    skipped_cats = Counter()
    replaced_quests = Counter()
    for l in logs:
        if l.detail:
            d = json.loads(l.detail)
            if l.action == "quest_completed":
                completed_cats[d.get("category", "")] += 1
            elif l.action == "quest_skipped":
                skipped_cats[d.get("category", "")] += 1
            elif l.action == "quest_replaced":
                replaced_quests[d.get("old_title", "")] += 1

    # 일일 완료율
    quest_logs_completed = sum(1 for l in logs if l.action == "quest_completed")
    quest_logs_total = sum(1 for l in logs if l.action in ("quest_completed", "quest_skipped", "quest_expired"))
    avg_completion = (quest_logs_completed / quest_logs_total * 100) if quest_logs_total > 0 else 0

    # 스트릭 평균
    users = session.query(User).filter_by(status="active").all()
    avg_streak = sum(u.streak for u in users) / len(users) if users else 0

    # 위험 유저 (스트릭 0 + 최근 활동 없음)
    risk_users = []
    for u in users:
        if u.streak == 0:
            recent = (
                session.query(DailyQuest)
                .filter(
                    DailyQuest.user_id == u.id,
                    DailyQuest.quest_date >= start_date,
                    DailyQuest.state == "COMPLETED",
                )
                .count()
            )
            if recent == 0:
                risk_users.append({"user_id": u.id, "nickname": u.nickname, "reason": "스트릭 0 + 최근 완료 없음"})

    # 난이도별 완료율
    difficulty_stats = defaultdict(lambda: {"completed": 0, "total": 0})
    for l in logs:
        if l.action in ("quest_completed", "quest_skipped", "quest_expired") and l.detail:
            d = json.loads(l.detail)
            diff = d.get("difficulty", "unknown")
            difficulty_stats[diff]["total"] += 1
            if l.action == "quest_completed":
                difficulty_stats[diff]["completed"] += 1

    difficulty_rates = {
        k: round(v["completed"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        for k, v in difficulty_stats.items()
    }

    # 시간대별 완료 패턴
    hour_dist = Counter()
    for l in logs:
        if l.action == "quest_completed":
            hour_dist[l.created_at.hour] += 1

    # 가장 교체 많은 퀘스트 Top 5
    most_replaced = [q for q, _ in replaced_quests.most_common(5)]

    return {
        "period": f"{start_date} ~ {today}",
        "total_users": total_users,
        "active_users": active_users,
        "summary": {
            "onboarding_completion_rate": round(onboarding_rate, 1),
            "avg_daily_completion_rate": round(avg_completion, 1),
            "most_completed_category": completed_cats.most_common(1)[0][0] if completed_cats else None,
            "most_skipped_category": skipped_cats.most_common(1)[0][0] if skipped_cats else None,
            "most_replaced_quests": most_replaced,
            "flow_distribution": dict(flow_dist),
            "streak_avg": round(avg_streak, 1),
            "difficulty_completion_rates": difficulty_rates,
            "peak_completion_hours": [h for h, _ in hour_dist.most_common(3)],
            "risk_users_count": len(risk_users),
        },
        "risk_users": risk_users,
        "ai_recommendations_context": {
            "description": "이 데이터를 기반으로 다음을 분석해주세요",
            "questions": [
                "어떤 카테고리/난이도의 퀘스트가 가장 많이 교체되거나 건너뛰어지는가? 해당 퀘스트를 개선하거나 제거해야 하는가?",
                "난이도별 완료율 차이가 크다면, 보상 밸런스를 어떻게 조정해야 하는가?",
                "유저들이 주로 어떤 시간대에 퀘스트를 완료하는가? 아침 메시지 발송 시간을 조정해야 하는가?",
                "회복 모드/가볍게 선택 비율이 높다면, 기본 난이도를 낮춰야 하는가?",
                "위험 유저들의 공통 패턴은 무엇인가? 이탈 방지를 위해 어떤 개입이 필요한가?",
                "스트릭 평균이 낮다면, 보호 메커니즘을 강화해야 하는가?",
            ],
        },
    }
