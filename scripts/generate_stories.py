"""Generate synthetic patient stories for MCP for Health.

Produces up to 20 high-fidelity ("4k") synthetic stories as JSON in app/data/.
Two hand-authored "hero" stories (one cardiac, one neuro) anchor the demo;
the rest are procedurally varied so the patient picker feels populated.

Run:  uv run python scripts/generate_stories.py
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"
SEED = 42


# --------------------------------------------------------------------------- #
# Hand-authored "hero" stories                                                #
# --------------------------------------------------------------------------- #
HERO_STORIES = [
    {
        "id": "p001",
        "name": "Maria Alvarez",
        "age": 63,
        "sex": "F",
        "focus": "heart",
        "primary_condition": "Heart failure with reduced ejection fraction (HFrEF)",
        "conditions": ["HFrEF", "Type 2 Diabetes", "Hypertension"],
        "pcp": "Dr. Nguyen (Internal Medicine)",
        "next_visit": "Cardiology follow-up",
        "conversations": [
            {
                "id": "c-p001-1",
                "type": "phone",
                "date": "2026-06-14",
                "with": "Heart-failure nurse (care team)",
                "source": "Care team call",
                "transcript": (
                    "Nurse: Hi Maria, checking in after your discharge. How's the "
                    "breathing?\n"
                    "Maria: Honestly not great. I'm using three pillows now to sleep and "
                    "my ankles are swollen again.\n"
                    "Nurse: Are you weighing yourself each morning?\n"
                    "Maria: I stopped. The scale broke and I couldn't afford a new one "
                    "this month. Money's been tight since I cut back my hours.\n"
                    "Nurse: Did you fill the new water pill?\n"
                    "Maria: I picked up the others but that one was $40 so I skipped it."
                ),
                "affect": "anxious, discouraged",
                "signals": {
                    "intent": "Report worsening symptoms after discharge",
                    "outcome": "Symptoms escalating; two care gaps surfaced",
                    "engagement": 0.35,
                    "needs": ["social", "medical", "financial"],
                    "trusts_pcp": True,
                    "sentiment": "negative",
                },
            },
            {
                "id": "c-p001-2",
                "type": "chat",
                "date": "2026-06-16",
                "with": "Claude (health assistant)",
                "source": "Claude",
                "transcript": (
                    "Maria: is it normal to gain 5 pounds in 3 days on heart failure "
                    "medicine?\n"
                    "Claude: A rapid gain like that often means fluid is building up and "
                    "is worth calling your care team about today. Are you short of "
                    "breath?\n"
                    "Maria: yes when i walk to the mailbox. i don't want to bother them "
                    "again though."
                ),
                "affect": "worried, reluctant to escalate",
                "signals": {
                    "intent": "Self-triage rapid weight gain",
                    "outcome": "Red-flag fluid overload; patient hesitant to seek care",
                    "engagement": 0.5,
                    "needs": ["medical", "behavioral"],
                    "trusts_pcp": True,
                    "sentiment": "negative",
                },
            },
        ],
        "imaging": [
            {
                "modality": "Echocardiogram",
                "region": "heart",
                "date": "2026-05-30",
                "findings": "LVEF 32%. Dilated left ventricle, moderate mitral "
                "regurgitation. Elevated filling pressures.",
                "annotations": [
                    {"label": "Dilated LV (EF 32%)", "x": 38, "y": 58},
                    {"label": "Moderate mitral regurg.", "x": 55, "y": 44},
                ],
            }
        ],
        "timeline": [
            {"date": "2026-05-28", "kind": "visit", "event": "ED visit for dyspnea; admitted"},
            {"date": "2026-05-30", "kind": "imaging", "event": "Echo: EF 32%"},
            {"date": "2026-06-02", "kind": "visit", "event": "Discharged on GDMT + diuretic"},
            {"date": "2026-06-14", "kind": "call", "event": "Nurse check-in: symptoms worse"},
            {"date": "2026-06-16", "kind": "call", "event": "Chatbot: rapid 5 lb weight gain"},
        ],
    },
    {
        "id": "p002",
        "name": "James Okafor",
        "age": 47,
        "sex": "M",
        "focus": "brain",
        "primary_condition": "Focal epilepsy, post-first-seizure workup",
        "conditions": ["New-onset focal seizures", "Migraine", "Anxiety"],
        "pcp": "Dr. Patel (Family Medicine)",
        "next_visit": "Neurology consult",
        "conversations": [
            {
                "id": "c-p002-1",
                "type": "phone",
                "date": "2026-07-01",
                "with": "Neurology triage nurse",
                "source": "Care team call",
                "transcript": (
                    "Nurse: You're calling about the episode last week?\n"
                    "James: Yeah. My wife said I stared blankly and my right hand was "
                    "twitching for about a minute, then I was confused for a while.\n"
                    "Nurse: Any warning before it?\n"
                    "James: A weird rising feeling in my stomach and a smell that wasn't "
                    "there. It's happened twice more since, smaller.\n"
                    "Nurse: Are you driving?\n"
                    "James: I have to, to get to work. Nobody told me not to."
                ),
                "affect": "matter-of-fact, unaware of risk",
                "signals": {
                    "intent": "Report recurrent focal episodes",
                    "outcome": "Semiology suggests temporal-lobe focus; safety gap (driving)",
                    "engagement": 0.6,
                    "needs": ["medical", "safety"],
                    "trusts_pcp": True,
                    "sentiment": "neutral",
                },
            },
            {
                "id": "c-p002-2",
                "type": "chat",
                "date": "2026-07-05",
                "with": "ChatGPT",
                "source": "ChatGPT",
                "transcript": (
                    "James: what does a temporal lobe seizure aura feel like\n"
                    "Assistant: People often describe a rising stomach sensation, an "
                    "unusual smell or taste, or intense deja vu...\n"
                    "James: that's exactly it. should i be worried about my memory? "
                    "i've been forgetting words."
                ),
                "affect": "curious, newly concerned",
                "signals": {
                    "intent": "Understand aura + new word-finding trouble",
                    "outcome": "Reports interictal cognitive symptoms",
                    "engagement": 0.7,
                    "needs": ["medical", "behavioral"],
                    "trusts_pcp": True,
                    "sentiment": "neutral",
                },
            },
        ],
        "imaging": [
            {
                "modality": "Brain MRI (epilepsy protocol)",
                "region": "brain",
                "date": "2026-06-28",
                "findings": "Subtle left mesial temporal signal change; possible "
                "hippocampal sclerosis. No mass.",
                "annotations": [
                    {"label": "L mesial temporal signal", "x": 40, "y": 60},
                    {"label": "Hippocampus — asymmetry", "x": 44, "y": 66},
                ],
            }
        ],
        "timeline": [
            {"date": "2026-06-24", "kind": "visit", "event": "PCP visit after first episode"},
            {"date": "2026-06-28", "kind": "imaging", "event": "MRI: L mesial temporal change"},
            {"date": "2026-07-01", "kind": "call", "event": "Triage: recurrent auras, still driving"},
            {"date": "2026-07-05", "kind": "call", "event": "Chatbot: aura + word-finding trouble"},
        ],
    },
]


# --------------------------------------------------------------------------- #
# Procedural filler                                                           #
# --------------------------------------------------------------------------- #
FIRST_NAMES = [
    "Aisha", "Robert", "Wei", "Sofia", "Darnell", "Emma", "Hiroshi", "Fatima",
    "Liam", "Priya", "Marcus", "Elena", "Tomas", "Grace", "Omar", "Nadia",
    "Carlos", "Ingrid",
]
LAST_NAMES = [
    "Chen", "Johnson", "Kowalski", "Rossi", "Mbeki", "Andersson", "Khan",
    "Silva", "Nakamura", "Reyes", "Hughes", "Petrov", "Adeyemi", "Larsson",
    "Costa", "Haddad", "Novak", "Ferreira",
]

HEART_CONDITIONS = [
    ("Coronary artery disease", ["CAD", "Hyperlipidemia", "Former smoker"], "Echocardiogram",
     "Regional wall-motion abnormality, EF 48%.", "Coronary catheterization"),
    ("Atrial fibrillation", ["AFib", "Hypertension", "Obesity"], "Echocardiogram",
     "Left atrial enlargement, preserved EF 58%.", "Electrophysiology consult"),
    ("Aortic stenosis", ["Severe AS", "Hypertension"], "Echocardiogram",
     "Calcified aortic valve, mean gradient 44 mmHg.", "Structural heart clinic"),
]
BRAIN_CONDITIONS = [
    ("Ischemic stroke (recovery)", ["Prior stroke", "Hypertension", "Diabetes"], "Brain MRI",
     "Chronic left MCA-territory infarct; encephalomalacia.", "Stroke follow-up"),
    ("Multiple sclerosis", ["Relapsing-remitting MS"], "Brain MRI",
     "Multiple periventricular T2 lesions; one enhancing.", "Neuro-immunology visit"),
    ("Parkinson's disease", ["Parkinson's disease", "REM sleep behavior disorder"], "DaTscan",
     "Reduced striatal uptake, right > left.", "Movement-disorders clinic"),
]

AFFECTS = ["anxious", "hopeful", "frustrated", "resigned", "calm", "overwhelmed"]
SENTIMENTS = ["negative", "neutral", "positive"]
NEEDS_POOL = [["social"], ["medical"], ["financial"], ["behavioral"],
              ["medical", "social"], ["medical", "financial"]]


def _rand_date(rng: random.Random, base: date, spread: int) -> str:
    return (base - timedelta(days=rng.randint(0, spread))).isoformat()


def make_filler(idx: int, rng: random.Random) -> dict:
    focus = "heart" if idx % 2 == 0 else "brain"
    pool = HEART_CONDITIONS if focus == "heart" else BRAIN_CONDITIONS
    cond, conds, modality, findings, next_visit = rng.choice(pool)
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    base = date(2026, 7, 10)
    pid = f"p{idx:03d}"

    def conv(kind: str, source: str, n: int) -> dict:
        eng = round(rng.uniform(0.2, 0.9), 2)
        return {
            "id": f"c-{pid}-{n}",
            "type": kind,
            "date": _rand_date(rng, base, 40),
            "with": source,
            "source": source,
            "transcript": (
                f"[Synthetic {kind} about managing {cond.lower()}. "
                f"Patient raises questions about symptoms, medications, and "
                f"day-to-day coping between visits.]"
            ),
            "affect": rng.choice(AFFECTS),
            "signals": {
                "intent": f"Discuss {cond.lower()} management",
                "outcome": "Context captured between visits",
                "engagement": eng,
                "needs": rng.choice(NEEDS_POOL),
                "trusts_pcp": rng.random() > 0.25,
                "sentiment": rng.choice(SENTIMENTS),
            },
        }

    return {
        "id": pid,
        "name": name,
        "age": rng.randint(34, 82),
        "sex": rng.choice(["F", "M"]),
        "focus": focus,
        "primary_condition": cond,
        "conditions": conds,
        "pcp": f"Dr. {rng.choice(LAST_NAMES)} ({'Cardiology' if focus == 'heart' else 'Neurology'})",
        "next_visit": next_visit,
        "conversations": [
            conv("phone", "Care team call", 1),
            conv("chat", rng.choice(["Claude", "ChatGPT"]), 2),
        ],
        "imaging": [
            {
                "modality": modality,
                "region": focus,
                "date": _rand_date(rng, base, 50),
                "findings": findings,
                "annotations": [
                    {"label": "Region of interest",
                     "x": rng.randint(35, 60), "y": rng.randint(40, 65)},
                ],
            }
        ],
        "timeline": [
            {"date": _rand_date(rng, base, 60), "kind": "imaging", "event": f"{modality}: {findings[:40]}..."},
            {"date": _rand_date(rng, base, 30), "kind": "call", "event": "Care-team check-in"},
            {"date": _rand_date(rng, base, 10), "kind": "call", "event": "Chatbot conversation logged"},
        ],
    }


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    stories = list(HERO_STORIES)
    for i in range(len(stories) + 1, 21):  # fill up to 20 total
        stories.append(make_filler(i, rng))

    for story in stories:
        (DATA_DIR / f"{story['id']}.json").write_text(
            json.dumps(story, indent=2), encoding="utf-8"
        )

    index = [
        {"id": s["id"], "name": s["name"], "age": s["age"], "sex": s["sex"],
         "focus": s["focus"], "primary_condition": s["primary_condition"]}
        for s in stories
    ]
    (DATA_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Wrote {len(stories)} stories to {DATA_DIR}")


if __name__ == "__main__":
    main()
