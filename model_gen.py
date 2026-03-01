"""
Generate the 5-body nanoparticle STL files using manifold3d (pure Python CSG).
No OpenSCAD required.

Bodies (filament order 1–5):
  1. Curcumin core     — Yellow
  2. Chitosan shell    — White
  3. NH3+ bumps        — Red
  4. Alginate shell    — Blue
  5. COO- bumps        — Green
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from manifold3d import Manifold

# ── Geometry constants (from spec) ────────────────────────────────────────────

CORE_R        = 9.8
CHITOSAN_IN   = 10.0
CHITOSAN_OUT  = 13.0
GAP           = 0.2
ALGINATE_IN   = CHITOSAN_OUT + GAP   # 13.2
ALGINATE_OUT  = 15.0
BUMP_R        = 0.8
NUM_BUMPS     = 60

CUT_R      = 22.0
CUT_CENTER = np.array([12.0, 12.0, 12.0])

# Sphere resolution — circular segments
FN_SPHERE = 96
FN_BUMP   = 24

BODY_NAMES = {
    1: "curcumin_core",
    2: "chitosan_shell",
    3: "nh3_bumps",
    4: "alginate_shell",
    5: "coo_bumps",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sphere(radius: float, fn: int = FN_SPHERE) -> Manifold:
    return Manifold.sphere(radius, circular_segments=fn)


def _cut() -> Manifold:
    cx, cy, cz = CUT_CENTER
    return (
        _sphere(CUT_R)
        .translate([cx, cy, cz])
    )


def _fibonacci_pts(n: int, seed: int = 0) -> np.ndarray:
    """Return n evenly distributed unit vectors on a sphere (Fibonacci lattice)."""
    golden = np.pi * (3 - np.sqrt(5))
    i = np.arange(n)
    # seed offsets the angular phase only, not the z-distribution, to avoid arccos domain errors
    phi   = np.arccos(np.clip(1 - 2 * (i + 0.5) / n, -1.0, 1.0))
    theta = golden * (i + seed)
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.stack([x, y, z], axis=1)


def _bumps(surface_r: float, seed: int, fn: int = FN_BUMP) -> Manifold:
    """Union of NUM_BUMPS hemispherical caps protruding outward from surface_r."""
    pts = _fibonacci_pts(NUM_BUMPS, seed=seed)
    # Union all bump spheres first, then subtract the interior — more numerically stable
    result = _sphere(BUMP_R, fn).translate((pts[0] * surface_r).tolist())
    for pt in pts[1:]:
        center = pt * surface_r
        result = result + _sphere(BUMP_R, fn).translate(center.tolist())
    # Keep only the caps that protrude outside the surface
    result = result - _sphere(surface_r - 0.01)
    return result


# ── Body builders ─────────────────────────────────────────────────────────────

def _body_core() -> Manifold:
    return _sphere(CORE_R) - _cut()


def _body_chitosan() -> Manifold:
    shell = _sphere(CHITOSAN_OUT) - _sphere(CHITOSAN_IN)
    return shell - _cut()


def _body_nh3_bumps() -> Manifold:
    # Hemispherical caps on the chitosan outer surface.
    # They protrude from r=13.0 to r=13.8mm — overlapping with alginate is fine
    # because each body prints in its own filament; bumps are visible in the cutaway.
    bumps = _bumps(CHITOSAN_OUT, seed=0)
    return bumps - _cut()


def _body_alginate() -> Manifold:
    shell = _sphere(ALGINATE_OUT) - _sphere(ALGINATE_IN)
    return shell - _cut()


def _body_coo_bumps() -> Manifold:
    bumps = _bumps(ALGINATE_OUT, seed=17)
    bumps = bumps - _sphere(ALGINATE_OUT - 0.01)
    return bumps - _cut()


BUILDERS = {
    1: _body_core,
    2: _body_chitosan,
    3: _body_nh3_bumps,
    4: _body_alginate,
    5: _body_coo_bumps,
}


# ── STL export ────────────────────────────────────────────────────────────────

def _to_stl(m: Manifold, path: Path) -> None:
    """Export a Manifold to STL via trimesh (handles vertex merging and normals)."""
    import trimesh

    raw = m.to_mesh()
    verts = np.array(raw.vert_properties)[:, :3]  # xyz only, drop any extra properties
    tris  = np.array(raw.tri_verts)

    tm = trimesh.Trimesh(vertices=verts, faces=tris, process=True)
    tm.export(str(path))


def generate_stls(
    out_dir: Path,
    openscad_bin: str = "openscad",  # ignored — kept for API compat
) -> dict[int, Path]:
    """
    Build each of the 5 bodies and write STL files to out_dir.
    Returns {body_number: stl_path}.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    for body_num, name in BODY_NAMES.items():
        print(f"  Building body {body_num} ({name})...", end=" ", flush=True)
        mesh = BUILDERS[body_num]()
        stl_path = out_dir / f"{name}.stl"
        _to_stl(mesh, stl_path)
        n_tri = len(mesh.to_mesh().tri_verts)
        print(f"{n_tri:,} triangles  →  {stl_path.name}")
        results[name] = stl_path
    return results


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("stl_output")
    print(f"Generating STLs in {out}/")
    stls = generate_stls(out)
    total = sum(p.stat().st_size for p in stls.values())
    print(f"Done. Total STL size: {total // 1024:,} KB")
