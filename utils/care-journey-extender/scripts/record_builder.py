#!/usr/bin/env python3
"""Assemble journey-extension records matching the ambient-FHIR source schema.

Import into a generation script:

    from record_builder import JourneyBatch
    batch = JourneyBatch()
    batch.mk(patient_idx=0, pid="<patient_id>", visit_num=2,
             date_str="2023-02-05T09:10:00-08:00",
             title="Migraine follow-up",
             code_display="Follow-up encounter (procedure)",
             provider="WHITLEY WELLNESS LLC", clinician="Dr. ...",
             transcript="DR: ...", note="Subjective: ...", avs="Visit summary ...",
             conditions=[...], observations=[...], medications=[...], procedures=[...],
             months_after=6)
    batch.save_jsonl("/mnt/user-data/outputs/care-journeys-batch1.jsonl")
"""
import json


class JourneyBatch:
    def __init__(self):
        self.records = []

    def mk(self, patient_idx, pid, visit_num, date_str, title, code_display,
           provider, clinician, transcript, note, avs,
           conditions=None, observations=None, medications=None, procedures=None,
           months_after=None):
        eid = f"{pid}-v{visit_num}"
        self.records.append({
            "id": f"{pid}::{eid}",
            "metadata": {
                "source": "synthetic-journey-extension",
                "synthetic": True,
                "patient_id": pid,
                "encounter_id": eid,
                "encounter_reference": f"urn:uuid:{eid}",
                "date": date_str,
                "status": "finished",
                "visit_type": code_display,
                "document_status": "current",
                "visit_title": title,
                "visit_number": visit_num,
                "months_after_index_visit": months_after,
            },
            "encounter_fhir": {
                "encounter": {
                    "resourceType": "Encounter",
                    "id": eid,
                    "status": "finished",
                    "serviceProvider": {"display": provider},
                    "participant": [{"individual": {"display": clinician}}],
                    "period": {"start": date_str},
                },
                "related_resources": {
                    "Condition": conditions or [],
                    "Observation": observations or [],
                    "MedicationRequest": medications or [],
                    "Procedure": procedures or [],
                },
            },
            "transcript": transcript.strip(),
            "note": note.strip(),
            "after_visit_summary": avs.strip(),
            "after_visit_summary_provenance": {
                "method": "deterministic_extractive_v1",
                "review_status": "not_clinically_reviewed",
                "source": "clinical_note_assessment_and_plan",
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
