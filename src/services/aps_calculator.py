"""APS (Action Priority Score) calculator.

Scores items on a 0-100 scale using weighted components:
- Revenue impact (40%)
- Urgency (30%)
- Strategic value (20%)
- Effort (10%, inverted so lower effort increases score)

Heuristics are simple and deterministic for v0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class APSResult:
    score: float
    components: Dict[str, float]
    reasoning: str


def _bounded(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _defaults_for_action(action_type: str) -> Tuple[float, float, float, float]:
    """Return (revenue, urgency, effort, strategic) in [0,1] for a given action type.

    This is a simple heuristic mapping for v0.
    """
    action = (action_type or "").lower()
    if action in {"schedule_meeting", "book_meeting", "meeting_follow_up"}:
        return 0.9, 0.8, 0.4, 0.8
    if action in {"email_follow_up", "send_email", "thread_bump"}:
        return 0.6, 0.7, 0.2, 0.5
    if action in {"update_crm", "data_cleanup"}:
        return 0.3, 0.4, 0.3, 0.6
    if action in {"create_task", "log_call"}:
        return 0.4, 0.5, 0.3, 0.5
    # Unknown defaults
    return 0.5, 0.5, 0.5, 0.5


def calculate_aps(action_type: str, context: Dict | None = None) -> APSResult:
    """Compute APS score and a concise reasoning string.

    Context may provide numeric hints (0-1 floats) for keys:
    - revenue_impact, urgency, effort, strategic_value
    """
    context = context or {}

    rev_base, urg_base, eff_base, strat_base = _defaults_for_action(action_type)

    revenue = _bounded(float(context.get("revenue_impact", rev_base)))
    urgency = _bounded(float(context.get("urgency", urg_base)))
    # Effort increases cost; lower effort should boost APS. Keep raw in [0,1].
    effort = _bounded(float(context.get("effort", eff_base)))
    strategic = _bounded(float(context.get("strategic_value", strat_base)))

    # Weights
    w_rev, w_urg, w_strat, w_eff = 0.40, 0.30, 0.20, 0.10
    eff_inverted = 1.0 - effort

    raw = (revenue * w_rev) + (urgency * w_urg) + (strategic * w_strat) + (eff_inverted * w_eff)
    score = round(raw * 100.0, 2)

    reasoning = (
        f"Revenue {int(revenue*100)}%, Urgency {int(urgency*100)}%, "
        f"Strategic {int(strategic*100)}%, Effort↓ {int(eff_inverted*100)}%"
    )

    components = {
        "revenue": round(revenue, 3),
        "urgency": round(urgency, 3),
        "effort": round(effort, 3),
        "strategic": round(strategic, 3),
    }

    return APSResult(score=score, components=components, reasoning=reasoning)
