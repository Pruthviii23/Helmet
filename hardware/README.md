# Helmate hardware

Everything here is generated from code. Edit the `.py` file and re-run it. Don't hand-edit the outputs.

| What | Source | Output |
|---|---|---|
| Prototype enclosure (3D print) | `enclosure/proto/helmate_pod.py` | `enclosure/proto/out/*.stl, *.step` |
| Production enclosure concept | `enclosure/production/helmate_pod_v1.py` | `enclosure/production/out/` |
| Prototype circuit (perfboard) | `pcb/helmate_prototype.py` | `pcb/prototype/HP-0_prototype.pdf` + KiCad |
| Production circuit (3 boards) | `pcb/helmate_production.py` | `pcb/production/*.pdf`, `*_BOM.csv`, KiCad |
| Renders | `tools/render_stl.py` + `renders/scene_*.json` | `renders/*.png` |

Tools: build123d 0.13 (Python), KiCad 10.0.8 (`kicad-cli`), Blender 4.0, easyeda2kicad (LCSC parts → `pcb/lib/`).

## Prototype pod: print list
PETG or ASA. PLA softens on a parked bike in the sun. 0.2 mm layers, 3 walls.

| Part | Qty | Orientation | Notes |
|---|---|---|---|
| pod_body | 1 | back face down | dovetail prints as a short overhang, no supports |
| pod_lid | 1 | outer face down | flex button is part of the lid |
| cradle_tape **or** cradle_clamp + clamp_inner | 1 | back down | tape: 3M VHB 5952 on the curved back. clamp: 2 × M3×12 + 2 M3 nuts |
| alc_pod + alc_grille | 1 | base down | VHB inside a chin bar, or thread the chin strap through the base slot |
| hall_sleeve, magnet_sleeve | 1 each | flat | slide onto strap webbing up to 26 mm wide |

Hardware: 2 × M2×8 self-tapping screws (lid), 6×6 mm tact switch under the flex button.

**Measure your battery** and set `BAT_L, BAT_W, BAT_T` at the top of `helmate_pod.py`. The default is a 103450 pouch (50 × 34 × 10 mm).

## Check before ordering production boards
- BZ1 (MLT-8530): confirm which two pads are the coil from the datasheet drawing (assumed 1-2).
- J2 battery: match pin 1 = + to the cell you buy.
- S1 (SPEC 110-202): footprint is a placeholder, draw it from SPEC's mechanical drawing.
- Passive LCSC numbers: run the BOM through JLC's parts check.
