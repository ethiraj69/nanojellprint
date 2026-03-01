"""
Read AMS filament state from a Bambu Lab printer.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class FilamentSlot:
    ams_id: int
    slot: int
    color_hex: str   # e.g. "FFFF00" — no leading #
    material: str    # e.g. "PLA"
    bed_temp: int
    nozzle_min: int
    nozzle_max: int

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        h = self.color_hex.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def __str__(self) -> str:
        return (
            f"AMS{self.ams_id}/Slot{self.slot}  #{self.color_hex}  "
            f"{self.material}  bed={self.bed_temp}°C  "
            f"nozzle={self.nozzle_min}–{self.nozzle_max}°C"
        )


def read_ams(
    ip: str | None = None,
    access_code: str | None = None,
    serial: str | None = None,
    wait_seconds: float = 3.0,
) -> list[FilamentSlot]:
    """
    Connect to the printer, wait for an MQTT state update, then return
    all loaded filament slots from every connected AMS unit.
    """
    import bambulabs_api as bl

    ip = ip or os.environ["BAMBU_IP"]
    access_code = access_code or os.environ["BAMBU_ACCESS_CODE"]
    serial = serial or os.environ["BAMBU_SERIAL"]

    printer = bl.Printer(ip, access_code, serial)
    printer.connect()

    # Give the MQTT subscription time to receive at least one state message
    time.sleep(wait_seconds)

    slots: list[FilamentSlot] = []

    hub = printer.ams_hub()
    if hub is None:
        printer.disconnect()
        raise RuntimeError("No AMS data received — is developer mode enabled?")

    for ams_id, ams in hub.ams_hub.items():
        for slot_idx, tray in ams.filament_trays.items():
            if not tray or not tray.tray_type:
                continue  # empty slot
            slots.append(
                FilamentSlot(
                    ams_id=int(ams_id),
                    slot=int(slot_idx),
                    color_hex=tray.tray_color.lstrip("#"),
                    material=tray.tray_type,
                    bed_temp=int(tray.bed_temp or 0),
                    nozzle_min=int(tray.nozzle_temp_min or 0),
                    nozzle_max=int(tray.nozzle_temp_max or 0),
                )
            )

    printer.disconnect()
    return sorted(slots, key=lambda s: (s.ams_id, s.slot))


def print_slots(slots: list[FilamentSlot]) -> None:
    if not slots:
        print("No filaments found.")
        return
    print(f"Found {len(slots)} filament slot(s):")
    for s in slots:
        print(f"  {s}")


if __name__ == "__main__":
    slots = read_ams()
    print_slots(slots)
