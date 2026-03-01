# 3D Print Model Spec: Curcumin–Chitosan–Alginate Nanoparticle Cutaway

## Purpose

A single 3D-printable display model (30 mm diameter) showing a **layered nanoparticle drug delivery system** for colorectal cancer research. This is a conceptual macroscopic visualization of nanoscale architecture, intended for use at ISEF 2026 and related scientific presentations.

The model uses an **organic spherical cutaway** (not a flat plane) to expose the internal layered structure while keeping the exterior intact on the remaining surface.

---

## What the Model Represents

From inside out:

| Layer | Material | Role | Charge |
|-------|----------|------|--------|
| Core | Curcumin | Hydrophobic drug payload | Neutral |
| Shell 1 | Chitosan | Cationic polymer mesh holding drug | Positive (NH₃⁺ protonated amines) |
| Shell 2 | Alginate | Anionic protective outer shell | Negative (COO⁻ carboxylate groups) |

The electrostatic interaction between chitosan (+) and alginate (−) is what holds the layered structure together. The model must visually communicate this.

---

## Single Model — Organic Cutaway Sphere

One model. Remove approximately ¼ of the sphere using a **spherical boolean subtraction** (organic curved cut, not a flat slice). The cut exposes all three concentric layers.

### What the viewer should see

- **From the outside (intact portion):** Blue alginate shell with small green COO⁻ bumps dotting the surface.
- **From the cutaway (exposed cross-section):** Yellow curcumin core → white chitosan shell → small red NH₃⁺ bumps on the chitosan surface → blue alginate shell. The layering tells the electrostatic encapsulation story at a glance.

---

## Dimensions

| Element | Specification |
|---------|--------------|
| Total diameter | 30 mm |
| Curcumin core radius | 9.8 mm |
| Chitosan shell | 10.0 mm inner → 13.0 mm outer (3 mm thick) |
| Gap between chitosan and alginate | 0.2 mm (for visual separation in cutaway) |
| Alginate shell | 13.2 mm inner → 15.0 mm outer (1.8 mm thick) |
| NH₃⁺ bumps | 0.8 mm radius hemispheres, ~60 count, on chitosan outer surface (r = 13.0 mm) |
| COO⁻ bumps | 0.8 mm radius hemispheres, ~60 count, on alginate outer surface (r = 15.0 mm) |

### Bump Distribution

Use a **Fibonacci sphere** algorithm to evenly distribute bump positions on each surface. Use different seed offsets for the NH₃⁺ and COO⁻ distributions so they don't align radially.

### Bump Construction

Each bump is a full sphere placed at the target surface radius, then **intersected** with the region just outside that surface to create a hemispherical cap protruding outward. This avoids any geometry penetrating inward into the shell below.

- NH₃⁺ bumps: Keep only the portion of each sphere between r = 13.0 mm and r = 13.0 + bump_r + 0.5 mm
- COO⁻ bumps: Keep only the portion of each sphere between r = 15.0 mm and r = 15.0 + bump_r + 0.5 mm

### Organic Cut

Spherical boolean subtraction:

- Cut sphere radius: 22 mm
- Cut sphere center: (12, 12, 12) mm from model center

This removes roughly one quarter of the sphere with a smooth curved surface, preserving structural integrity and wall thickness > 1 mm everywhere.

---

## Bodies (5 Separate Printable Parts)

The model consists of **5 separate solid bodies** so that a multi-color slicer can assign a different filament to each:

| # | Body | Description | Print Color |
|---|------|-------------|-------------|
| 1 | Curcumin core | Solid sphere, r = 9.8 mm, with cut | Yellow |
| 2 | Chitosan shell | Hollow shell, 10.0–13.0 mm, with cut | White |
| 3 | NH₃⁺ bumps | ~60 hemispherical caps on chitosan surface, with cut | Red |
| 4 | Alginate shell | Hollow shell, 13.2–15.0 mm, with cut | Blue |
| 5 | COO⁻ bumps | ~60 hemispherical caps on alginate surface, with cut | Green |

Each body must be a **true solid** — no overlapping geometry between bodies. Shells are constructed by boolean difference (outer sphere minus inner sphere), not by overlapping concentric solids.

---

## File Format & Slicer Compatibility

### Target: Bambu Lab H2D with AMS (5 filaments)

