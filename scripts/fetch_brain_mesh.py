"""Bake a *proper* anatomical brain surface into a web asset (brain.glb).

Primary source is FreeSurfer's **fsaverage** cortical surface — the same mesh
PySurfer renders in its "transparent brain" example
(https://pysurfer.github.io/auto_examples/plot_transparent_brain.html).
We fetch it via nilearn (no FreeSurfer / Mayavi install needed), stitch the two
hemispheres, orient it upright, normalize/decimate, and export a GLB that the
Three.js viewer loads and shades as a glass brain.

Run (deps are ephemeral, not added to the app runtime):
  uv run --with nilearn --with nibabel --with trimesh python scripts/fetch_brain_mesh.py

If the surface can't be fetched, the app falls back to a procedural glass brain.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "assets" / "brain.glb"
MAX_FACES = 60_000  # decimate above this to keep the asset light

# fsaverage meshes, in decreasing detail. fsaverage6 ~ 80k verts/hemi (nice
# folds); fsaverage5 ~ 10k (lighter). Full "fsaverage" is ~160k/hemi.
FSAVERAGE_VARIANTS = ["fsaverage6", "fsaverage5"]
SURFACE = "pial"  # folded cortical surface = "proper" brain (vs. "infl")


def fetch_fsaverage_mesh() -> trimesh.Trimesh:
    from nilearn import datasets, surface

    last_err = None
    for variant in FSAVERAGE_VARIANTS:
        try:
            print(f"→ fetching {variant} ({SURFACE}) …", flush=True)
            fs = datasets.fetch_surf_fsaverage(variant)
            cl, fl = surface.load_surf_mesh(fs[f"{SURFACE}_left"])
            cr, fr = surface.load_surf_mesh(fs[f"{SURFACE}_right"])
            # stitch hemispheres (offset right-hemi face indices)
            verts = np.vstack([cl, cr])
            faces = np.vstack([fl, fr + len(cl)])
            mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
            print(f"  loaded: {len(mesh.faces)} faces, {len(mesh.vertices)} verts")
            return mesh
        except Exception as e:  # noqa: BLE001 — try a lighter variant
            print(f"  failed: {e}")
            last_err = e
    raise SystemExit(f"Could not fetch fsaverage surface. Last error: {last_err}")


def orient_upright(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    # FreeSurfer RAS: x=R, y=A, z=S(up). Three.js is y-up, so rotate z->y.
    R = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    mesh.apply_transform(R)
    return mesh


def normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    mesh.apply_scale(2.0 / mesh.extents.max())
    return mesh


def decimate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if len(mesh.faces) <= MAX_FACES:
        return mesh
    try:
        import fast_simplification

        reduction = max(0.0, min(0.95, 1 - MAX_FACES / len(mesh.faces)))
        v, f = fast_simplification.simplify(
            np.asarray(mesh.vertices, dtype=np.float32),
            np.asarray(mesh.faces, dtype=np.int32),
            reduction,
        )
        m = trimesh.Trimesh(vertices=v, faces=f, process=True)
        print(f"  decimated to {len(m.faces)} faces")
        return m
    except Exception as e:  # noqa: BLE001 — optional; keep full mesh if unavailable
        print(f"  decimation unavailable ({e}); keeping full mesh")
        return mesh


def main() -> None:
    mesh = fetch_fsaverage_mesh()
    mesh = orient_upright(mesh)
    mesh = decimate(mesh)
    mesh = normalize(mesh)
    mesh.fix_normals()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(OUT))
    print(f"✓ wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(mesh.faces)} faces)")


if __name__ == "__main__":
    main()
