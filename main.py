"""
nanojellprint — full pipeline:
  1. Read AMS filaments from printer
  2. Let user assign which slot goes to which body
  3. Generate STLs via OpenSCAD
  4. Package into a print-ready .3mf

Usage:
  python main.py [--no-printer] [--stl-dir DIR] [--out FILE]

  --no-printer   Skip printer connection; use default filament colors
  --stl-dir DIR  Use pre-generated STLs instead of re-rendering (fast)
  --out FILE     Output .3mf path (default: nanoparticle.3mf)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from make_3mf import BODIES, build_3mf
from model_gen import BODY_NAMES, generate_stls


# Default filament colors per body if no printer / no match
DEFAULT_COLORS = {
    "curcumin_core":   ("FFFF00", "Yellow"),
    "chitosan_shell":  ("FFFFFF", "White"),
    "nh3_bumps":       ("FF0000", "Red"),
    "alginate_shell":  ("0000FF", "Blue"),
    "coo_bumps":       ("00AA00", "Green"),
}


def pick_slots(slots, use_printer: bool) -> list | None:
    """
    Interactively map printer filament slots to the 5 bodies.
    Returns a list of 5 FilamentSlot objects (in BODIES order), or None.
    """
    if not use_printer or not slots:
        return None

    print("\nAvailable filament slots:")
    for i, s in enumerate(slots):
        print(f"  [{i}]  {s}")

    print("\nAssign a slot to each body (enter index, or blank to skip / use default):")
    assigned: list = []
    for body in BODIES:
        default_color, default_label = DEFAULT_COLORS[body.stl_key]
        while True:
            raw = input(f"  Body {body.number} — {body.name}  "
                        f"(default {default_label} #{default_color}): ").strip()
            if raw == "":
                assigned.append(None)
                break
            try:
                idx = int(raw)
                if 0 <= idx < len(slots):
                    assigned.append(slots[idx])
                    break
                print(f"    Index must be 0–{len(slots)-1}")
            except ValueError:
                print("    Enter a number or press Enter to skip.")

    return assigned


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate nanoparticle print .3mf")
    parser.add_argument("--no-printer", action="store_true",
                        help="Skip printer connection, use default colors")
    parser.add_argument("--stl-dir", type=Path, default=None,
                        help="Path to existing STL directory (skip re-rendering)")
    parser.add_argument("--out", type=Path, default=Path("nanoparticle.3mf"),
                        help="Output .3mf file path")
    parser.add_argument("--openscad", default="openscad",
                        help="Path to OpenSCAD binary")
    args = parser.parse_args()

    # ── Step 1: Read printer AMS ──────────────────────────────────────────────
    slots = []
    use_printer = not args.no_printer
    if use_printer:
        print("Connecting to printer...")
        try:
            from printer import print_slots, read_ams
            slots = read_ams()
            print_slots(slots)
        except Exception as e:
            print(f"Could not read printer AMS: {e}")
            print("Continuing with default filament colors.\n")
            use_printer = False

    # ── Step 2: Map slots to bodies ───────────────────────────────────────────
    filament_slots = pick_slots(slots, use_printer)

    # ── Step 3: Generate or locate STLs ──────────────────────────────────────
    if args.stl_dir:
        stl_dir = args.stl_dir
        stl_paths = {name: stl_dir / f"{name}.stl" for name in BODY_NAMES.values()}
        missing = [k for k, v in stl_paths.items() if not v.exists()]
        if missing:
            print(f"Missing STLs in {stl_dir}: {missing}")
            sys.exit(1)
        print(f"Using existing STLs from {stl_dir}/")
    else:
        stl_dir = args.out.parent / "stl_output"
        print(f"\nRendering STLs (this takes a few minutes)...")
        stl_paths = generate_stls(stl_dir, openscad_bin=args.openscad)

    # ── Step 4: Build .3mf ────────────────────────────────────────────────────
    print(f"\nPackaging {args.out}...")
    build_3mf(stl_paths, args.out, filament_slots)

    print(f"\nDone. Open {args.out} in Bambu Studio to verify and print.")


if __name__ == "__main__":
    main()
