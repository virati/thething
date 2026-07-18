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
  static/          SPA (index.html, app.js, styles.css)
    anatomy3d.js   3D heart/brain renderer (marker overlays, orbit controls)
    assets/        Baked mesh assets (brain.glb, optional — see below)
    vendor/        Three.js r128 + OrbitControls + GLTFLoader, vendored (offline)
scripts/
  generate_stories.py   Builds up to 20 synthetic stories
  fetch_brain_mesh.py   Bakes a real BrainGlobe/brainrender brain mesh -> brain.glb
  bake_dz_map.py        Bakes a CBCT correlome isosurface -> depression_map.glb
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
3. **Main screen = the glass brain.** An interactive **3D** organ fills the
   stage (drag to rotate, auto-spins) with patient-specific marker overlays.
   **Brain is the default**, a translucent **"glass brain"** with edge glow so
   the imaging markers appear suspended inside it; the floating **organ dropdown**
   (🧠 Brain / ❤ Heart) switches models.
4. **Collapsible side panel** (arrow tab on its left edge — click to collapse/
   expand) holds the patient's between-visit context:
   - **Conversations** — expand a phone call or chat to see the transcript plus
     extracted **affect**, sentiment, engagement, and unmet needs.
   - **Portal Interactions** — secure messages, refill requests, released
     results, scheduling, forms, and billing, each with type, direction, and
     status (e.g. a diuretic refill left *pending* over a copay).
   - **Imaging / Findings** — the studies behind the anatomy view.
5. **Patient record dropdown** (blue, top bar) — lists every real patient folder
   under `data/patients/`. Selecting one opens a **Patient Record** section in the
   side panel with **all** their information: demographics, problem list,
   medications, longitudinal resource counts, and every encounter's clinical
   **note**, **transcript**, and **after-visit summary**. It also drops
   **regions-of-concern dots** on the glass brain (colored by severity) based on
   that patient's clinical presentation — defined in the side file
   `data/regions_of_concern.json`.
6. Click **"Package context →"** to open the Advocate brief. Toggle between
   **Without middle zones** (what the clinic sees today) and **With middle
   zones** (engagement score, unmet needs, between-visit highlights, and
   "ask the right questions sooner" prompts). That contrast is the pitch.

## Real patient records (`data/patients/`)

Drop a patient folder under `data/patients/<name>/` containing a
`*_full_trajectory.json` (a list of encounters, each with `metadata`,
`patient_context`, `transcript`, `note`, `after_visit_summary` — the Synthea/FHIR
shape used by `data/patients/howell/`). It appears automatically in the **Patient
record** dropdown; no code changes needed.

Brain **regions of concern** live in the side file `data/regions_of_concern.json`,
keyed by folder name — each dot has a `label`, `reason`, `severity`
(`high`/`moderate`/`low`), and `x`/`y`/`z` in normalized brain-model space. Edit
that file to change the dots.

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/patients` | List synthetic demo stories (from `index.json`) |
| GET | `/api/patients/{id}` | Full synthetic story |
| GET | `/api/patients/{id}/package` | Advocate context package (with/without views) |
| GET | `/api/records` | List real patient folders under `data/patients/` |
| GET | `/api/records/{folder}` | Full record (demographics, summary, encounters) |
| GET | `/api/records/{folder}/regions` | Brain regions of concern for that patient |
| GET | `/` | The SPA |

Interactive API docs are auto-served at **http://localhost:8000/docs**.

## Real anatomical brain (FreeSurfer fsaverage / PySurfer) — optional

By default the brain is a **procedural glass brain** (no download needed). To use
a real cortical surface — FreeSurfer's **fsaverage** pial mesh, the same surface
[PySurfer](https://pysurfer.github.io/auto_examples/plot_transparent_brain.html)
renders in its transparent-brain example — bake it into a web asset once:

```bash
uv run --with nilearn --with nibabel --with trimesh python scripts/fetch_brain_mesh.py
```

This fetches fsaverage via `nilearn` (no FreeSurfer/Mayavi needed), stitches the
two hemispheres, orients it upright, normalizes/decimates, and writes
`app/static/assets/brain.glb`. The viewer loads it automatically and shades it
with the same glass material; if the file is absent (or the surface can't be
fetched), it silently falls back to the procedural brain. The dependencies are
ephemeral (`--with`) and are **not** added to the app's runtime.

### Depression-circuit overlay (CBCT correlome) — optional

The **"depression circuit"** toggle on the brain drapes a translucent isosurface
of a CBCT circuit map (correlome) over the glass brain — ported from rseeg's
`do_map_overlay.py` / `smooth_contour_actor_scalar`. Bake it into an overlay
asset once:

```bash
uv run --with nibabel --with scipy --with scikit-image --with nilearn \
       --with trimesh --with fast-simplification python scripts/bake_dz_map.py
```

This masks the correlome (`|value| > 3`, matching `show_dz_map=3`), smooths it,
runs marching cubes to an isosurface, applies the NIfTI affine to MNI/RAS space,
and **co-registers it into `brain.glb`'s normalized frame** (same fsaverage
orient/center/scale), writing `app/static/assets/depression_map.glb`. Point at a
different map with `--map`/`--threshold`/`--out`. If the asset is absent the app
simply skips the overlay. Dependencies are ephemeral and not in the app runtime.

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
