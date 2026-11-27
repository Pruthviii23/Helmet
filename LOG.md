# Helmate log

Newest at the bottom. One line per thing done → result.

## 2026-11-22
- Made blueprint (8 sheets: schematics, wiring, code, parts, tests) → `blueprint.html`, [online](https://claude.ai/artifact/PygZuaMAihTNRJU6PGHCEJ)
- Installed arduino-cli 1.6.0 + ESP32 core 4.0.0 → works, uploads need no BOOT button
- Found both boards → COM7 = `14:63:93:6F:0D:BC`, COM8 = `E0:72:A1:6D:20:A4`
- ESP-NOW link test, full radio power → ❌ one way only (COM7's messages never arrived)
- Same test, radio power lowered to 8.5 dBm → ✅ both ways, 0 failures, signal −40 dBm
- Added the power fix to blueprint code (sheet 06) → keep it in every sketch
- Uploaded fast blink to COM7 → blue LED flashing = COM7
- Assigned roles → COM7 = helmet, COM8 = bike

## 2026-11-23
- Sensor test on helmet (COM7), FSR on GPIO5, Hall on GPIO3 → Hall ✅ (magnet seen), FSR ❌ (GPIO5 is ADC2, "adc unit not supported")
- Moved FSR to GPIO4, retested → FSR ✅ (0 at rest, up to ~1.4 V pressed, smooth ramp), Hall ✅ (magnet seen)
- Worn-link test, helmet (COM7) → bike (COM8) over ESP-NOW → ✅ 141/141 delivered, 0 fails; bike LED on only with magnet + pressure (4 times)
- Made working log page (V1 helmet sensors, V2 helmet→bike link, V3 planned) → `working.html`
- Pushed blueprint, working log, firmware to GitHub → ✅ branch `bench-tests`

## 2026-11-27
- Installed KiCad 10.0.8, FreeCAD 1.1.4, build123d 0.13, easyeda2kicad → ✅ (Blender 4.0 already there)
- Prototype pod enclosure, intercom-style universal mount (tape cradle + clamp kit) → ✅ 63×43×24 mm + 6 mm cradle, 9 printable parts
- Chin pod (MQ-3), Hall + magnet strap sleeves → ✅
- Prototype v3 circuit (MQ-3 + boost + heater switch, buzzer, long-press button, battery sense, keyed JST-PH plugs) → ✅ ERC 0 errors
- Production parts picked, all on LCSC/JLC: ESP32-C3-MINI-1, BQ25180, RT9080, LMP91000SDX + SPEC 110-202, DRV5032 → ✅
- Production schematics HB-1 main / AB-1 alcohol / SB-1 strap → ✅ ERC clean (2 known false alarms on USBLC6)
- Production pod concept → ✅ 50×38×15 mm, same cradle as prototype
- Blender renders → `hardware/renders/`
- Helmet scene in Blender (generic full-face helmet + real pod/cradle/sensor STLs, cables routed under the rim) → `hardware/renders/helmet/helmate_on_helmet.blend`
- Measured cable routes → FSR to crown 46 cm, HALL 28.7 cm, ALC 30.3 cm, FSR to cheek pad 19.4 cm ❌ planned 10/20/25 cm too short
- Turntable 36 angles × 3 heights × outside/x-ray + 7 close-ups → ✅ 223 renders, 8.9 MB
- Interactive fit viewer → ✅ `hardware/viewer/index.html` (drag/zoom, x-ray, part pins, lead-length check, notes)
