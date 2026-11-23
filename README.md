# Helmate

A smart helmet that talks to your bike. Wear it and click the strap, or the bike won't start.

- **Helmet:** ESP32-C3 SuperMini + pressure pad (FSR) + Hall sensor and magnet on the strap.
- **Bike:** ESP32-C3 SuperMini + relay on the self-start line.
- The helmet pings the bike over ESP-NOW while it's worn and buckled. No pings, no power to the starter.

Open `index.html` in a browser for the interactive explainer.

Open `blueprint.html` for the bench wiring set: schematics, wiring tables, firmware, parts list and bring-up steps.

Open `working.html` for the working log: what has been wired and tested so far, version by version.
