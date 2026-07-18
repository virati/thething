# PLAN — MCP for Health ("The Patient Advocate") v1

Derived from [docs/SPECS.md](docs/SPECS.md). This plan scopes a **demoable v1**
that can grow toward the full vision. Checked items are done.

## Guiding scope decisions (v1)

- **Web app**, responsive so the same URL works on desktop and Android.
  (No native app — a mobile-friendly web app satisfies "computer and phone".)
- **Backend:** FastAPI (repo is already Python 3.12 / uv). Serves a JSON API
  + the static single-page frontend.
- **Frontend:** dependency-free HTML/CSS/vanilla JS SPA. No build step — keeps
  the hackathon prototype trivial to run and deploy.
- **Auth:** a *mock* Google-style authorization screen (no real OAuth in v1).
  It sets the tone (consent/authorization) without external dependencies.
  Real Google + Claude Connector OAuth is a roadmap item.
- **The "Advocate":** v1 ships a deterministic, rule-based **context packager**
  that compresses a patient's story into a clinician-ready brief. The seam for
  a real Claude/DSPy agent is isolated in one module (`advocate.py`).
- **Synthetic data:** ship a generator + a committed seed set. Target 20
  stories; hand-author a few rich ones and procedurally fill the rest.

## Architecture

```
browser (SPA)  ──HTTP/JSON──►  FastAPI app
   auth screen                   /api/patients            -> list
   two panes                     /api/patients/{id}       -> full story
                                 /api/patients/{id}/package -> advocate brief
                                 /            (static SPA)
                                        │
                                 synthetic data (JSON on disk)
                                        ▲
                                 generator script
```

Data model (per patient story):
- `demographics`, `conditions`
- `conversations[]` — type (phone|chat), transcript, extracted **affect** &
  signals (intent, outcome, engagement, needs, trust, sentiment)
- `imaging[]` — modality, region (heart|brain), findings, annotations
- `timeline[]` — longitudinal events (the "journey")

## Milestones

### M0 — Project scaffold  ✅
- [x] Reorganize `docs/SPECS.md`
- [x] Write this `PLAN.md`
- [x] Add deps to `pyproject.toml` (fastapi, uvicorn)

### M1 — Data layer
- [ ] `app/models.py` — dataclasses/pydantic for the story schema
- [ ] `app/data/` — synthetic stories as JSON
- [ ] `scripts/generate_stories.py` — build up to 20 synthetic stories
- [ ] Hand-author 2–3 rich "hero" stories (1 cardiac, 1 neuro)

### M2 — Backend API
- [ ] `app/server.py` — FastAPI app, endpoints above, serves static SPA
- [ ] `app/advocate.py` — context packager (with/without middle-zones views)

### M3 — Frontend SPA
- [ ] Mock Google authorization screen → home
- [ ] Patient picker
- [ ] **Conversations pane** — collapsible sources (phone→transcript/affect, chats)
- [ ] **Anatomy pane** — SVG heart/brain template + patient overlays
- [ ] **Context package** view: WITHOUT vs WITH middle zones (the pitch)
- [ ] Responsive layout (stacks on phone, side-by-side on desktop)

### M4 — Run & verify
- [ ] `README.md` run instructions
- [ ] Launch server, smoke-test endpoints + UI

## Explicitly deferred (roadmap, not v1)

Real OAuth/Claude Connector · live Claude/DSPy advocate · federated learning ·
homomorphic crypto · JEPA imaging models · EHR write-back · persistence/DB.

## How to run (target)

```
uv sync
uv run uvicorn app.server:app --reload
# open http://localhost:8000  (or http://<lan-ip>:8000 on phone)
```
