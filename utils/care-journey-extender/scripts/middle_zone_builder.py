#!/usr/bin/env python3
"""Assemble *middle-zone* artifacts for an ambient-FHIR patient cohort.

The care-journey-extender's `record_builder.py` builds physician *visits*
(transcript + note + AVS). This sibling builds the **middle zone**: the
between-visit, non-physician touchpoints an encounter-scoped tool never sees —
nurse-line and care-coordinator calls, patient-portal messages, pharmacy refill
logs, home-health check-ins, chatbot/symptom-checker sessions, passive device
uploads, and hospice/family calls.

Each artifact keeps the source dataset's dual `transcript` + `note` shape (so it
reads like the raw data) and adds an `annotations` block using the canonical
call-transcript model: intent / outcome / engagement / needs / trust /
sentiment / journey_position / signal_value.

Usage:

    from middle_zone_builder import MiddleZoneBatch
    b = MiddleZoneBatch()
    b.mk(pid="...", name="...", n=1, date_str="2024-11-18T21:40:00-08:00",
         channel="chatbot.symptom_checker", direction="inbound",
         title="Late-night migraine self-check",
         transcript="PT: ...\nBOT: ...", note="Automated session ...",
         annotations={...}, signal_value="moderate",
         months_after_index=3)
    b.save_jsonl("data/middle-zone/middle-zone-artifacts.jsonl")
"""
from __future__ import annotations

import json


# Allowed channels (documented; not enforced) — keep artifacts realistic.
CHANNELS = {
    "call.nurse_triage", "call.care_coordinator", "call.home_health",
    "call.hospice_nurse", "call.family_caregiver",
    "portal.message", "portal.device_upload",
    "pharmacy.refill", "chatbot.symptom_checker",
}

_REQUIRED_ANNOTATIONS = (
    "intent", "outcome", "engagement", "needs", "trust",
    "sentiment", "journey_position",
)


class MiddleZoneBatch:
    def __init__(self):
        self.records = []

    def mk(self, pid, name, n, date_str, channel, direction, title,
           transcript, note, annotations, signal_value, months_after_index=None):
        missing = [k for k in _REQUIRED_ANNOTATIONS if k not in annotations]
        if missing:
            raise ValueError(f"{pid} mz{n}: missing annotations {missing}")
        if signal_value not in ("high", "moderate", "low"):
            raise ValueError(f"{pid} mz{n}: bad signal_value {signal_value!r}")
        aid = f"{pid}-mz{n}"
        ann = dict(annotations)
        ann["signal_value"] = signal_value
        self.records.append({
            "id": f"{pid}::{aid}",
            "metadata": {
                "source": "synthetic-middle-zone",
                "synthetic": True,
                "patient_id": pid,
                "patient_name": name,
                "artifact_id": aid,
                "date": date_str,
                "zone": "middle",
                "channel": channel,
                "direction": direction,        # inbound | outbound | passive
                "title": title,
                "status": "logged",
                "months_relative_to_index_visit": months_after_index,
            },
            "transcript": transcript.strip(),
            "note": note.strip(),
            "annotations": ann,
            "provenance": {
                "method": "synthetic_generation_v1",
                "review_status": "not_clinically_reviewed",
                "generator": "care-journey-extender/middle-zone",
            },
        })
        return self.records[-1]

    def save_jsonl(self, path):
        with open(path, "w") as f:
            for r in self.records:
                f.write(json.dumps(r) + "\n")
        return len(self.records)

    def save_json(self, path):
        json.dump(self.records, open(path, "w"), indent=2)
        return len(self.records)
