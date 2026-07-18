"""Fetch a real anatomical brain surface from BrainGlobe / brainrender atlases
and bake it into a compact web asset (app/static/assets/brain.glb).

BrainGlobe (https://github.com/brainglobe/brainrender) is the mesh layer behind
brainrender; `brainglobe-atlasapi` downloads atlas data including per-structure
`.obj` meshes. We export the whole-brain "root" surface, normalize it, and write
a GLB the Three.js viewer loads and shades as a glass brain.

Run (deps are ephemeral, not added to the app runtime):
  uv run --with brainglobe-atlasapi --with trimesh python scripts/fetch_brain_mesh.py

If BrainGlobe's data server is unreachable, the app falls back to a procedural
glass brain automatically — this script only needs to succeed once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh
from brainglobe_atlasapi import BrainGlobeAtlas

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "assets" / "brain.glb"

# Preference order: a human brain reads best for a patient app; mouse atlases
# are smaller fallbacks if the human atlas is unavailable.
ATLAS_CANDIDATES = [
    "allen_human_500um",
    "allen_mouse_50um",
    "allen_mouse_100um",
    "example_mouse_100um",
]
MAX_FACES = 40_000  # decimate above this to keep the web asset light


def load_root_mesh() -> trimesh.Trimesh:
    last_err = None
    for name in ATLAS_CANDIDATES:
        try:
            print(f"→ trying atlas {name} …", flush=True)
            atlas = BrainGlobeAtlas(name)
            mf = atlas.meshfile_from_structure("root")
            mesh = trimesh.load(str(mf), process=True)
            print(f"  got root mesh: {len(mesh.faces)} faces, {len(mesh.vertices)} verts")
            return mesh
        except Exception as e:  # noqa: BLE001 — try the next atlas
            print(f"  failed: {e}")
            last_err = e
    raise SystemExit(f"Could not fetch any atlas mesh (server down?). Last error: {last_err}")


def normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    # center on the origin and scale so the largest dimension ~= 2 units
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    scale = 2.0 / mesh.extents.max()
    mesh.apply_scale(scale)
    return mesh


def decimate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if len(mesh.faces) <= MAX_FACES:
        return mesh
    try:
        m = mesh.simplify_quadric_decimation(MAX_FACES)
        print(f"  decimated to {len(m.faces)} faces")
        return m
    except Exception as e:  # noqa: BLE001 — optional; keep full mesh if unavailable
        print(f"  decimation unavailable ({e}); keeping full mesh")
        return mesh


def main() -> None:
    mesh = load_root_mesh()
    mesh = decimate(mesh)
    mesh = normalize(mesh)
    # smooth vertex normals for a nice glass look
    mesh.fix_normals()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(OUT))
    print(f"✓ wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
