"""Loads real patient records from data/patients/<folder>/ (Synthea/FHIR
trajectories) and the data/regions_of_concern.json side file.

Each patient folder holds a `*_full_trajectory.json` — a list of encounters,
each with metadata, patient_context, transcript, note, and after_visit_summary.
We flatten that into an "all information" record the SPA can render, and expose
the brain regions-of-concern dots authored per patient.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATIENTS_DIR = ROOT / "data" / "patients"
REGIONS_FILE = ROOT / "data" / "regions_of_concern.json"


def _trajectory_file(folder: Path) -> Path | None:
    """Find the trajectory JSON in a patient folder."""
    candidates = sorted(folder.glob("*full_trajectory.json")) or [
        p for p in sorted(folder.glob("*.json"))
        if _is_encounter_list(p)
    ]
    return candidates[0] if candidates else None


def _is_encounter_list(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, list) and bool(data) and isinstance(data[0], dict) \
            and "encounter_fhir" in data[0]
    except Exception:  # noqa: BLE001
        return False


def _person_name(patient: dict) -> str:
    names = patient.get("name") or [{}]
    n = names[0]
    parts = list(n.get("prefix", [])) + list(n.get("given", [])) + ([n.get("family")] if n.get("family") else [])
    return " ".join(p for p in parts if p) or "Unknown"


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None


def _age(birth: str | None, ref: date | None) -> int | None:
    b = _parse_date(birth)
    r = ref or date.today()
    if not b:
        return None
    return r.year - b.year - ((r.month, r.day) < (b.month, b.day))


def _address(patient: dict) -> str:
    addr = (patient.get("address") or [{}])[0]
    bits = [addr.get("city"), addr.get("state"), addr.get("country")]
    return ", ".join(b for b in bits if b)


def _richest_summary(encounters: list[dict]) -> dict:
    """Pick the longitudinal_summary with the most conditions (most complete)."""
    best, best_n = {}, -1
    for enc in encounters:
        ls = enc.get("patient_context", {}).get("longitudinal_summary", {}) or {}
        n = len(ls.get("condition_labels", []))
        if n > best_n:
            best, best_n = ls, n
    return best


def parse_record(folder_name: str) -> dict[str, Any]:
    folder = PATIENTS_DIR / folder_name
    tf = _trajectory_file(folder) if folder.is_dir() else None
    if not tf:
        raise FileNotFoundError(f"No trajectory for record '{folder_name}'")
    encounters = json.loads(tf.read_text(encoding="utf-8"))
    encounters = sorted(encounters, key=lambda e: e.get("metadata", {}).get("date", ""))

    patient = encounters[-1].get("patient_context", {}).get("patient", {})
    last_date = _parse_date(encounters[-1].get("metadata", {}).get("date"))
    summary = _richest_summary(encounters)

    return {
        "folder": folder_name,
        "patient_id": patient.get("id"),
        "name": _person_name(patient),
        "gender": patient.get("gender"),
        "birthDate": patient.get("birthDate"),
        "age": _age(patient.get("birthDate"), last_date),
        "marital": (patient.get("maritalStatus") or {}).get("text"),
        "address": _address(patient),
        "language": ((patient.get("communication") or [{}])[0].get("language") or {}).get("text"),
        "longitudinal_summary": {
            "resource_counts": summary.get("resource_counts", {}),
            "condition_labels": summary.get("condition_labels", []),
            "medication_labels": summary.get("medication_labels", []),
        },
        "encounters": [
            {
                "id": enc.get("id"),
                "date": (enc.get("metadata", {}) or {}).get("date"),
                "visit_title": (enc.get("metadata", {}) or {}).get("visit_title"),
                "visit_type": (enc.get("metadata", {}) or {}).get("visit_type"),
                "status": (enc.get("metadata", {}) or {}).get("status"),
                "related_resource_counts": (enc.get("metadata", {}) or {}).get("related_resource_counts", {}),
                "transcript": enc.get("transcript"),
                "note": enc.get("note"),
                "after_visit_summary": enc.get("after_visit_summary"),
            }
            for enc in encounters
        ],
    }


def list_records() -> list[dict[str, Any]]:
    if not PATIENTS_DIR.is_dir():
        return []
    out = []
    for folder in sorted(p for p in PATIENTS_DIR.iterdir() if p.is_dir()):
        try:
            rec = parse_record(folder.name)
        except Exception:  # noqa: BLE001 — skip unreadable folders
            continue
        conds = rec["longitudinal_summary"]["condition_labels"]
        out.append({
            "folder": rec["folder"],
            "name": rec["name"],
            "age": rec["age"],
            "gender": rec["gender"],
            "encounters": len(rec["encounters"]),
            "headline": _headline(conds),
            # Lightweight encounter timeline (dates + type) for the patient chooser.
            "timeline": [
                {
                    "date": (e.get("date") or "")[:10],
                    "title": e.get("visit_title") or e.get("visit_type") or "Encounter",
                    "type": _visit_category(e),
                }
                for e in rec["encounters"]
                if e.get("date")
            ],
        })
    return out


def _visit_category(enc: dict) -> str:
    """Coarse encounter category for timeline marker color.

    Prefer the human ``visit_title``; fall back to ``visit_type`` with its
    SNOMED qualifier stripped (e.g. "...(procedure)") so the qualifier doesn't
    falsely match the procedure bucket.
    """
    title = (enc.get("visit_title") or "").lower()
    vtype = re.sub(r"\(.*?\)", "", enc.get("visit_type") or "").lower()
    text = title or vtype
    if any(k in text for k in ("emergency", "ed visit", " ed ", "acute", "urgent", "stroke", "infarction")):
        return "acute"
    if any(k in text for k in ("admission", "inpatient", "hospital", "snf", "discharge")):
        return "hospitalization"
    if any(k in text for k in ("surgery", "operation", "cath", "stent", "replacement", "biopsy", "angioplasty")):
        return "procedure"
    return "routine"


def _headline(condition_labels: list[str]) -> str:
    priority = ["cerebral", "stroke", "atrial fibrillation", "myocardial",
                "ischemic heart", "diabetes"]
    for key in priority:
        for c in condition_labels:
            if key in c.lower():
                return c.split(" (")[0]
    return condition_labels[0].split(" (")[0] if condition_labels else ""


def load_regions(folder_name: str) -> list[dict[str, Any]]:
    if not REGIONS_FILE.exists():
        return []
    data = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    return data.get(folder_name, [])


# ---- Middle-zone artifacts (data/middle-zone/) --------------------------- #
MIDDLE_ZONE_FILE = ROOT / "data" / "middle-zone" / "middle-zone-artifacts.json"

# Which channels surface in which pane, plus display source + icon.
_CONV_CHANNELS = {
    "call.nurse_triage": ("Nurse triage line", "📞", "phone"),
    "call.care_coordinator": ("Care coordinator", "📞", "phone"),
    "call.home_health": ("Home health aide", "🏠", "phone"),
    "call.hospice_nurse": ("Hospice nurse", "📞", "phone"),
    "call.family_caregiver": ("Family caregiver", "👪", "phone"),
    "chatbot.symptom_checker": ("Symptom-checker chatbot", "💬", "chat"),
}
_PORTAL_CHANNELS = {
    "portal.message": ("Secure message", "✉️"),
    "portal.device_upload": ("Device upload", "📈"),
    "pharmacy.refill": ("Pharmacy", "💊"),
}


def load_middle_zone(folder_name: str) -> dict[str, list[dict[str, Any]]]:
    """Middle-zone artifacts for a record, split into conversation vs portal.

    Resolves the record's ``patient_id`` (shared with the raw cohort) and
    filters the generated artifacts to that patient.
    """
    empty = {"conversations": [], "portal": []}
    if not MIDDLE_ZONE_FILE.exists():
        return empty
    try:
        pid = parse_record(folder_name).get("patient_id")
    except FileNotFoundError:
        return empty
    if not pid:
        return empty

    artifacts = json.loads(MIDDLE_ZONE_FILE.read_text(encoding="utf-8"))
    mine = [a for a in artifacts if a.get("metadata", {}).get("patient_id") == pid]
    mine.sort(key=lambda a: a["metadata"].get("date", ""))

    conversations, portal = [], []
    for a in mine:
        m = a["metadata"]
        ann = a.get("annotations", {})
        ch = m.get("channel", "")
        date = (m.get("date") or "")[:10]
        if ch in _CONV_CHANNELS:
            source, icon, kind = _CONV_CHANNELS[ch]
            conversations.append({
                "channel": ch, "source": source, "icon": icon, "type": kind,
                "date": date, "title": m.get("title", ""),
                "transcript": a.get("transcript", ""),
                "intent": ann.get("intent", ""),
                "needs": ann.get("needs", ""),
                "sentiment": ann.get("sentiment", ""),
                "journey_position": ann.get("journey_position", ""),
                "signal_value": ann.get("signal_value", "low"),
            })
        elif ch in _PORTAL_CHANNELS:
            source, icon = _PORTAL_CHANNELS[ch]
            portal.append({
                "channel": ch, "source": source, "icon": icon,
                "date": date, "title": m.get("title", ""),
                "direction": m.get("direction", ""),
                "detail": a.get("note", ""),
                "transcript": a.get("transcript", ""),
                "needs": ann.get("needs", ""),
                "signal_value": ann.get("signal_value", "low"),
            })
    return {"conversations": conversations, "portal": portal}
