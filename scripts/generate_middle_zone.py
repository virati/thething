#!/usr/bin/env python3
"""Generate 2 "middle-zone" artifacts for every patient in the raw
synthetic-ambient-fhir-25 dataset, using the care-journey-extender skill's
middle-zone builder.

Middle zone = the between-visit, non-physician touchpoints an encounter-scoped
tool never captures. Each artifact is grounded in that patient's actual
conditions/medications and dated relative to their index visit. Content is
authored here (the clinical-reasoning step); the builder assembles the schema.

Run:
  uv run python scripts/generate_middle_zone.py

Writes:
  data/middle-zone/middle-zone-artifacts.jsonl   (one artifact per line)
  data/middle-zone/middle-zone-artifacts.json    (same, as an array)
  data/middle-zone/master_plan.json              (per-patient artifact index)
"""
from __future__ import annotations

import calendar
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "synthetic-ambient-fhir-25" / "synthetic-ambient-fhir-25.jsonl"
OUT_DIR = ROOT / "data" / "middle-zone"
SKILL_SCRIPTS = ROOT / "utils" / "care-journey-extender" / "scripts"

sys.path.insert(0, str(SKILL_SCRIPTS))
from middle_zone_builder import MiddleZoneBatch  # noqa: E402


def add_months(iso_date: str, months: float) -> date:
    base = date.fromisoformat(iso_date[:10])
    whole = int(months)
    frac = months - whole
    y = base.year + (base.month - 1 + whole) // 12
    m = (base.month - 1 + whole) % 12 + 1
    d = min(base.day, calendar.monthrange(y, m)[1])
    return date(y, m, d) + timedelta(days=round(frac * 30.44))


# Default time-of-day per channel (drives the felt texture: chatbot = late night)
CHANNEL_TIME = {
    "chatbot.symptom_checker": "23:10",
    "portal.message": "19:25",
    "portal.device_upload": "07:35",
    "pharmacy.refill": "09:05",
    "call.nurse_triage": "10:40",
    "call.care_coordinator": "14:15",
    "call.home_health": "16:30",
    "call.hospice_nurse": "11:20",
    "call.family_caregiver": "18:50",
}


def A(channel, direction, months, title, transcript, note, ann, signal, time=None):
    """Compact constructor for an authored artifact spec."""
    return {
        "channel": channel, "direction": direction, "months": months,
        "title": title, "transcript": transcript, "note": note,
        "ann": ann, "signal": signal, "time": time,
    }


def ann(intent, outcome, engagement, needs, trust, sentiment, journey):
    return {
        "intent": intent, "outcome": outcome, "engagement": engagement,
        "needs": needs, "trust": trust, "sentiment": sentiment,
        "journey_position": journey,
    }