Output a single **.3mf file** with the following structure:

- 5 child objects (one per body above), each containing its mesh
- 1 parent object referencing all 5 as **components**
- The **build** element references only the parent object

This component structure is required for Bambu Studio to show a single grouped object where each component has its own filament color picker. Without this parent-child relationship, Bambu Studio treats the parts as independent objects and does not allow per-part filament assignment within the group.

```xml
<!-- Simplified structure -->
<object id="1" name="Curcumin Core (Yellow)"><mesh>...</mesh></object>
<object id="2" name="Chitosan Shell (White)"><mesh>...</mesh></object>
<object id="3" name="NH3+ Charge Groups (Red)"><mesh>...</mesh></object>
<object id="4" name="Alginate Shell (Blue)"><mesh>...</mesh></object>
<object id="5" name="COO- Charge Groups (Green)"><mesh>...</mesh></object>
<object id="6" name="Nanoparticle Cutaway">
  <components>
    <component objectid="1"/>
    <component objectid="2"/>
    <component objectid="3"/>
    <component objectid="4"/>
    <component objectid="5"/>
  </components>
</object>
<build><item objectid="6"/></build>
```

---

## Print Settings

| Parameter | Value |
|-----------|-------|
| Nozzle | 0.4 mm |
| Layer height | 0.16–0.20 mm |
| Walls | 3–4 |
| Infill | 15% |
| Supports | Tree supports recommended (for cutaway overhang) |
| Adhesion | Brim recommended |

---

## Geometry Requirements

Every body must be:

- **Watertight** (manifold, closed mesh)
- **Valid volume** (consistent face normals, no self-intersections)
- **Non-overlapping** with other bodies (no shared volume between parts)

Use proper CSG boolean operations (difference, intersection) — not mesh concatenation. Previous attempts that used overlapping spheres without boolean subtraction produced 753+ non-manifold edges.

Recommended approach: **OpenSCAD** for CSG operations (clean boolean math), export individual STL bodies, verify with trimesh, then package into 3MF.

### Mesh Resolution

- Main spheres: $fn = 96
- Bump spheres: $fn = 24
- Total face count target: ~65,000–70,000 faces across all 5 bodies

---

## Known Pitfalls from Previous Iterations

1. **Bumps hidden inside alginate shell** — Early versions placed NH₃⁺ bumps on chitosan (r = 13 mm) but the alginate shell extended to r = 15 mm, completely covering them. Solution: NH₃⁺ bumps are only meant to be visible in the cutaway, not from outside. COO⁻ bumps on the alginate surface provide the exterior texture.

2. **Bumps too large** — When bumps were sized to punch through the alginate (2.5 mm radius), they looked like warts on a 30 mm sphere. Solution: 0.8 mm radius bumps that sit as surface hemispheres on their respective layers.

3. **Non-manifold geometry** — Concatenating overlapping sphere meshes without boolean operations. Solution: Use OpenSCAD CSG, verify every body is watertight.

4. **3MF structure wrong for Bambu Studio** — Separate top-level objects don't get per-part filament pickers. Solution: Use parent object with child components (see File Format section above).

5. **OpenSCAD brace escaping** — When generating OpenSCAD via Python f-strings, `{` and `}` must be escaped as `{{` and `}}` in f-strings but NOT in module definitions written as plain strings. Watch for double-brace bugs.

---

## Scientific Notes (For Design Accuracy)

- **Curcumin** is a hydrophobic polyphenol from turmeric. It sits in the core because it's insoluble in water and gets trapped in the chitosan gel network.
- **Chitosan** is a positively charged biopolymer (protonated NH₃⁺ groups at acidic pH). It forms an ionic gel mesh around the curcumin.
- **Alginate** is a negatively charged polysaccharide (COO⁻ carboxylate groups). It coats the chitosan through electrostatic attraction, forming a protective outer shell.
- The system is **pH-responsive**: the alginate shell protects the payload in stomach acid (pH ~1.2) and releases it in the colon (pH ~7.4) as the electrostatic interactions weaken.
- **CD44 targeting and molecular docking have NOT been performed** — do not include these in any labels or descriptions.
- The **β-cyclodextrin approach was abandoned** due to curcumin precipitation. The current formulation uses **Tween 80** for curcumin solubilization.
