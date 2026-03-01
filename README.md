# nanojellprint

Generate a print-ready `.3mf` file for a 5-color Bambu Lab print of a
curcumin–chitosan–alginate nanoparticle drug delivery system — and optionally
read your AMS filament slots directly from the printer to pre-configure everything.

Built for ISEF 2026.

---

## What it prints

A 30 mm cutaway sphere visualizing a **pH-responsive nanoparticle** designed for
colorectal cancer drug delivery. The model exposes all three concentric layers
through an organic spherical boolean cut.

| # | Body | Color | Science |
|---|------|-------|---------|
| 1 | Curcumin core | Yellow | Hydrophobic drug payload trapped in the chitosan gel network |
| 2 | Chitosan shell | White | Cationic polymer mesh (protonated NH₃⁺ at acidic pH) |
| 3 | NH₃⁺ charge groups | Red | ~60 hemispherical bumps on the chitosan surface, visible in the cutaway |
| 4 | Alginate shell | Blue | Anionic outer coat (COO⁻ carboxylate groups), held by electrostatic attraction |
| 5 | COO⁻ charge groups | Green | ~60 hemispherical bumps on the alginate outer surface |

The electrostatic interaction between chitosan (+) and alginate (−) holds the
layered structure together. The model is pH-responsive: the alginate shell
protects the payload in stomach acid (pH ~1.2) and releases it in the colon
(pH ~7.4) as the interactions weaken.

---

## How to run

### 1. Install dependencies

```bash
pip install manifold3d trimesh numpy bambulabs-api python-dotenv
```

### 2. Configure printer (optional)

```bash
cp .env.example .env
# Edit .env with your Bambu printer's IP, access code, and serial number
# Find these in Bambu Studio → Device → your printer → ⋯ → Developer Mode
```

### 3. Run

**With printer** — reads your AMS slots and lets you assign each to a body:
```bash
python main.py
```

**Without printer** — uses default colors (yellow/white/red/blue/green):
```bash
python main.py --no-printer
```

**Skip re-rendering** — repackage from existing STLs (fast):
```bash
python main.py --no-printer --stl-dir stl_output
```

Output: `nanoparticle.3mf` — open in Bambu Studio and print.

---

## Project structure

```
nanojellprint/
├── printer.py      # Connect to Bambu printer, read AMS filament slots
├── model_gen.py    # Generate 5 watertight STL bodies via manifold3d CSG
├── make_3mf.py     # Package STLs + filament config into a Bambu-compatible .3mf
├── main.py         # CLI orchestrator
├── pyproject.toml
└── .env.example
```

---

## The story of how we got here

### The model spec

The starting point was a detailed spec (`Nanoparticle_3D_Model_Spec.md`) describing
exactly what the model should look like: a 30 mm sphere with an organic cutaway,
concentric shells at precise radii, and two sets of ~60 hemispherical charge-group
bumps distributed evenly across two surfaces. Previous attempts in other tools had
produced meshes with 750+ non-manifold edges from overlapping geometry.

### Choosing the toolchain

The original plan was to use **OpenSCAD** for CSG boolean operations (as the spec
recommended), driven by a Python-generated `.scad` file. OpenSCAD wasn't installed,
and installing it required sudo access that wasn't available in the terminal session.

Instead we switched to **manifold3d** — a pure Python CSG library that does the
same clean boolean math (difference, union, intersection) without any external binary.
`trimesh` handles STL export with proper vertex sharing.

### The non-manifold saga

Getting the mesh clean took three rounds:

1. **First attempt:** Hand-rolled binary STL writer — created one unique vertex per
   triangle corner instead of sharing vertices between adjacent faces. Bambu Studio
   reported 9,684 non-manifold edges on a 3,228-triangle mesh (i.e. 3× — every single
   vertex was unshared). Switched `_to_stl` to use trimesh, which merges duplicate
   vertices automatically. Verified watertight with `trimesh.is_watertight`.

2. **Second attempt:** trimesh was writing correct STLs, but `make_3mf.py` was reading
   them back with the old hand-rolled `_read_stl_binary` function — which re-created the
   same triangle soup problem. Bambu Studio now saw 110,742 non-manifold edges across
   all 5 bodies combined (36,914 triangles × 3 = the whole mesh). Replaced the reader
   with trimesh as well.

3. **Correct result:** All 5 bodies `is_watertight = True`. File size dropped from
   745 KB to 391 KB (proof of shared vertices).

### The filament assignment fix

Bambu Studio wasn't showing per-component filament color pickers. The
`model_settings.config` was nesting all 5 parts as `<part>` children of the parent
object (id=6) rather than giving each body its own `<object>` entry. Fixed to emit:

```xml
<object id="1"><metadata key="extruder" value="1"/></object>
<object id="2"><metadata key="extruder" value="2"/></object>
...
```

### Bump geometry

The NH₃⁺ bump body was producing 0 triangles. Two bugs:

- The Fibonacci sphere function was adding the `seed` offset into the z-distribution,
  pushing some `arccos` inputs outside `[-1, 1]`. Fixed by applying seed only to the
  angular phase (`theta`), not the polar angle (`phi`).
- The bump caps were being unioned individually and clipped one at a time, which was
  numerically unstable. Fixed by unioning all 60 bump spheres first, then subtracting
  the inner surface sphere in one operation.

A third bug in `_body_nh3_bumps` was subtracting `_sphere(14.5)` — a sphere *larger*
than the bumps themselves (which only reach r = 13.8 mm), erasing them entirely.
Removed the incorrect clip; the bumps are intentionally inside the alginate shell and
are only meant to be visible in the cutaway.

---

## Roadmap

- [ ] Connect printer AMS read → auto-assign filaments by color match
- [ ] MCP server wrapping the full pipeline (`generate_model`, `read_ams`, `send_to_printer`)
- [ ] Verify filament assignment survives a Bambu Studio round-trip
- [ ] Add `--send` flag to upload `.3mf` to printer via FTP + MQTT trigger
