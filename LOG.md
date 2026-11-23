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