# --------------------------------------------------------------------------- #
# Authored middle-zone artifacts, keyed by patient index (from explore.py).   #
# Two per patient, grounded in their real conditions/meds.                     #
# --------------------------------------------------------------------------- #
AUTHORED = {
0: [  # Ali Kuhic, 31M — migraine, stress, transport problem, social isolation
  A("chatbot.symptom_checker", "inbound", 3,
    "Late-night migraine self-check",
    "PT: it's 11pm and I've had a migraine for 3 days now, the propranolol isn't touching it\n"
    "BOT: I'm sorry you're dealing with this. Any new symptoms — vision changes, weakness, worst-headache-of-life?\n"
    "PT: no just the usual but longer. I don't want to bug the office again, they'll think I'm dramatic\n"
    "BOT: A migraine lasting 72h+ despite your preventive can be status migrainosus and is worth a same-week call.\n"
    "PT: maybe. I'll see if it breaks on its own.",
    "Automated symptom-checker session. 72h migraine refractory to propranolol; no red flags reported. "
    "Bot advised same-week clinical contact. No follow-up booked; patient self-minimizing.",
    ann("symptom help (surface) / permission to escalate (actual)",
        "advice given; no appointment booked",
        "engaged but reluctant to use human channels",
        "informational (status migrainosus); reassurance he isn't 'dramatic'",
        "trusts the anonymous bot more than the office",
        "frustrated, self-minimizing",
        "between preventive visits; a preventable escalation point"),
    "moderate"),
  A("portal.message", "inbound", 5,
    "Can't get to the neurology referral",
    "Hi — I got the neurology referral but it's 40 minutes away and I don't drive. "
    "Is there anyone closer or can it be a video visit? Otherwise I probably just won't go. Thanks.",
    "Portal message re: access barrier to neurology referral (no transportation). Patient signals likely "
    "no-show without an alternative. Logged to referral coordinator queue.",
    ann("scheduling (surface) / flag an access barrier (actual)",
        "unresolved at time of logging",
        "proactive but conditional ('probably won't go')",
        "logistical (transportation / telehealth option)",
        "willing to ask once",
        "resigned",
        "referral about to fail silently"),
    "moderate"),
],
1: [  # Ariane Runolfsson, 80F — post-COVID, STEMI hx, HTN, osteoporosis; aspirin/atenolol/statin/lisinopril
  A("call.nurse_triage", "inbound", 4,
    "Breathless on the stairs since discharge",
    "PT: since I got home from the hospital I get so winded on the stairs, I have to stop halfway\n"
    "NURSE: any chest pain, ankle swelling, or waking up short of breath?\n"
    "PT: a little puffy in the ankles by evening. No chest pain.\n"
    "NURSE: Let's get you weighed daily and I'll ask cardiology to review — call back if the swelling climbs.\n"
    "PT: I don't want to be a nuisance, but alright.",
    "Nurse triage: post-discharge exertional dyspnea + evening ankle edema in 80F with prior STEMI. "
    "Advised daily weights, cardiology review requested. Query early heart failure.",
    ann("symptom report",
        "daily weights advised; cardiology review requested",
        "hesitant ('nuisance') but follows advice",
        "medical (HF surveillance)",
        "moderate — defers to nurse",
        "worried, apologetic",
        "post-hospitalization surveillance window"),
    "high"),
  A("pharmacy.refill", "passive", 6,
    "Atenolol refill 12 days late",
    "SYSTEM: atenolol 50 MG — last fill +12 days overdue. Prior fills on time. "
    "No refusal recorded. Auto-reminder texted; no response.",
    "Pharmacy refill-gap alert: rate-control (atenolol) coverage lapse of ~12 days in an 80F with cardiac "
    "history. No clinical review triggered.",
    ann("n/a (passive log)",
        "reminder sent; gap unaddressed",
        "passive non-fill",
        "adherence support (why the gap?)",
        "n/a",
        "n/a",
        "silent rate-control lapse between visits"),
    "moderate"),
],
2: [  # Clarence Reinger, 32F — normal pregnancy, recurrent UTI
  A("call.nurse_triage", "inbound", 4,
    "Burning with urination at 30 weeks",
    "PT: I've got that burning feeling again when I pee, I get these UTIs a lot and I'm 30 weeks now\n"
    "NURSE: any fever, back pain, or contractions?\n"
    "PT: no fever, just uncomfortable and going constantly\n"
    "NURSE: In pregnancy we treat these promptly — I'll set up a urine sample today and loop in OB.\n"
    "PT: thank you, I was worried about the baby.",
    "Nurse triage: recurrent-UTI patient at 30wk with dysuria/frequency, no systemic signs. "
    "Same-day urinalysis arranged; OB notified. Untreated UTI in pregnancy carries preterm risk.",
    ann("symptom report",
        "same-day UA arranged; OB looped in",
        "proactive, health-literate",
        "medical (prompt UTI treatment in pregnancy)",
        "high trust in nurse line",
        "anxious about baby",
        "antenatal, actively managed"),
    "moderate"),
  A("portal.message", "inbound", 2,
    "Is my UTI medication safe in pregnancy?",
    "Quick question — last time I had a UTI I was given nitrofurantoin. Is that okay now that I'm pregnant, "
    "or should I ask for something else? Don't want to take anything that isn't safe.",
    "Portal message: medication-safety question (nitrofurantoin in pregnancy). Routed to OB nurse. "
    "Reflects engaged, safety-conscious patient.",
    ann("informational (medication safety)",
        "awaiting OB nurse reply",
        "engaged, self-advocating",
        "informational (teratogenicity/trimester timing)",
        "trusts and verifies",
        "cautious",
        "antenatal education"),
    "low"),
],
3: [  # Corinne Crooks, 46F — chronic sinusitis, obesity
  A("portal.message", "inbound", 6,
    "Sinus infection again — can I get antibiotics?",
    "This is my third sinus infection since spring — facial pressure, thick discharge, 10 days now and not "
    "improving. Can you call in an antibiotic so I don't have to take another day off work?",
    "Portal message: recurrent sinusitis (3rd episode), 10-day duration meeting bacterial criteria. "
    "Requests phone-in antibiotic; work-absence barrier to being seen. Query ENT referral for recurrence.",
    ann("treatment request (surface) / avoid taking time off (actual)",
        "pending clinician review",
        "self-directed",
        "medical (recurrence workup) + logistical (work absence)",
        "expects the system to act on her read",
        "impatient, practical",
        "recurrent-condition pattern forming"),
    "moderate"),
  A("chatbot.symptom_checker", "inbound", 2,
    "Which decongestant won't raise my blood pressure?",
    "PT: what over-the-counter decongestant is safe? I keep getting sinus infections\n"
    "BOT: Do you have high blood pressure or take any daily meds?\n"
    "PT: borderline BP, no meds. and I'm trying to lose weight\n"
    "BOT: Consider saline/steroid nasal sprays over oral pseudoephedrine; recurrent sinusitis is worth an ENT look.",
    "Symptom-checker: OTC decongestant guidance with borderline-hypertension caution; recurrent-sinusitis "
    "pattern surfaced but no human referral generated.",
    ann("self-care guidance",
        "advice given; no referral",
        "engaged, information-seeking",
        "informational (safe OTC choice); behavioral (weight)",
        "uses bot as first stop",
        "matter-of-fact",
        "self-management between visits"),
    "low"),
],
4: [  # Delana Gutkowski, 22F — prediabetes, obesity, isolation, allergy (epi-pen), cetirizine
  A("pharmacy.refill", "passive", 8,
    "Epinephrine auto-injector expired, not refilled",
    "SYSTEM: Epinephrine auto-injector — expired 6 weeks ago, no refill on file. Cetirizine filled on time. "
    "Auto-reminder sent; unread.",
    "Pharmacy alert: life-saving epinephrine auto-injector lapsed/expired in a patient with documented "
    "anaphylaxis risk. No active prescription. High-consequence gap despite good antihistamine adherence.",
    ann("n/a (passive log)",
        "reminder sent; not acted on",
        "passive lapse of a rescue med",
        "safety-critical (current epinephrine)",
        "n/a",
        "n/a",
        "silent safety gap"),
    "high"),
  A("chatbot.symptom_checker", "inbound", 3,
    "Prediabetes and eating alone",
    "PT: got told I'm prediabetic at 22 and honestly I don't know where to start, I eat alone most nights\n"
    "BOT: Small, sustainable swaps help more than overhauls. Would a referral to a dietitian or a group program help?\n"
    "PT: a group sounds nice actually, it gets pretty lonely\n"
    "BOT: I can note your interest — a care coordinator can follow up.",
    "Symptom-checker: newly-labeled prediabetes in a socially-isolated 22F; expresses loneliness and interest "
    "in a group program. Coordinator follow-up flagged (not yet routed to a human).",
    ann("informational (surface) / connection (actual)",
        "interest captured; human follow-up not yet routed",
        "opens up to the bot",
        "behavioral (diet) + social (isolation)",
        "discloses to a non-judgmental channel",
        "lonely, tentatively hopeful",
        "early chronic-risk, high-leverage for engagement"),
    "moderate"),
],
5: [  # Dick Larson, 36M — post-sepsis/ARDS, prediabetes, housing unsatisfactory, unemployed, isolation
  A("call.care_coordinator", "inbound", 4,
    "Can't afford the follow-up labs",
    "PT: I got the lab order but I lost my job and my insurance is a mess, I can't pay for it right now\n"
    "COORD: Thanks for telling me — we have a sliding-scale option and I can flag financial assistance.\n"
    "PT: and honestly the place I'm staying isn't stable, mail doesn't always reach me\n"
    "COORD: I'll note housing and use phone for everything. Let's not let the labs slide.",
    "Care-coordinator call: financial + housing instability blocking post-sepsis follow-up labs and reachability. "
    "Sliding-scale and financial assistance offered; contact preference set to phone.",
    ann("logistics (surface) / disclose financial + housing barriers (actual)",
        "assistance offered; labs preserved via sliding scale",
        "re-engages when asked directly",
        "financial, housing, communication access",
        "cautiously trusting the coordinator",
        "stressed, embarrassed",
        "recovery derailing on social determinants"),
    "high"),
  A("call.nurse_triage", "inbound", 7,
    "Still winded months after the ICU",
    "PT: it's been months since the sepsis thing but I still get out of breath doing basic stuff\n"
    "NURSE: any cough, chest pain, or is it just exertion?\n"
    "PT: just exertion, and I get tired fast\n"
    "NURSE: Post-ARDS recovery can linger — let's check pulmonary function and rule out anemia given your history.",
    "Nurse triage: persistent exertional dyspnea/fatigue post-ARDS with known anemia. PFTs and CBC recommended; "
    "pulmonary follow-up considered.",
    ann("symptom report",
        "PFT + CBC recommended",
        "engaged",
        "medical (post-ARDS workup, anemia)",
        "moderate",
        "discouraged",
        "long-tail recovery surveillance"),
    "moderate"),
],
6: [  # Elias Wisozk, 54M — new HTN, metabolic syndrome, anemia; HCTZ, B12
  A("portal.device_upload", "passive", 3,
    "Home BP readings trending up",
    "SYSTEM: Home BP cuff sync — 14-day average 152/95 (baseline 138/86). Morning readings highest. "
    "No alert threshold configured; not reviewed.",
    "Passive device upload: home BP averaging 152/95 in a newly-diagnosed hypertensive on HCTZ monotherapy. "
    "Suggests inadequate control; no clinician saw the trend.",
    ann("n/a (passive stream)",
        "captured but unreviewed",
        "adhering to home monitoring",
        "medical (BP escalation — likely needs 2nd agent)",
        "n/a",
        "n/a",
        "titration signal sitting unread"),
    "moderate"),
  A("portal.message", "inbound", 4,
    "The water pill makes me dizzy — thinking of stopping",
    "The hydrochlorothiazide is making me lightheaded, especially mornings, and I'm peeing all the time. "
    "I'm thinking of just stopping it. Is that okay?",
    "Portal message: HCTZ-attributed dizziness/polyuria; patient contemplating self-discontinuation of "
    "antihypertensive. Adherence at risk — needs prompt clinician outreach (BP already elevated on home cuff).",
    ann("permission-seeking (self-discontinuation)",
        "pending reply; discontinuation risk live",
        "communicates before stopping (good)",
        "medical (side-effect management, regimen change)",
        "checks in rather than silently stopping",
        "frustrated with side effects",
        "adherence fork — pairs with the unread BP trend"),
    "high"),
],
7: [  # Emory Kovacek, 22M — chronic low back pain, positive depression screen, stress; ibuprofen
  A("chatbot.symptom_checker", "inbound", 2,
    "Low mood, late night",
    "PT: can't sleep, everything feels pointless lately, back pain doesn't help\n"
    "BOT: I'm really glad you reached out. Have you had thoughts of harming yourself?\n"
    "PT: not really acting on anything, just tired of it all\n"
    "BOT: Thank you for telling me. I'm sharing crisis-line options and flagging a same-week behavioral-health "
    "outreach. You don't have to manage this alone.",
    "Symptom-checker after hours: worsening low mood with passive hopelessness (no active SI/plan) in a patient "
    "with a positive depression screen. Crisis resources surfaced; behavioral-health outreach flagged.",
    ann("support-seeking (surface) / disclosure of hopelessness (actual)",
        "crisis resources given; BH outreach flagged",
        "discloses to the bot at night",
        "psychological (depression) + medical (pain-mood loop)",
        "safer disclosing anonymously",
        "hopeless, exhausted",
        "highest-value mental-health signal between visits"),
    "high"),
  A("portal.message", "inbound", 5,
    "Back pain worse — ibuprofen isn't cutting it",
    "My lower back has been worse for two weeks, the ibuprofen barely helps and it's affecting work and sleep. "
    "Can I get physical therapy or something stronger?",
    "Portal message: escalating chronic low-back pain refractory to OTC NSAID, impacting function/sleep. "
    "Requests PT vs. stronger analgesia. Note mood interplay from prior screen.",
    ann("treatment request",
        "pending triage (PT referral vs. med review)",
        "self-advocating",
        "medical (pain), functional (work/sleep)",
        "uses portal for care requests",
        "frustrated",
        "chronic-pain flare tied to mood"),
    "moderate"),
],
8: [  # Eva Casas, 62F — knee OA, prediabetes, IPV victim, refugee, isolation; naproxen
  A("call.care_coordinator", "inbound", 3,
    "Rescheduling — and something she almost didn't say",
    "COORD (via interpreter): calling to rebook your knee appointment\n"
    "PT: yes... it's hard to come when he's home. Sometimes it isn't safe to leave.\n"
    "COORD: Thank you for trusting me with that. Your safety matters as much as the knee. Can I connect you with "
    "someone who helps with exactly this, privately?\n"
    "PT: maybe. Please don't put it where he could see.",
    "Care-coordinator call (interpreter-assisted): rescheduling that surfaced an IPV safety concern. Patient "
    "requests confidentiality re: chart visibility. Warm handoff to advocacy offered; consent pending.",
    ann("rescheduling (surface) / IPV disclosure (actual)",
        "advocacy referral offered; confidentiality flagged; consent pending",
        "avoidant then discloses when safe",
        "safety (IPV), language access, social (isolation)",
        "fragile — trusts the coordinator, fears the chart",
        "fearful, guarded",
        "single most safety-critical unrouted disclosure"),
    "high"),
  A("call.nurse_triage", "inbound", 6,
    "Knee giving out, can't manage stairs",
    "PT (via interpreter): my knee is worse, it gives out and I can't do the stairs, the naproxen isn't enough\n"
    "NURSE: any locking, redness, or warmth?\n"
    "PT: no, just pain and it buckles\n"
    "NURSE: Let's advance imaging and get ortho involved — sounds like the OA is progressing.",
    "Nurse triage (interpreter): progressive knee OA with instability, NSAID-refractory, functional decline "
    "(stairs). Imaging + ortho referral advised.",
    ann("symptom report",
        "imaging + ortho referral advised",
        "engaged with interpreter support",
        "medical (OA progression), language access",
        "moderate",
        "worn down",
        "conservative therapy failing"),
    "moderate"),
],
9: [  # Hiedi Thiel, 30F — pregnancy, anemia, severe anxiety/panic, transport problem; iron, B12
  A("call.nurse_triage", "inbound", 3,
    "Panic attacks during pregnancy",
    "PT: I keep getting these panic attacks, heart pounding, can't breathe, and then I worry it's hurting the baby\n"
    "NURSE: Let's separate the two — during an episode, any bleeding, contractions, or chest pain that lasts?\n"
    "PT: no, it passes in ten minutes but it's terrifying\n"
    "NURSE: These sound like panic episodes, not obstetric emergencies. I'll connect perinatal mental health today.",
    "Nurse triage: recurrent panic episodes in pregnancy (known severe anxiety), self-limited, no obstetric red "
    "flags. Reassurance + same-day perinatal mental-health referral.",
    ann("symptom report + reassurance-seeking",
        "perinatal MH referral placed",
        "reaches out during crisis",
        "psychological (panic in pregnancy), reassurance",
        "high trust in nurse line",
        "frightened",
        "antenatal MH intervention point"),
    "moderate"),
  A("pharmacy.refill", "passive", 4,
    "Iron refill late; GI side effects noted",
    "SYSTEM: ferrous sulfate 325 MG — refill 15 days late. Prior portal note: 'iron upsets my stomach.' "
    "B12 injections on schedule.",
    "Pharmacy gap: iron non-refill in an anemic pregnant patient, with a prior tolerance complaint — likely "
    "side-effect-driven non-adherence rather than choice. Adherence support / alternate formulation indicated.",
    ann("n/a (passive log + prior complaint)",
        "gap unaddressed",
        "silent non-fill due to side effects",
        "medical (anemia treatment), adherence support",
        "n/a",
        "n/a",
        "treatable anemia quietly undertreated"),
    "moderate"),
],
10: [  # Isreal Howell, 85M — cardiometabolic, ischemic heart, NSTEMI hx, T2DM; many cardiac meds
  A("portal.message", "inbound", 5,
    "Ankles swelling and short of breath lying down",
    "My ankles have been really swollen this week and I need two pillows now to breathe at night. "
    "I've gained a few pounds too. Is this something to worry about?",
    "Portal message: new orthopnea + peripheral edema + weight gain in an 85M with ischemic heart disease — "
    "classic early decompensated heart failure. Requires prompt outreach, not an FYI. Routed to portal queue.",
    ann("symptom report",
        "pending review in portal queue",
        "proactive self-report",
        "medical (HF decompensation — urgent)",
        "trusts the portal to be read timely",
        "concerned",
        "early-HF window — the highest-value catch before an admission"),
    "high"),
  A("call.care_coordinator", "inbound", 6,
    "Skipping heart meds over the copay",
    "COORD: your pharmacy flagged the metoprolol hasn't been picked up — everything okay?\n"
    "PT: the copay went up and money's tight this month, so I've been stretching the pills, skipping some days\n"
    "COORD: Thank you for being honest — skipping the heart medicine isn't safe, and there's help for the cost. "
    "Let me set up financial assistance and a 90-day fill today.\n"
    "PT: I didn't want to make a fuss. The losartan's about due too.\n"
    "COORD: I'll sort both and let your cardiologist know.",
    "Care-coordinator call: cost-driven non-adherence — beta-blocker (and ARB) doses skipped due to copay in a "
    "complex cardiac patient. Financial assistance + 90-day fill arranged; cardiology to be notified. "
    "Rate/afterload control was silently interrupted.",
    ann("refill nudge (surface) / disclose cost-rationing of cardiac meds (actual)",
        "financial assistance + 90-day fill arranged; cardiology to be notified",
        "discloses when asked directly",
        "financial + adherence (cardiac meds)",
        "trusts coordinator enough to admit rationing",
        "embarrassed, practical",
        "silent cardiac-med lapse compounding HF risk"),
    "high"),
],
11: [  # Issac Mayer, 31M — obesity, reports of violence in environment
  A("call.care_coordinator", "inbound", 6,
    "It's not safe where I'm living",
    "COORD: following up on your wellness visit\n"
    "PT: honestly things at home have gotten worse, there's a lot of violence around where I live, I don't feel safe\n"
    "COORD: I'm really glad you told me. Let's talk options — I can connect you with resources and note safe ways "
    "to reach you.\n"
    "PT: yeah. just don't call in the evenings, that's when it's bad.",
    "Care-coordinator call: disclosure of community/household violence exposure. Safety resources offered; "
    "safe-contact window (avoid evenings) documented. No structured pathway from this note to the PCP.",
    ann("check-in (surface) / safety disclosure (actual)",
        "resources offered; safe-contact window noted; not routed to PCP",
        "discloses when re-engaged",
        "safety, social support",
        "trusts coordinator enough to disclose",
        "guarded, stressed",
        "unrouted safety signal"),
    "high"),
  A("portal.message", "inbound", 10,
    "Missed my recheck — can I redo the weight plan?",
    "Sorry I missed the last appointment, things have been chaotic. I still want to work on the weight stuff — "
    "can we restart that? Text is best for reaching me.",
    "Portal message: re-engagement after a no-show; renewed interest in weight management; requests text contact. "
    "Pattern of missed visits tied to unstable environment.",
    ann("re-engagement",
        "awaiting scheduling via text",
        "returns despite chaos",
        "behavioral (weight), communication access",
        "wants to keep trying",
        "apologetic, motivated",
        "re-engagement after disengagement"),
    "low"),
],
12: [  # Julius Renner, 35M — HTN initiation, chronic LBP, housing unsatisfactory, unemployed; HCTZ/lisinopril/amlodipine, tylenol
  A("pharmacy.refill", "passive", 3,
    "Blood-pressure meds not picked up",
    "SYSTEM: lisinopril + amlodipine — 18 days overdue; HCTZ picked up. Patient told pharmacy 'which one can I "
    "skip, money's tight.' New to therapy.",
    "Pharmacy gap: partial fill of a 3-drug antihypertensive regimen with an explicit cost-rationing statement, "
    "in a newly-treated hypertensive. Adherence at risk on affordability; simplify/assist indicated.",
    ann("n/a (passive log + cost statement)",
        "partial adherence; cost barrier surfaced",
        "rationing meds by cost",
        "financial + regimen simplification",
        "n/a",
        "n/a",
        "new-therapy adherence collapsing on cost"),
    "high"),
  A("call.nurse_triage", "inbound", 5,
    "Back pain and can't work",
    "PT: my back's been bad, I can't stand for long and I'm trying to find work but can't with this\n"
    "NURSE: is the pain radiating down a leg, any numbness or weakness?\n"
    "PT: mostly the low back, no numbness\n"
    "NURSE: Let's get you into PT and review your pain plan — and I'll note the work-capacity piece for the provider.",
    "Nurse triage: mechanical chronic low-back pain limiting work capacity; no radicular red flags. PT referral "
    "and pain-plan review; social/work-capacity context flagged.",
    ann("symptom report + functional concern",
        "PT referral; pain plan review",
        "engaged",
        "medical (pain), functional (employment)",
        "moderate",
        "stressed about work/money",
        "pain-driven socioeconomic spiral"),
    "moderate"),
],
13: [  # Lala Casper, 48F — IPV, recurrent UTI, criminal record, stress; epi-pen, loratadine, hydrocortisone
  A("call.care_coordinator", "inbound", 3,
    "Safety planning, quietly",
    "COORD: is now a safe time to talk?\n"
    "PT: for a few minutes. He's out.\n"
    "COORD: Last visit you shared some things about home. I want to make sure you have a plan and a private way to "
    "reach help.\n"
    "PT: I have a bag packed. I just... I don't trust that it stays private. My record's already been used against me.\n"
    "COORD: I hear that. Here's how confidentiality works, and a hotline that keeps no shared record.",
    "Care-coordinator call: IPV safety-planning follow-up. Patient has an escape plan; expresses distrust of "
    "record confidentiality (prior harm from records). Confidential hotline provided.",
    ann("safety planning",
        "safety plan reinforced; confidential hotline given",
        "engages in a safe window",
        "safety (IPV), privacy/confidentiality",
        "ambivalent — history of records used against her",
        "wary, resolved",
        "active safety management between visits"),
    "high"),
  A("call.nurse_triage", "inbound", 6,
    "UTI symptoms are back",
    "PT: the burning and urgency are back again, I get these all the time\n"
    "NURSE: any fever or flank pain?\n"
    "PT: no, just the usual\n"
    "NURSE: I'll arrange a urine test today; given how often this recurs let's talk prevention too.",
    "Nurse triage: recurrent UTI symptoms, no upper-tract signs. Same-day UA; recurrence-prevention discussion "
    "offered.",
    ann("symptom report",
        "UA arranged; prevention discussion offered",
        "engaged for physical symptoms",
        "medical (recurrent UTI)",
        "trusts nurse line for medical issues",
        "matter-of-fact",
        "recurrent-condition management"),
    "low"),
],
14: [  # Lamont Ernser, 52M — social isolation, criminal record, sleep; diphenhydramine
  A("chatbot.symptom_checker", "inbound", 3,
    "Can't sleep, taking Benadryl nightly",
    "PT: I take Benadryl every night to sleep, is that bad? been doing it months\n"
    "BOT: Nightly diphenhydramine can lose effect and carries risks over time, especially for daytime grogginess. "
    "Loud snoring or gasping at night?\n"
    "PT: my brother said I stop breathing sometimes when I used to have someone around\n"
    "BOT: That's worth a sleep evaluation — I can flag it for follow-up.",
    "Symptom-checker: chronic nightly diphenhydramine use for insomnia; secondhand report of witnessed apneas. "
    "Sleep-study evaluation flagged; anticholinergic-risk counseling given.",
    ann("self-care question (surface) / undiagnosed OSA clue (actual)",
        "sleep eval flagged; counseling given",
        "discloses to bot",
        "medical (OSA screen), medication safety",
        "isolated — no one to notice symptoms now",
        "resigned",
        "OSA hiding behind self-medication"),
    "moderate"),
  A("portal.message", "inbound", 5,
    "Following up on a sleep study",
    "The chat thing suggested I might have sleep apnea. Can I actually get a sleep study set up? I live alone so "
    "no one can really tell me what happens at night.",
    "Portal message: patient-initiated request for sleep-study referral following chatbot advice; notes isolation "
    "limits symptom corroboration. Route to sleep medicine.",
    ann("referral request",
        "pending sleep-medicine referral",
        "self-advocating after bot nudge",
        "medical (OSA workup)",
        "acts on the bot's suggestion",
        "hopeful",
        "converting a middle-zone clue into care"),
    "low"),
],
15: [  # Latoyia Wilkinson, 75F — post-SNF, CKD from DM, T2DM; clopidogrel/metoprolol/nitro/statin/B12
  A("call.home_health", "inbound", 10,
    "Hypoglycemic episode at home",
    "AIDE: calling it in — she got shaky, sweaty, confused before lunch; glucose read 52. Gave juice, came back to 78.\n"
    "NURSE: good catch. Was she eating normally? Any med changes?\n"
    "AIDE: she skipped breakfast, said she wasn't hungry, but took all her pills\n"
    "NURSE: We need to review the diabetes regimen around her intake — I'll escalate to the provider today.",
    "Home-health call: symptomatic hypoglycemia (52 mg/dL) after skipped meal with full medication dosing, in a "
    "diabetic with CKD (altered drug clearance). Treated by aide; provider review escalated.",
    ann("incident report",
        "treated on scene; provider review escalated",
        "aide vigilant; patient minimizes appetite loss",
        "medical (hypoglycemia, regimen-to-intake mismatch, CKD dosing)",
        "high trust in aide",
        "shaken but downplaying",
        "medication-safety near-miss caught only in the home"),
    "high"),
  A("call.nurse_triage", "inbound", 16,
    "Dizzy and worried about the kidneys",
    "PT: I've been lightheaded standing up, and I know my kidneys aren't great, are my pills too strong?\n"
    "NURSE: any falls, chest pain, or fainting?\n"
    "PT: no falls yet, just wobbly\n"
    "NURSE: With your kidney function we should recheck labs and the doses — I'll get orthostatics and a metabolic panel.",
    "Nurse triage: orthostatic lightheadedness in CKD patient on cardiac/antihypertensive meds. Renal dosing "
    "review, orthostatics, and metabolic panel arranged; fall-risk caution.",
    ann("symptom report + medication concern",
        "labs + orthostatics arranged",
        "engaged, health-literate about her CKD",
        "medical (renal dosing, fall prevention)",
        "moderate–high",
        "worried",
        "CKD medication-safety surveillance"),
    "moderate"),
],
16: [  # Margarita Rau, 43F — high-risk pregnancy at 43, HTN, obesity, prediabetes, anemia, IPV
  A("portal.device_upload", "passive", 6,
    "Home BP climbing in third trimester",
    "SYSTEM: Home BP sync — 3 readings ≥150/95 over 4 days, up from 132/84. Third trimester. No threshold alert "
    "configured; not reviewed.",
    "Passive upload: rising home BP (≥150/95) in a 43yo high-risk pregnancy — a preeclampsia warning sitting "
    "unreviewed. Warrants urgent OB contact and labs (protein, LFTs, platelets).",
    ann("n/a (passive stream)",
        "captured but unreviewed",
        "adhering to home BP monitoring",
        "medical (preeclampsia surveillance — urgent)",
        "n/a",
        "n/a",
        "highest-acuity unread signal in the pregnancy"),
    "high"),
  A("call.care_coordinator", "inbound", 5,
    "Getting to the high-risk OB — and safety at home",
    "COORD: checking you can make the maternal-fetal medicine visits\n"
    "PT: it's far and rides are hard, and... it's tense at home, he doesn't like me going to appointments\n"
    "COORD: Both matter. Let me arrange transportation and, privately, some support around what you're describing.\n"
    "PT: okay. quietly, please.",
    "Care-coordinator call: transportation barrier to MFM visits plus an IPV disclosure (partner obstructing "
    "care) in a high-risk pregnancy. Transport arranged; confidential advocacy offered.",
    ann("logistics (surface) / IPV + access disclosure (actual)",
        "transport arranged; advocacy offered confidentially",
        "discloses when re-engaged",
        "safety (IPV), transportation, high-risk OB access",
        "trusts coordinator; fears partner",
        "anxious, guarded",
        "access + safety barriers to critical prenatal care"),
    "high"),
],
17: [  # Marty Toy, 34M — gingival disease, military service, obesity
  A("portal.message", "inbound", 4,
    "Scheduling dental around a deployment",
    "I have the periodontal treatment referral but I'm about to be away on a military assignment for a few months. "
    "Can we do it before I leave, or is there something I should keep up while I'm gone?",
    "Portal message: patient balancing periodontal treatment against an upcoming deployment; requests expedited "
    "scheduling + interim self-care guidance. Continuity-of-care logistics.",
    ann("scheduling + continuity",
        "expedited scheduling pending; interim guidance requested",
        "proactive, planning ahead",
        "logistical (timing), informational (interim care)",
        "engaged with the system",
        "organized, practical",
        "continuity around a service absence"),
    "low"),
  A("chatbot.symptom_checker", "inbound", 2,
    "Bleeding gums — what do I do at home?",
    "PT: my gums bleed when I brush, dentist said gum disease. what actually helps at home?\n"
    "BOT: Consistent brushing/flossing, an antiseptic rinse, and not skipping the periodontal cleanings. "
    "Bleeding that worsens or comes with pain/swelling needs a prompt visit.\n"
    "PT: got it, thanks",
    "Symptom-checker: home-care guidance for periodontal disease; escalation criteria provided. Low-acuity "
    "self-management.",
    ann("self-care guidance",
        "advice given",
        "information-seeking",
        "informational (oral self-care)",
        "uses bot for quick answers",
        "neutral",
        "self-management between dental visits"),
    "low"),
],
18: [  # Melodee Satterfield, 20F — pregnancy, chronic pain; hydrocodone/acetaminophen, tramadol
  A("pharmacy.refill", "inbound", 4,
    "Early opioid refill request during pregnancy",
    "PT (pharmacy note): requesting early refill of hydrocodone/acetaminophen; states pain uncontrolled. "
    "Pregnant. Pharmacist held for prescriber review re: pregnancy + neonatal withdrawal risk.",
    "Pharmacy interaction: early opioid refill in pregnancy, held for prescriber review. Balances genuine "
    "pain-management need against NAS (neonatal abstinence) risk and taper planning. Needs coordinated OB + pain "
    "plan, not a reflexive fill or denial.",
    ann("refill request (surface) / uncontrolled pain + taper tension (actual)",
        "held for prescriber review; OB coordination needed",
        "engaged but fears being labeled 'drug-seeking'",
        "medical (pain control), fetal safety (NAS), non-stigmatizing plan",
        "guarded — expects judgment",
        "anxious, defensive",
        "high-stakes medication-safety decision point"),
    "high"),
  A("call.nurse_triage", "inbound", 6,
    "Pain and afraid of being judged",
    "PT: I know how it looks asking about pain meds while pregnant, but I'm really hurting and scared for the baby too\n"
    "NURSE: You did the right thing calling. We can build a plan that protects both you and the baby — pain "
    "specialist and OB together.\n"
    "PT: I don't want them to think I'm just after pills\n"
    "NURSE: This is about safe care. Let me set up that joint plan.",
    "Nurse triage: pregnant patient with chronic pain seeking non-stigmatizing, coordinated pain management. "
    "Reassurance given; joint pain-medicine + OB planning initiated.",
    ann("help-seeking + fear of stigma",
        "coordinated pain/OB plan initiated",
        "reaches out despite fear of judgment",
        "medical (safe analgesia), psychological (stigma), fetal safety",
        "tentative trust after reassurance",
        "scared, defensive",
        "shaping a safe pain plan before delivery"),
    "moderate"),
],
19: [  # Monica Hilpert, 76F — post-SNF, osteoporosis, pain (meperidine/naproxen), IPV, isolation
  A("call.home_health", "inbound", 6,
    "A minor fall at home",
    "AIDE: reporting a fall — she slipped getting to the bathroom overnight, no head strike, sore hip, moving okay\n"
    "NURSE: given the osteoporosis we should image the hip and review night-time safety\n"
    "AIDE: she didn't want to mention it, said she didn't want to go back to the nursing home\n"
    "NURSE: understood — let's keep her home safely. Ordering imaging and a home safety review.",
    "Home-health call: unwitnessed overnight fall in an osteoporotic 76F; no head strike, hip soreness. Imaging "
    "and home-safety review ordered. Patient minimized to avoid re-institutionalization.",
    ann("incident report",
        "hip imaging + home-safety review ordered",
        "aide reports; patient conceals to stay home",
        "medical (fracture rule-out), safety (falls), autonomy",
        "high trust in aide; fears the system",
        "minimizing, fearful of losing independence",
        "fall-injury catch that would otherwise be hidden"),
    "high"),
  A("call.nurse_triage", "inbound", 14,
    "Pain meds and feeling foggy",
    "PT: the pain pills help but I feel foggy and off-balance, and I'm scared of falling again\n"
    "NURSE: which pain medicine, and how often? Meperidine can build up and cause exactly that in older adults.\n"
    "PT: the meperidine, most days\n"
    "NURSE: Let's review that with your provider — safer options exist. I'll flag it today.",
    "Nurse triage: meperidine-associated cognitive fogginess/imbalance in an elderly faller — a Beers-criteria "
    "concern. Regimen review flagged for safer analgesia.",
    ann("symptom + medication concern",
        "provider medication review flagged",
        "engaged, links meds to fall fear",
        "medical (deprescribing meperidine, fall prevention)",
        "trusts nurse line",
        "worried",
        "medication-safety optimization"),
    "moderate"),
],
20: [  # Nigel Ankunding, 52M — prediabetes, chronic sinusitis, criminal record, isolation, stress
  A("chatbot.symptom_checker", "inbound", 3,
    "Trying to turn prediabetes around, alone",
    "PT: I've got prediabetes and want to fix it before it becomes diabetes, but I'm on my own and it's hard to stay on track\n"
    "BOT: You can absolutely lower that risk. Would a coach, a group, or a dietitian referral help you stick with it?\n"
    "PT: a check-in from someone would help, I don't have people around\n"
    "BOT: I'll flag you for a coordinator to set up regular check-ins.",
    "Symptom-checker: motivated prediabetic seeking accountability amid social isolation. Coordinator check-in "
    "program flagged (not yet routed). Engagement opportunity.",
    ann("informational (surface) / accountability + connection (actual)",
        "coordinator check-ins flagged",
        "motivated but isolated",
        "behavioral (prevention), social (isolation)",
        "opens up to bot",
        "determined, lonely",
        "prevention window with high engagement leverage"),
    "moderate"),
  A("portal.message", "inbound", 6,
    "Sinus infection back again",
    "Sinuses are acting up again — pressure and congestion for over a week. This keeps happening. "
    "Anything I can do besides wait it out?",
    "Portal message: recurrent chronic sinusitis flare; patient frustrated by recurrence pattern. Consider ENT "
    "evaluation for recurrence; interim management guidance.",
    ann("treatment request",
        "pending review; ENT referral consideration",
        "self-directed",
        "medical (recurrence workup)",
        "uses portal appropriately",
        "frustrated",
        "recurrent-condition pattern"),
    "low"),
],
21: [  # Nola Kling, 75F — hospice, end-stage colon cancer, chronic pain, IPV hx
  A("call.hospice_nurse", "inbound", 4,
    "Pain crisis at home overnight",
    "FAMILY: mom's pain broke through again last night, she was crying, the current dose isn't holding\n"
    "NURSE: I'm sorry — comfort is the priority now. Let's titrate the long-acting dose and make sure you have "
    "breakthrough medication ready. I'll visit today.\n"
    "FAMILY: thank you. we just don't want her to suffer\n"
    "NURSE: That's exactly what we'll prevent. You're doing beautifully caring for her.",
    "Hospice nurse call: uncontrolled breakthrough pain overnight. Long-acting opioid titration + breakthrough "
    "plan; same-day home visit. Comfort-focused; family reassured.",
    ann("symptom report (comfort)",
        "opioid titration + breakthrough plan; home visit scheduled",
        "family highly engaged",
        "medical (pain/comfort), family support",
        "high trust in hospice team",
        "distressed, loving",
        "active comfort management at end of life"),
    "high"),
  A("call.family_caregiver", "inbound", 7,
    "Daughter reaching her limit",
    "DAUGHTER: I'm doing everything I can but I'm exhausted, I haven't slept, and I'm scared I'll miss something\n"
    "NURSE: You are carrying so much. Let's get you respite hours and a volunteer this week, and I'll walk you "
    "through what to expect so nothing catches you off guard.\n"
    "DAUGHTER: that would mean everything. I just want to be her daughter again, not only her nurse.",
    "Family-caregiver call: caregiver burnout and anticipatory grief. Respite hours + volunteer arranged; "
    "expectation-setting education provided. Caregiver support is part of the plan of care.",
    ann("caregiver support-seeking",
        "respite + volunteer arranged; education provided",
        "highly engaged, overwhelmed",
        "caregiver respite, anticipatory-grief support, education",
        "high trust in hospice team",
        "exhausted, grieving",
        "caregiver sustainability near end of life"),
    "high"),
],
22: [  # Solomon Macejkovic, 75M — hospice, colon cancer + cardiac; clopidogrel/metoprolol/nitro/statin
  A("call.hospice_nurse", "inbound", 4,
    "Declining, eating less, more short of breath",
    "FAMILY: he's sleeping most of the day now, barely eating, and gets breathless just sitting up\n"
    "NURSE: These are expected changes as things progress. Let's add comfort measures for the breathing and "
    "simplify medicines that aren't helping his comfort now.\n"
    "FAMILY: should we stop the heart pills?\n"
    "NURSE: We'll review each one for comfort benefit — I'll go over that with you today.",
    "Hospice nurse call: functional decline, anorexia, dyspnea at rest consistent with disease progression. "
    "Comfort measures for dyspnea; deprescribing review of cardiac meds for comfort-only goals.",
    ann("symptom report (comfort)",
        "comfort measures added; deprescribing review initiated",
        "family engaged",
        "medical (dyspnea comfort, deprescribing), family guidance",
        "high trust in hospice team",
        "sad, accepting",
        "progression management at end of life"),
    "high"),
  A("call.family_caregiver", "inbound", 6,
    "What happens next — preparing the family",
    "SON: we don't really know what to expect or what to do when the time comes, and it scares us\n"
    "NURSE: I'll walk you through the signs and exactly who to call — you won't be alone, someone is available "
    "any hour.\n"
    "SON: that helps. we want him comfortable and at home\n"
    "NURSE: That's our plan. Let's make sure everything's in place for that.",
    "Family-caregiver call: anticipatory guidance and end-of-life planning; reassurance re: 24/7 availability. "
    "Reinforces goal of comfortable death at home.",
    ann("preparation / support-seeking",
        "anticipatory guidance provided; 24/7 access reaffirmed",
        "family engaged, fearful",
        "education (dying process), family support, care logistics",
        "high trust in hospice team",
        "frightened, seeking reassurance",
        "preparing for end of life at home"),
    "moderate"),
],
23: [  # Traci Wiegand, 65F — post-SNF, T2DM, hyperglycemia, metabolic syndrome
  A("portal.device_upload", "passive", 5,
    "Glucometer readings running high",
    "SYSTEM: Glucometer sync — 7-day fasting average 198 mg/dL (target <130); several post-meal >250. "
    "Uploads consistent; no clinician review.",
    "Passive upload: persistent hyperglycemia (fasting ~198, post-prandial >250) post-SNF discharge. "
    "Regimen intensification likely needed; trend unreviewed.",
    ann("n/a (passive stream)",
        "captured but unreviewed",
        "consistently uploading data",
        "medical (glycemic control — regimen adjustment)",
        "n/a",
        "n/a",
        "titration signal sitting unread post-discharge"),
    "moderate"),
  A("call.nurse_triage", "inbound", 22,
    "Numbness and tingling in the feet",
    "PT: my feet have been numb and tingly, especially at night, is that the diabetes?\n"
    "NURSE: it can be — any sores, color changes, or wounds you can't feel?\n"
    "PT: no wounds that I've noticed\n"
    "NURSE: Let's get a foot exam and check your control; we want to catch neuropathy early and protect your feet.",
    "Nurse triage: new peripheral neuropathy symptoms in long-standing T2DM. Podiatry/foot-exam referral and "
    "glycemic review; foot-protection education.",
    ann("symptom report",
        "foot exam / podiatry referral; glycemic review",
        "engaged",
        "medical (neuropathy screen, foot care)",
        "trusts nurse line",
        "mildly worried",
        "diabetes-complication surveillance"),
    "moderate"),
],
24: [  # Van O'Reilly, 42M — hand OA, anxiety, stress; naproxen
  A("chatbot.symptom_checker", "inbound", 3,
    "Anxiety spiking late at night",
    "PT: my anxiety's been bad, racing thoughts at night, chest feels tight and then I worry it's my heart\n"
    "BOT: That tightness with racing thoughts can be anxiety, though chest symptoms always deserve care if severe "
    "or with exertion. Would talking to someone help — therapy or your provider?\n"
    "PT: maybe therapy. I keep meaning to and not doing it\n"
    "BOT: I can flag a behavioral-health outreach so someone reaches out to you.",
    "Symptom-checker after hours: anxiety with somatic chest symptoms; health anxiety re: cardiac cause. "
    "Behavioral-health outreach flagged; safety-netting on exertional chest symptoms.",
    ann("reassurance-seeking (surface) / accepting a BH nudge (actual)",
        "BH outreach flagged; cardiac safety-netting given",
        "discloses to bot at night, avoids booking himself",
        "psychological (anxiety), reassurance",
        "lower barrier with the bot",
        "anxious, avoidant",
        "converting avoidance into a BH contact"),
    "moderate"),
  A("portal.message", "inbound", 6,
    "Hand pain affecting my work",
    "The arthritis in my hands is making it hard to grip and type, and the naproxen upsets my stomach. "
    "Can I see someone about hand therapy or a different medication?",
    "Portal message: hand OA with functional impairment (grip/typing) and NSAID GI intolerance. Requests "
    "occupational/hand therapy and analgesic alternative.",
    ann("treatment request",
        "pending triage (OT referral, analgesic review)",
        "self-advocating",
        "medical (OA management), functional (work), GI-safe analgesia",
        "uses portal appropriately",
        "frustrated",
        "functional OA management"),
    "low"),
],
}


