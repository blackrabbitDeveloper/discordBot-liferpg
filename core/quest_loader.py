import yaml
from typing import Any


def load_quests(yaml_path: str) -> dict[str, list[dict]]:
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
