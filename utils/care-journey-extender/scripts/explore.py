#!/usr/bin/env python3
"""Print a per-patient clinical summary of an ambient-FHIR JSONL dataset.

Usage: python3 explore.py <path/to/dataset.jsonl>
"""
import json, sys
from datetime import date

def age_at(birth, when):
    try:
        b = date.fromisoformat(birth)
        w = date.fromisoformat(when[:10])
        return w.year - b.year - ((w.month, w.day) < (b.month, b.day))
    except Exception:
        return "?"

def main(path):
    recs = [json.loads(l) for l in open(path)]
    pids = [r["metadata"]["patient_id"] for r in recs]
    print(f"{len(recs)} records | {len(set(pids))} unique patients | "
          f"{len(set(r['metadata']['encounter_id'] for r in recs))} unique encounters\n")
    for i, r in enumerate(recs):
        m = r["metadata"]
        pt = r.get("patient_context", {}).get("patient", {})
        ls = r.get("patient_context", {}).get("longitudinal_summary", {})
        name = pt.get("name", [{}])[0]
        full = " ".join(name.get("given", [])) + " " + name.get("family", "")
        print(f"[{i}] {m['patient_id'][:8]} {full.strip()} | "
              f"{age_at(pt.get('birthDate',''), m['date'])}{(pt.get('gender') or '?')[0].upper()} | "
              f"{m['date'][:10]} | {m.get('visit_title', m.get('visit_type',''))}")
        if ls.get("condition_labels"):
            print(f"     conditions: {ls['condition_labels']}")
        if ls.get("medication_labels"):
            print(f"     meds: {ls['medication_labels']}")

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except BrokenPipeError:
        pass
