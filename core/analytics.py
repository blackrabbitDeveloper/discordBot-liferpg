# core/analytics.py
import json
from datetime import date, timedelta, datetime
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from core.models import User, UserActivityLog, DailyQuest


def _calc_retention(session: Session, users: list[User], day_n: int) -> float:
    """Day N 유지율 계산. 온보딩 후 N일째에 활동(퀘스트 완료/건너뛰기)한 유저 비율."""
    if not users:
        return 0.0
    retained = 0
    for user in users:
        if not user.created_at:
            continue
        target_date = user.created_at.date() + timedelta(days=day_n)
        has_activity = (
            session.query(DailyQuest)
            .filter(
                DailyQuest.user_id == user.id,
                DailyQuest.quest_date == target_date,
                DailyQuest.state.in_(["COMPLETED", "SKIPPED"]),
            )
            .first()
            is not None
        )
        if has_activity:
            retained += 1
    return round(retained / len(users) * 100, 1)


def _calc_first_quest_rate(session: Session, logs: list[UserActivityLog]) -> dict:
    """첫 퀘스트 선택률 + 첫날 완료율."""
    # 온보딩 완료한 유저 목록
    onboarded_user_ids = set()
    for l in logs:
        if l.action == "onboarding_complete" and l.user_id:
            onboarded_user_ids.add(l.user_id)

    if not onboarded_user_ids:
        return {"first_quest_selection_rate": 0, "first_day_completion_rate": 0}

    first_quest_selected = 0
    first_day_completed = 0

    for user_id in onboarded_user_ids:
        # 해당 유저의 온보딩 날짜 찾기
        user = session.query(User).get(user_id)
        if not user or not user.created_at:
            continue
        onboard_date = user.created_at.date()

        # 첫날 퀘스트가 있는지 (선택)
        first_day_quests = (
            session.query(DailyQuest)
            .filter(
                DailyQuest.user_id == user_id,
                DailyQuest.quest_date == onboard_date,
            )
            .all()
        )
        if first_day_quests:
            first_quest_selected += 1
            # 첫날 완료가 있는지
            if any(q.state == "COMPLETED" for q in first_day_quests):
                first_day_completed += 1

    total = len(onboarded_user_ids)
    return {
        "first_quest_selection_rate": round(first_quest_selected / total * 100, 1),
        "first_day_completion_rate": round(first_day_completed / total * 100, 1),
    }


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
    active_users_list = session.query(User).filter_by(status="active").all()
    active_users = len(active_users_list)
    all_users = session.query(User).all()

    # 온보딩 분석
    onboarding_starts = sum(1 for l in logs if l.action == "onboarding_start")
    onboarding_completes = sum(1 for l in logs if l.action == "onboarding_complete")
    onboarding_rate = (onboarding_completes / onboarding_starts * 100) if onboarding_starts > 0 else 0

    # 유지율 (전체 유저 대상)
    day1_retention = _calc_retention(session, all_users, 1)
    day2_retention = _calc_retention(session, all_users, 2)
    day3_retention = _calc_retention(session, all_users, 3)
    day7_retention = _calc_retention(session, all_users, 7)

    # 첫 퀘스트 선택률 + 첫날 완료율
    first_quest_stats = _calc_first_quest_rate(session, logs)

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
    avg_streak = sum(u.streak for u in active_users_list) / len(active_users_list) if active_users_list else 0

    # 위험 유저 (스트릭 0 + 최근 활동 없음)
    risk_users = []
    for u in active_users_list:
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

    # 카테고리별 완료율
    category_stats = defaultdict(lambda: {"completed": 0, "total": 0})
    for l in logs:
        if l.action in ("quest_completed", "quest_skipped", "quest_expired") and l.detail:
            d = json.loads(l.detail)
            cat = d.get("category", "unknown")
            category_stats[cat]["total"] += 1
            if l.action == "quest_completed":
                category_stats[cat]["completed"] += 1

    category_rates = {
        k: round(v["completed"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        for k, v in category_stats.items()
    }

    # 요일별 완료율
    weekday_stats = defaultdict(lambda: {"completed": 0, "total": 0})
    WEEKDAY_KR = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    for l in logs:
        if l.action in ("quest_completed", "quest_skipped", "quest_expired"):
            day_name = WEEKDAY_KR[l.created_at.weekday()]
            weekday_stats[day_name]["total"] += 1
            if l.action == "quest_completed":
                weekday_stats[day_name]["completed"] += 1

    weekday_rates = {
        k: round(v["completed"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        for k, v in weekday_stats.items()
    }

    return {
        "period": f"{start_date} ~ {today}",
        "total_users": total_users,
        "active_users": active_users,
        "retention": {
            "onboarding_completion_rate": round(onboarding_rate, 1),
            "first_quest_selection_rate": first_quest_stats["first_quest_selection_rate"],
            "first_day_completion_rate": first_quest_stats["first_day_completion_rate"],
            "day1_retention": day1_retention,
            "day2_retention": day2_retention,
            "day3_retention": day3_retention,
            "day7_retention": day7_retention,
        },
        "engagement": {
            "avg_daily_completion_rate": round(avg_completion, 1),
            "streak_avg": round(avg_streak, 1),
            "flow_distribution": dict(flow_dist),
            "peak_completion_hours": [h for h, _ in hour_dist.most_common(3)],
        },
        "quest_analysis": {
            "most_completed_category": completed_cats.most_common(1)[0][0] if completed_cats else None,
            "most_skipped_category": skipped_cats.most_common(1)[0][0] if skipped_cats else None,
            "most_replaced_quests": most_replaced,
            "difficulty_completion_rates": difficulty_rates,
            "category_completion_rates": category_rates,
            "weekday_completion_rates": weekday_rates,
        },
        "risk": {
            "risk_users_count": len(risk_users),
            "risk_users": risk_users,
        },
        "ai_recommendations_context": {
            "description": "이 데이터를 기반으로 다음을 분석해주세요",
            "questions": [
                "유지율(Day1~Day7) 추이가 어떤가? 이탈이 급격한 시점이 있다면 원인은 무엇인가?",
                "첫 퀘스트 선택률과 첫날 완료율 차이가 크다면, 온보딩 직후 UX에 문제가 있는 것인가?",
                "어떤 카테고리/난이도의 퀘스트가 가장 많이 교체되거나 건너뛰어지는가? 해당 퀘스트를 개선하거나 제거해야 하는가?",
                "난이도별 완료율 차이가 크다면, 보상 밸런스를 어떻게 조정해야 하는가?",
                "요일별 완료율에 패턴이 있는가? 특정 요일에 난이도를 낮춰야 하는가?",
                "유저들이 주로 어떤 시간대에 퀘스트를 완료하는가? 아침 메시지 발송 시간을 조정해야 하는가?",
                "회복 모드/가볍게 선택 비율이 높다면, 기본 난이도를 낮춰야 하는가?",
                "위험 유저들의 공통 패턴은 무엇인가? 이탈 방지를 위해 어떤 개입이 필요한가?",
                "스트릭 평균이 낮다면, 보호 메커니즘을 강화해야 하는가?",
            ],
        },
    }
