"""Decides if the panel genuinely disagrees. PURE PYTHON — no AI call.

Comparing 8 to 2 is subtraction. Code does it instantly, for free, the same way
every time. This yes/no is what decides whether a debate happens.
"""
from schemas import Scorecard

# How big a score gap counts as a disagreement. Higher strictness = smaller gap needed.
THRESHOLDS = {"high": 2, "medium": 4, "low": 6}


def _direction(rec: str) -> str:
    """Squash 4 labels into 2. strong_hire/hire -> hire, the rest -> no_hire."""
    return "hire" if rec in ("strong_hire", "hire") else "no_hire"


def detect(scores: dict[str, Scorecard], sensitivity: str = "high") -> dict:
    """Return a small report: do they disagree, and why."""
    threshold = THRESHOLDS.get(sensitivity, 2)

    values = [s.score for s in scores.values()]
    spread = max(values) - min(values)

    directions = {_direction(s.recommendation) for s in scores.values()}
    direction_conflict = len(directions) > 1

    # Disagree if the gap is big enough OR the recommendations point opposite ways.
    is_disagreement = (spread >= threshold) or direction_conflict

    if is_disagreement:
        summary = (f"Disagreement ({sensitivity}, needs gap {threshold}+): "
                   f"scores spread by {spread}. The panel should debate.")
    else:
        summary = f"Panel agrees (spread only {spread}). No debate needed."

    return {
        "is_disagreement": is_disagreement,
        "spread": spread,
        "direction_conflict": direction_conflict,
        "sensitivity": sensitivity,
        "threshold": threshold,
        "summary": summary,
    }
