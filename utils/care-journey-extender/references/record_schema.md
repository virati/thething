# Extended record schema

Extended records mirror the source dataset's shape so both can be concatenated into one JSONL. `record_builder.py` produces this automatically.

## Top-level keys

| Key | Content |
|---|---|
| `id` | `<patient_id>::<encounter_id>` |
| `metadata` | Provenance + visit descriptors (see below) |
| `encounter_fhir` | `encounter` (condensed Encounter resource) + `related_resources` |
| `transcript` | Ambient DR/PT/NURSE/FAMILY dialogue, plain text |
| `note` | SOAP-format clinical note |
| `after_visit_summary` | Patient-facing summary derived from the note's A&P |
| `after_visit_summary_provenance` | `method`, `review_status: not_clinically_reviewed`, `source` |

## metadata fields

```json
{
  "source": "synthetic-journey-extension",
  "synthetic": true,
  "patient_id": "<uuid from source dataset>",
  "encounter_id": "<patient_id>-v<N>",
  "encounter_reference": "urn:uuid:<encounter_id>",
  "date": "2023-02-05T09:10:00-08:00",
  "status": "finished",
  "visit_type": "Follow-up encounter (procedure)",
  "document_status": "current",
  "visit_title": "Migraine and stress follow-up",
  "visit_number": 2,
  "months_after_index_visit": 6
}
```

`visit_number` starts at 2 (the source record is visit 1). Keep `patient_id`, provider organization, and clinician names identical to the source record so journeys join cleanly on patient_id.

## related_resources entries

Condensed rather than full FHIR R4 — each entry needs at minimum a `code` string; add `clinicalStatus`, `value`, or `status` where they carry the visit's clinical change:

```json
"Condition":         [{"code": "Essential hypertension (disorder)", "clinicalStatus": "chronic, controlled"}],
"Observation":       [{"code": "Blood pressure", "value": "128/80 mmHg"}],
"MedicationRequest": [{"code": "furosemide 20 MG Oral Tablet", "status": "new"}],
"Procedure":         [{"code": "Total knee arthroplasty, right"}]
```

If the user needs fully valid FHIR R4 resources instead of condensed ones, say so and expand these into complete resource objects with `resourceType`, `subject` references, and coding systems — but the condensed form is the default because it keeps generated records readable and diff-able.

## Differences from source records

Source records also contain `patient_context` (patient demographics + longitudinal summary). Extended records omit it to avoid duplicating chart state that drifts as the journey progresses; consumers should join on `patient_id` back to the source record for demographics.
