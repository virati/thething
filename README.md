# MCP for Health — The Patient Advocate

An **agentic advocate that carries the patient's story between visits** and
delivers the missing context to clinicians at the point of decision.

- Full concept: [`docs/SPECS.md`](docs/SPECS.md)
- Build plan / status: [`PLAN.md`](PLAN.md)

This repo contains a **demoable v1**: a responsive two-pane web app
(Conversations + Anatomy) over synthetic patient stories, plus an "Advocate"
that packages a clinician-ready brief contrasting the story **without** vs
**with** the between-visit ("middle zone") context.

---

## What's inside

```
app/
  server.py        FastAPI app: JSON API + serves the SPA
  advocate.py      The Advocate — rule-based context packager (LLM seam)
  data/            Generated synthetic patient stories (JSON)
  static/          Dependency-free SPA (index.html, app.js, styles.css)
scripts/
  generate_stories.py   Builds up to 20 synthetic stories
main.py            Convenience launcher (uvicorn)
```

## Prerequisites

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) (recommended). Plain `pip`/`venv` also works.

## Run it (with uv)

```bash
# 1. install dependencies
uv sync

# 2. generate the synthetic patient stories (writes app/data/*.json)
uv run python scripts/generate_stories.py

# 3. start the app
uv run python main.py
#    (equivalent: uv run uvicorn app.server:app --reload --host 0.0.0.0 --port 8000)
```

Then open **http://localhost:8000** and click **Sign in with Google** (mock).

### On your phone (Android)

The server binds to `0.0.0.0`, so from a phone on the same Wi-Fi open
`http://<your-computer-lan-ip>:8000`. Find your IP with `ip addr` (Linux) or
`ipconfig` (Windows). The layout stacks the two panes vertically on narrow
screens.

## Run it (without uv)

```bash
python -m venv .venv && source .venv/bin/activate
pip install "fastapi>=0.111" "uvicorn[standard]>=0.30"
python scripts/generate_stories.py
uvicorn app.server:app --reload --host 0.0.0.0 --port 8000
```

## Using the demo

1. **Sign in** on the mock Google authorization screen.
2. Pick a patient from the top selector (start with **Maria Alvarez** — cardiac,
   or **James Okafor** — neuro; these are the hand-authored "hero" stories).
3. **Conversations pane** — expand a phone call or chat to see the transcript
   plus extracted **affect**, sentiment, engagement, and unmet needs.
4. **Anatomy pane** — a heart or brain template with patient-specific imaging
   overlays and findings.
5. Click **"Package context →"** to open the Advocate brief. Toggle between
   **Without middle zones** (what the clinic sees today) and **With middle
   zones** (engagement score, unmet needs, between-visit highlights, and
   "ask the right questions sooner" prompts). That contrast is the pitch.

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/patients` | List all patients (from `index.json`) |
| GET | `/api/patients/{id}` | Full patient story |
| GET | `/api/patients/{id}/package` | Advocate context package (with/without views) |
| GET | `/` | The SPA |

Interactive API docs are auto-served at **http://localhost:8000/docs**.

## Regenerating / editing data

- Re-run `scripts/generate_stories.py` any time to rebuild `app/data/`.
- The two "hero" stories are hand-authored at the top of that script; edit them
  there. Filler stories are procedural (seeded, so output is stable).

## Where the real AI plugs in

`app/advocate.py::package_context` is the seam. v1 is deterministic so the demo
needs no API keys. To make it a real agent, replace that function with a
Claude / DSPy call that takes the same `story` dict and returns the same shape —
the API and UI don't change.

## Roadmap (deferred from v1)

Real Google OAuth + Claude Connector · live Claude/DSPy advocate · federated
learning · homomorphic crypto · JEPA imaging foundation models · EHR write-back ·
persistent storage. See [`docs/SPECS.md`](docs/SPECS.md) §7.
