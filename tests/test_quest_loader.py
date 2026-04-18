import pytest
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