def main() -> None:
    recs = [json.loads(line) for line in RAW.read_text().splitlines() if line.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    batch = MiddleZoneBatch()
    plan = []

    for idx, rec in enumerate(recs):
        meta = rec["metadata"]
        pid = meta["patient_id"]
        idx_date = meta["date"]
        tz = idx_date[19:] if len(idx_date) > 19 else "-08:00"  # keep source offset
        pt = rec.get("patient_context", {}).get("patient", {})
        nm = pt.get("name", [{}])[0]
        name = (" ".join(nm.get("given", [])) + " " + nm.get("family", "")).strip() or pid

        specs = AUTHORED.get(idx, [])
        entry = {"patient_index": idx, "patient_id": pid, "name": name,
                 "index_visit": idx_date[:10], "artifacts": []}
        for n, s in enumerate(specs, start=1):
            d = add_months(idx_date, s["months"])
            t = s["time"] or CHANNEL_TIME.get(s["channel"], "12:00")
            date_str = f"{d.isoformat()}T{t}:00{tz}"
            batch.mk(pid=pid, name=name, n=n, date_str=date_str,
                     channel=s["channel"], direction=s["direction"], title=s["title"],
                     transcript=s["transcript"], note=s["note"],
                     annotations=s["ann"], signal_value=s["signal"],
                     months_after_index=s["months"])
            entry["artifacts"].append({
                "n": n, "date": date_str[:10], "channel": s["channel"],
                "title": s["title"], "signal_value": s["signal"],
            })
        plan.append(entry)

    jsonl = OUT_DIR / "middle-zone-artifacts.jsonl"
    js = OUT_DIR / "middle-zone-artifacts.json"
    mp = OUT_DIR / "master_plan.json"
    n = batch.save_jsonl(jsonl)
    batch.save_json(js)
    mp.write_text(json.dumps(plan, indent=2))

    missing = [i for i in range(len(recs)) if not AUTHORED.get(i)]
    print(f"✓ {n} middle-zone artifacts for {len(recs)} patients "
          f"({n // max(len(recs),1)}x each)")
    print(f"  → {jsonl.relative_to(ROOT)}")
    print(f"  → {js.relative_to(ROOT)}")
    print(f"  → {mp.relative_to(ROOT)}")
    if missing:
        print(f"  ⚠ patients without artifacts: {missing}")
    # quick channel spread
    from collections import Counter
    spread = Counter(r["metadata"]["channel"] for r in batch.records)
    print("  channels:", dict(sorted(spread.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
