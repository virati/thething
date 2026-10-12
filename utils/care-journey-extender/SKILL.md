---
name: care-journey-extender
description: Extend a synthetic ambient-clinical FHIR dataset (a zip like synthetic-ambient-fhir-*.zip containing JSONL records with transcript + note + AVS + FHIR encounter per patient) into multi-visit longitudinal patient journeys. Use whenever the user uploads an ambient/FHIR encounter dataset and asks to add follow-up visits, extend patient timelines, create patient journeys or clinical trajectories, generate synthetic longitudinal data, or visualize care journeys. Also use for requests like "make another visit 6 months later" or "give each patient a 2-year story."
---

# Care Journey Extender

Takes a synthetic ambient-clinical dataset (one encounter per patient: transcript, clinical note, after-visit summary, FHIR resources) and generates clinically coherent follow-up visits that turn each single encounter into a multi-visit longitudinal journey.

## Workflow

### 1. Explore the input

Unzip to a working directory and load the `.jsonl`. For each record, extract what drives the journey design:

```bash
python3 scripts/explore.py <extracted_dir>/<name>.jsonl
```

This prints, per patient: index, patient_id, visit date, age at visit, gender, visit title, condition labels, and medication labels. Confirm the patient↔encounter cardinality (usually 1:1) and report it to the user.

### 2. Plan the journeys (the clinical reasoning step)

This step is judgment, not code. For each patient, design a visit sequence over the requested horizon (default 24 months) driven by their **actual diagnoses, age, and index visit type**. Principles:

- **Vary utilization realistically.** Healthy young adults get 1–3 visits; complex geriatric or multi-morbid patients get 4–5 including acute events. Aim for a spread, not uniform cadence.
- **Follow the natural history of the anchor condition.** Pregnancy → third trimester → delivery → postpartum → well-woman. Knee OA → conservative failure → injection → arthroplasty → recovery. Post-MI elderly → surveillance → recurrent event → heart failure → stabilization. Hospice → recertification → death.
- **Let outcomes differ.** Some patients improve and taper medications; some acquire new chronic diagnoses; some are hospitalized; hospice patients die. Do not give every patient a happy or stable arc — realism requires deterioration, complications, and death where the trajectory implies it. Handle death visits with the tone of real hospice documentation: factual, warm, family-facing.
- **Carry threads forward.** Psychosocial findings (isolation, IPV, housing), prediabetes, and medication lists from the index record should reappear and evolve — resolved, worsened, or newly relevant — in later visits.

Save the plan as `master_plan.json`: a list of `{patient_index, archetype, v1_date, visits:[{months_after_v1, date, label}]}`. Compute dates from the index visit date (calendar-month arithmetic; fractional months = extra days). Show the user the plan summary before generating full content, since it's the cheapest point for course correction.

### 3. Generate full-detail encounters

For each planned visit, author four artifacts that must agree with each other and with the patient's history:

1. **Transcript** — DR/PT/NURSE/FAMILY ambient dialogue, ~250–450 words. Natural speech, continuity references to prior visits ("last time we started..."), vitals spoken by NURSE, clinical decisions explained aloud.
2. **Clinical note** — SOAP format (Subjective/Objective/Assessment/Plan) consistent with the transcript's facts, numbers, and decisions.
3. **After-visit summary** — patient-facing, plain language, "What we discussed" + "Your plan" bullets, derived only from the note's A&P. For a death visit, address the family instead.
4. **Structured resources** — condensed Condition/Observation/MedicationRequest/Procedure entries reflecting what changed at that visit.

Use `scripts/record_builder.py` — it provides `mk(...)` which assembles records matching the source schema (metadata with `source: "synthetic-journey-extension"`, encounter_id `<patient_id>-v<N>`, AVS provenance block flagged `not_clinically_reviewed`). Write authored content as calls to `mk()` in a generation script; run it after each patient is added so errors surface early.

**Consistency rules that matter most:** vitals/labs must trend plausibly across visits (a BP treated at visit 2 should be lower at visit 3 unless the story says otherwise); medications started earlier must be referenced later; ages must advance; provider and organization names carry over from the index record.

**Batching:** ~20 full-detail encounters is a realistic single-pass budget. For 25 patients, generate a diverse first batch spanning the archetype range (routine, obstetric, surgical, high-acuity, end-of-life), deliver it, and continue remaining patients on request.

### 4. Package and visualize

- Write records to `/mnt/user-data/outputs/care-journeys-batch<N>.jsonl` (one JSON per line) and copy `master_plan.json` alongside.
- Build the timeline visualization with `scripts/build_timeline.py <viz_data.json> <out.html>` — a standalone HTML with one row per patient, index-visit diamond at t=0, follow-up circles colored by category (routine / acute / hospitalization / procedure / obstetric / end-of-life), and hover tooltips carrying one-line clinical highlights for fully generated patients. Categories are inferred from visit labels by `categorize()` in the script; review its output and correct miscategorized labels.
- Present the files and summarize the archetype spread in a short table.

## Output record schema

Match the source dataset's shape so extended records can be concatenated with the originals. Required top-level keys: `id`, `metadata`, `encounter_fhir` (with `encounter` + `related_resources`), `transcript`, `note`, `after_visit_summary`, `after_visit_summary_provenance`. See `references/record_schema.md` for the full field list and an example.

## Cautions

- Everything generated is synthetic; keep `"synthetic": true` in metadata and never blend in real patient data if the user has any nearby.
- The AVS is deterministically derived from the note's A&P by design — don't add content to the AVS that isn't in the note.
- When the dataset includes sensitive trajectories (IPV, hospice, NICU), write them with clinical seriousness, not drama.
