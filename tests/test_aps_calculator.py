from src.services.aps_calculator import calculate_aps


def test_aps_bounds_and_ordering():
    a = calculate_aps("schedule_meeting", {"revenue_impact": 0.9, "urgency": 0.8, "effort": 0.2, "strategic_value": 0.8})
    b = calculate_aps("update_crm", {"revenue_impact": 0.3, "urgency": 0.4, "effort": 0.4, "strategic_value": 0.6})

    assert 0 <= a.score <= 100
    assert 0 <= b.score <= 100
    assert a.score > b.score


def test_reasoning_contains_components():
    r = calculate_aps("email_follow_up")
    assert "Revenue" in r.reasoning and "Urgency" in r.reasoning and "Strategic" in r.reasoning and "Effort" in r.reasoning
