"""Bake a disease-circuit correlome into a web overlay asset (depression_map.glb).

Ports the disease-map overlay from rseeg's `do_map_overlay.py` /
`smooth_contour_actor_scalar` (rseeg.structure.shaders) into a static GLB the
Three.js viewer drapes over the glass brain when the "depression circuit"
toggle is on.

Pipeline (mirrors smooth_contour_actor_scalar):
  1. load the correlome NIfTI (continuous CBCT circuit map, can be signed)
  2. mask |value| > threshold  (do_map_overlay used show_dz_map=3)
  3. morphological close + Gaussian smooth the mask
  4. marching cubes -> isosurface, in voxel space
  5. affine -> MNI/RAS world coordinates
  6. co-register into brain.glb's normalized space (same orient + center + scale
     derived from the fsaverage surface, so the overlay lands inside the brain)

Run (deps are ephemeral, not added to the app runtime — same as
fetch_brain_mesh.py):
  uv run --with nibabel --with scipy --with scikit-image --with nilearn \
         --with trimesh python scripts/bake_dz_map.py

Defaults bake the Depression map; override with --map / --threshold / --out.
If the source NIfTI is missing the app simply skips the overlay.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

# Reuse the exact fsaverage fetch + orientation the brain asset was baked with,
# so the overlay shares brain.glb's coordinate frame.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_brain_mesh import fetch_fsaverage_mesh, orient_upright  # noqa: E402

DEFAULT_MAP = "/home/virati/Data/postdoc_25/cbct_circuit_maps/correlomes/Depression.nii"
DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "app" / "static" / "assets" / "depression_map.glb"
)
DEFAULT_THRESHOLD = 3.0  # do_map_overlay.py: render(..., show_dz_map=3)
MAX_FACES = 40_000

# smooth_contour_actor_scalar defaults
SIGMA = 2.0
CLOSING_ITERS = 2
ISO_LEVEL = 0.25


def brain_normalization() -> tuple[np.ndarray, float]:
    """(center, scale) that fetch_brain_mesh applied — so overlays co-register.

    normalize() there does: translate by -bounds.mean, scale by 2/extents.max,
    on the upright-oriented fsaverage mesh. We recompute those params here.
    """
    mesh = orient_upright(fetch_fsaverage_mesh())
    center = mesh.bounds.mean(axis=0)
    scale = 2.0 / mesh.extents.max()
    return center, scale


def correlome_isosurface(map_path: str, threshold: float) -> trimesh.Trimesh:
    import nibabel as nib
    from scipy.ndimage import binary_closing, gaussian_filter
    from skimage import measure

    img = nib.load(map_path)
    vol = np.asarray(img.dataobj, dtype=np.float32)
    affine = img.affine

    mask = np.abs(vol) > threshold
    if not mask.any():
        raise SystemExit(f"No voxels above |{threshold}| in {map_path}")
    print(f"  {int(mask.sum())} voxels above |{threshold}|")

    # close small gaps, then smooth the 0/1 field into a continuous one
    field = binary_closing(mask, iterations=CLOSING_ITERS).astype(np.float32)
    field = gaussian_filter(field, sigma=SIGMA)

    verts, faces, _, _ = measure.marching_cubes(field, level=ISO_LEVEL)

    # marching_cubes verts are in (i, j, k) voxel index space -> world via affine
    homog = np.c_[verts, np.ones(len(verts))]
    world = (affine @ homog.T).T[:, :3]

    mesh = trimesh.Trimesh(vertices=world, faces=faces, process=True)
    print(f"  isosurface: {len(mesh.faces)} faces, {len(mesh.vertices)} verts")
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", default=DEFAULT_MAP, help="source correlome NIfTI")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not Path(args.map).exists():
        raise SystemExit(f"Source map not found: {args.map}")

    print(f"→ deriving brain normalization frame …", flush=True)
    center, scale = brain_normalization()

    print(f"→ building isosurface from {args.map} …", flush=True)
    mesh = correlome_isosurface(args.map, args.threshold)
    mesh = orient_upright(mesh)  # RAS z-up -> Three.js y-up (same as brain)
    mesh = decimate(mesh)

    # co-register into brain.glb's normalized space
    mesh.apply_translation(-center)
    mesh.apply_scale(scale)
    mesh.fix_normals()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(args.out))
    print(
        f"✓ wrote {args.out} ({args.out.stat().st_size // 1024} KB, "
        f"{len(mesh.faces)} faces)"
    )


if __name__ == "__main__":
    main()
