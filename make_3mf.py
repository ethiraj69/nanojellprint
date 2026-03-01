"""
Package 5 STL bodies + filament assignments into a Bambu-compatible .3mf.

The .3mf is a ZIP containing:
  [Content_Types].xml
  _rels/.rels
  3D/3dmodel.model          ← geometry + object/component structure
  Metadata/model_settings.config  ← per-object filament index assignments
  Metadata/plate_1.json     ← plate config with filament list
  Metadata/filament_X.json  ← one per filament slot used
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import NamedTuple

import numpy as np
import trimesh


# ── Body metadata ──────────────────────────────────────────────────────────────

class BodyDef(NamedTuple):
    number: int        # 1-5
    name: str
    stl_key: str       # matches model_gen.BODY_NAMES values
    filament_idx: int  # 1-based filament index in the .3mf


BODIES: list[BodyDef] = [
    BodyDef(1, "Curcumin Core (Yellow)",    "curcumin_core",   1),
    BodyDef(2, "Chitosan Shell (White)",    "chitosan_shell",  2),
    BodyDef(3, "NH3+ Charge Groups (Red)",  "nh3_bumps",       3),
    BodyDef(4, "Alginate Shell (Blue)",     "alginate_shell",  4),
    BodyDef(5, "COO- Charge Groups (Green)","coo_bumps",       5),
]


def _read_stl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (vertices Nx3, faces Mx3-indices) with shared vertices via trimesh."""
    m = trimesh.load(str(path), force="mesh")
    return np.array(m.vertices, dtype=float), np.array(m.faces, dtype=int)


def _vertices_xml(verts: np.ndarray) -> str:
    lines = ["      <vertices>"]
    for x, y, z in verts:
        lines.append(f'        <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>')
    lines.append("      </vertices>")
    return "\n".join(lines)


def _triangles_xml(tris: np.ndarray) -> str:
    lines = ["      <triangles>"]
    for v1, v2, v3 in tris:
        lines.append(f'        <triangle v1="{v1}" v2="{v2}" v3="{v3}"/>')
    lines.append("      </triangles>")
    return "\n".join(lines)


# ── XML builders ──────────────────────────────────────────────────────────────

CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Default Extension="config" ContentType="application/xml"/>
  <Default Extension="json" ContentType="application/json"/>
</Types>"""

RELS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0"
    Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def _build_3dmodel(stl_paths: dict[str, Path]) -> str:
    """Build the main 3dmodel.model XML with all 5 bodies + parent component object."""
    object_xmls: list[str] = []

    for body in BODIES:
        stl_path = stl_paths[body.stl_key]
        verts, tris = _read_stl(stl_path)
        vxml = _vertices_xml(verts)
        txml = _triangles_xml(tris)
        object_xmls.append(
            f'  <object id="{body.number}" name="{body.name}" type="model">\n'
            f"    <mesh>\n{vxml}\n{txml}\n    </mesh>\n"
            f"  </object>"
        )

    parent_id = len(BODIES) + 1
    components = "\n".join(
        f'      <component objectid="{b.number}"/>' for b in BODIES
    )
    object_xmls.append(
        f'  <object id="{parent_id}" name="Nanoparticle Cutaway" type="model">\n'
        f"    <components>\n{components}\n    </components>\n"
        f"  </object>"
    )

    objects_block = "\n".join(object_xmls)
    build_item = f'    <item objectid="{parent_id}"/>'

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US"\n'
        '  xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"\n'
        '  xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06">\n'
        "  <resources>\n"
        f"{objects_block}\n"
        "  </resources>\n"
        "  <build>\n"
        f"{build_item}\n"
        "  </build>\n"
        "</model>"
    )


def _build_model_settings(filament_slots: list | None) -> str:
    """
    Bambu-specific config that assigns each component object its filament index.
    Each body (ids 1-5) gets its own <object> entry with an extruder assignment.
    """
    objects_xml = []
    for body in BODIES:
        objects_xml.append(
            f'  <object id="{body.number}">\n'
            f'    <metadata key="extruder" value="{body.filament_idx}"/>\n'
            f"  </object>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<config>\n"
        "  <plate>\n"
        '    <metadata key="plater_id" value="1"/>\n'
        "  </plate>\n"
        + "\n".join(objects_xml) + "\n"
        "</config>"
    )


def _filament_json(slot, idx: int) -> str:
    """
    Build the filament_N.json for Bambu Studio.
    slot is a FilamentSlot (or None to use defaults).
    """
    if slot is not None:
        color = f"#{slot.color_hex.upper()}"
        mat   = slot.material
        bed   = str(slot.bed_temp)
        noz   = str(slot.nozzle_min)
    else:
        # defaults per body
        defaults = [
            ("#FFFF00", "PLA", "55", "220"),
            ("#FFFFFF", "PLA", "55", "220"),
            ("#FF0000", "PLA", "55", "220"),
            ("#0000FF", "PLA", "55", "220"),
            ("#00AA00", "PLA", "55", "220"),
        ]
        color, mat, bed, noz = defaults[idx - 1]

    return json.dumps({
        "filament_colour":     [color],
        "filament_type":       [mat],
        "filament_vendor":     [""],
        "bed_temperature":     [bed],
        "nozzle_temperature":  [noz],
    }, indent=2)


def _plate_json(filament_slots: list | None) -> str:
    filaments = []
    for i, body in enumerate(BODIES):
        slot = filament_slots[i] if filament_slots else None
        color = f"#{slot.color_hex.upper()}" if slot else ["#FFFF00","#FFFFFF","#FF0000","#0000FF","#00AA00"][i]
        mat   = slot.material if slot else "PLA"
        filaments.append({
            "id":    body.filament_idx,
            "type":  mat,
            "color": color,
        })
    return json.dumps({
        "plate_index": 1,
        "filaments":   filaments,
        "print_settings": {
            "layer_height":    0.2,
            "nozzle_diameter": 0.4,
            "infill_density":  "15%",
            "support_type":    "tree(organic)",
            "brim_type":       "brim",
        },
    }, indent=2)


# ── Main packager ─────────────────────────────────────────────────────────────

def build_3mf(
    stl_paths: dict[str, Path],
    out_path: Path,
    filament_slots: list | None = None,
) -> Path:
    """
    stl_paths: {"curcumin_core": Path, "chitosan_shell": Path, ...}
    filament_slots: list of 5 FilamentSlot objects in BODIES order, or None for defaults.
    """
    print("Building 3dmodel.model...")
    model_xml = _build_3dmodel(stl_paths)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model_xml)
        z.writestr("Metadata/model_settings.config", _build_model_settings(filament_slots))
        z.writestr("Metadata/plate_1.json", _plate_json(filament_slots))
        for i, body in enumerate(BODIES):
            slot = filament_slots[i] if filament_slots else None
            z.writestr(
                f"Metadata/filament_{body.filament_idx}.json",
                _filament_json(slot, body.filament_idx),
            )

    size_kb = out_path.stat().st_size // 1024
    print(f"Written: {out_path}  ({size_kb:,} KB)")
    return out_path


if __name__ == "__main__":
    import sys
    stl_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("stl_output")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("nanoparticle.3mf")

    from model_gen import BODY_NAMES
    stl_paths = {name: stl_dir / f"{name}.stl" for name in BODY_NAMES.values()}
    missing = [k for k, v in stl_paths.items() if not v.exists()]
    if missing:
        print(f"Missing STLs: {missing}\nRun model_gen.py first.")
        sys.exit(1)

    build_3mf(stl_paths, out)
