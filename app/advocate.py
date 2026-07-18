"""The Advocate — compresses a patient's story into a clinician-ready brief.

v1 is deterministic and rule-based so the demo runs with no external calls.
This module is the *seam* where a real Claude / DSPy agent would slot in:
replace `package_context` with an LLM call that takes the same `story` dict and
returns the same shape. Everything downstream (API, UI) stays unchanged.

The core pitch lives in the two views this returns:
  - `without_middle_zones`: what the clinician sees today (visit note + imaging)
  - `with_middle_zones`:     what the Advocate surfaces from between visits
"""

from __future__ import annotations

from typing import Any

NeedLabel = {
    "social": "Social support",
    "medical": "Medical",
    "financial": "Financial / cost-of-care",
    "behavioral": "Behavioral health",
    "safety": "Safety",
}


def _avg_engagement(story: dict[str, Any]) -> float:
    convs = story.get("conversations", [])
    if not convs:
        return 0.0
    vals = [c["signals"]["engagement"] for c in convs if "signals" in c]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _collect_needs(story: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for c in story.get("conversations", []):
        for n in c.get("signals", {}).get("needs", []):
            if n not in seen:
                seen.append(n)
    return seen


def _suggested_questions(story: dict[str, Any]) -> list[str]:
    """Derive 'ask the right questions sooner' prompts from the signals."""
    qs: list[str] = []
    needs = _collect_needs(story)
    if "financial" in needs:
        qs.append("Are cost or access barriers keeping you from any medication?")
    if "social" in needs:
        qs.append("Who is helping you at home, and what's hardest to manage alone?")
    if "safety" in needs:
        qs.append("Let's review activities to pause for safety (e.g. driving) until we know more.")
    if "behavioral" in needs:
        qs.append("How are your mood and stress affecting your daily routine?")
    if _avg_engagement(story) < 0.5:
        qs.append("What would make it easier to stay on top of your care between visits?")
    # imaging-anchored question (clinicians start from imaging)
    for img in story.get("imaging", []):
        qs.append(f"Since your {img['modality'].lower()}, have symptoms in that area changed?")
        break
    return qs or ["Any changes since we last spoke that I should know about?"]


def _middle_zone_highlights(story: dict[str, Any]) -> list[dict[str, str]]:
    """The context that lives *between* visits and normally never reaches the clinic."""
    highlights: list[dict[str, str]] = []
    for c in story.get("conversations", []):
        sig = c.get("signals", {})
        highlights.append({
            "source": c.get("source", c.get("type", "conversation")),
            "date": c.get("date", ""),
            "affect": c.get("affect", ""),
            "insight": sig.get("outcome", ""),
            "sentiment": sig.get("sentiment", ""),
        })
    return highlights


def package_context(story: dict[str, Any]) -> dict[str, Any]:
    """Return a clinician brief with the with/without-middle-zones contrast."""
    engagement = _avg_engagement(story)
    needs = _collect_needs(story)

    without = {
        "headline": f"{story['name']}, {story['age']} — {story['primary_condition']}",
        "known_to_ehr": [
            f"Problem list: {', '.join(story.get('conditions', []))}",
            *[f"{img['modality']} ({img['date']}): {img['findings']}"
              for img in story.get("imaging", [])],
            f"Next: {story.get('next_visit', 'follow-up')}",
        ],
        "note": "This is roughly what the clinician sees at the visit today.",
    }

    with_ = {
        "headline": f"Advocate brief for {story['name']}",
        "engagement_score": engagement,
        "engagement_label": (
            "Low — at risk of falling out of care" if engagement < 0.45
            else "Moderate" if engagement < 0.7 else "High"
        ),
        "unmet_needs": [NeedLabel.get(n, n.title()) for n in needs],
        "middle_zone_highlights": _middle_zone_highlights(story),
        "suggested_questions": _suggested_questions(story),
        "note": "The Advocate compresses calls, chats, and affect from between "
                "visits into what the clinician needs at the point of decision.",
    }

    return {
        "patient_id": story["id"],
        "focus": story.get("focus"),
        "without_middle_zones": without,
        "with_middle_zones": with_,
    }
