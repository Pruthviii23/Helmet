"""
Helmate prototype helmet pod v3 (hand-wired on perfboard). 2026-11-27.

Adds to the bench-tested V2 (FSR GPIO4, Hall GPIO3, unchanged):
  MQ-3 alcohol sensor in the chin pod, 5 V mini boost + NPN heater switch,
  3 V active buzzer, long-press power button (deep sleep), battery sense,
  JST-PH plugs for the three sensors (2 / 3 / 4 pin, so they can't be swapped).

Run: python hardware/pcb/helmate_prototype.py  ->  hardware/pcb/prototype/
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from schgen import Part, build, check, bom_csv, nets_of

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prototype")
os.makedirs(OUT, exist_ok=True)


def R(ref, val, a, b, note=""):
    return Part(ref, "Device:R", val, "", {"1": a, "2": b}, note=note)


def C(ref, val, a, b, note=""):
    return Part(ref, "Device:C", val, "", {"1": a, "2": b}, note=note)


# ESP32-C3 SuperMini, both header rows as one 16-pin connector.
# 1..8  = 5V, GND, 3V3, GPIO4, GPIO3, GPIO2, GPIO1, GPIO0
# 9..16 = GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO20, GPIO21
supermini = {
    "1": "VSYS", "2": "GND", "3": "+3V3",
    "4": "FSR_SENSE",   # GPIO4  (unchanged from V2)
    "5": "HALL",        # GPIO3  (unchanged from V2)
    "6": None,          # GPIO2  strapping pin, leave free
    "7": "VBAT_SENSE",  # GPIO1  ADC1
    "8": "ALC_SENSE",   # GPIO0  ADC1
    "9": "BTN",         # GPIO5  button, deep-sleep wake
    "10": "HEAT_DRV",   # GPIO6  MQ-3 heater on
    "11": "BUZ_DRV",    # GPIO7  buzzer on
    "12": None,         # GPIO8  onboard blue LED
    "13": None,         # GPIO9  BOOT button
    "14": "BOOST_EN",   # GPIO10 boost converter on
    "15": None, "16": None,
}

proto = [
    "## POWER  battery -> TP4056 (USB-C) -> storage switch -> SuperMini 5V pin + boost",
    Part("BT1", "Device:Battery_Cell", "LiPo 2000 mAh", "", {"1": "BAT+", "2": "GND"}),
    Part("M1", "Connector_Generic:Conn_01x06", "TP4056 USB-C module", "",
         {"1": "USB_IN+", "2": "GND", "3": "BAT+", "4": "GND", "5": "TP_OUT", "6": "GND"},
         note="pads: 1 IN+  2 IN-  3 B+  4 B-  5 OUT+  6 OUT-  (IN pads unused, USB-C used)"),
    Part("SW2", "Switch:SW_SPDT", "Storage switch", "", {"2": "TP_OUT", "1": "VSYS", "3": None},
         note="small slide switch, hard off for storage/shipping"),
    Part("M2", "Connector_Generic:Conn_01x04", "5V mini boost", "",
         {"1": "VSYS", "2": "GND", "3": "BOOST_EN", "4": "+5V_HEAT"},
         note="Pololu U1V11F5 or any >=300 mA 5 V step-up with EN. pads: 1 VIN 2 GND 3 EN 4 VOUT"),
    R("R1", "100k", "VSYS", "VBAT_SENSE"), R("R2", "100k", "VBAT_SENSE", "GND"),
    C("C1", "100nF", "VBAT_SENSE", "GND"),
    Part("TP1", "Connector_Generic:Conn_01x02", "USB_IN (unused)", "", {"1": "USB_IN+", "2": "GND"},
         note="placeholder so the unused TP4056 IN+ pad shows as a net"),

    "## MCU  ESP32-C3 SuperMini",
    Part("U1", "Connector_Generic:Conn_01x16", "ESP32-C3 SuperMini", "", supermini,
         note="1-8: 5V GND 3V3 IO4 IO3 IO2 IO1 IO0 | 9-16: IO5 IO6 IO7 IO8 IO9 IO10 IO20 IO21"),
    Part("SW1", "Switch:SW_Push", "Power button (6x6 tact)", "", {"1": "BTN", "2": "GND"},
         note="under the lid's flex button. Internal pull-up. Long press 2 s = on/off"),

    "## SENSOR PLUGS  JST-PH 2.0: FSR 2 pin, HALL 3 pin, ALC 4 pin (can't be mixed up)",
    Part("J1", "Connector_Generic:Conn_01x02", "FSR (JST-PH 2)", "", {"1": "+3V3", "2": "FSR_SENSE"}, note="10 cm lead"),
    R("R3", "10k", "FSR_SENSE", "GND", note="existing R1 from the blueprint"),
    Part("J2", "Connector_Generic:Conn_01x03", "HALL (JST-PH 3)", "", {"1": "+3V3", "2": "HALL", "3": "GND"},
         note="20 cm lead. A3144 is rated 4.5 V min; it worked at 3.3 V on the bench, swap for a DRV5032/AH3366 if it gets flaky"),
    Part("J3", "Connector_Generic:Conn_01x04", "ALC (JST-PH 4)", "",
         {"1": "+5V_HEAT", "2": "HEAT_LOW", "3": "MQ_B", "4": None}, note="pin 4 empty = key. ~25 cm lead to the chin pod"),

    "## CHIN POD  bare MQ-3 (6 pins: A A, B B, H H)",
    Part("S1", "Connector_Generic:Conn_01x06", "MQ-3 sensor", "",
         {"1": "+5V_HEAT", "2": "+5V_HEAT", "3": "MQ_B", "4": "MQ_B", "5": "+5V_HEAT", "6": "HEAT_LOW"},
         note="1-2 = A pins (tie), 3-4 = B pins (tie), 5-6 = heater H pins"),
    Part("J4", "Connector_Generic:Conn_01x04", "ALC plug (chin side)", "",
         {"1": "+5V_HEAT", "2": "HEAT_LOW", "3": "MQ_B", "4": None}),

    "## ALCOHOL READOUT + HEATER SWITCH",
    R("R4", "100k", "MQ_B", "ALC_SENSE", note="RL = R4 + R5 = 300k, also scales 5 V down to 3.3 V"),
    R("R5", "200k", "ALC_SENSE", "GND"),
    C("C2", "100nF", "ALC_SENSE", "GND"),
    Part("Q1", "Device:Q_NPN", "S8050", "", {"B": "Q1_B", "C": "HEAT_LOW", "E": "GND"},
         note="switches the 150 mA heater; S8050/SS8050 (500 mA), not 2N3904"),
    R("R6", "220", "HEAT_DRV", "Q1_B"), R("R7", "10k", "Q1_B", "GND", note="off while booting"),

    "## BUZZER  3 V active, 9 mm",
    Part("BZ1", "Device:Buzzer", "3V active buzzer", "", {"1": "+3V3", "2": "BUZ_N"}, note="e.g. TMB09A03, ~30 mA"),
    Part("Q2", "Device:Q_NPN", "S8050", "", {"B": "Q2_B", "C": "BUZ_N", "E": "GND"}),
    R("R8", "1k", "BUZ_DRV", "Q2_B"), R("R9", "10k", "Q2_B", "GND"),
    Part("D1", "Device:D", "1N4148", "", {"1": "+3V3", "2": "BUZ_N"}, note="flyback"),
]

if __name__ == "__main__":
    bad = check(proto)
    if bad:
        print("SINGLE-PIN NETS:", bad)
    build(proto, os.path.join(OUT, "HP-0_prototype.kicad_sch"), "Helmate prototype pod v3 (perfboard)",
          "HP-0_prototype", comment="Hand-wired. Generated from hardware/pcb/helmate_prototype.py")
    bom_csv(proto, os.path.join(OUT, "HP-0_parts.csv"))
    print(f"{len([p for p in proto if not isinstance(p, str)])} parts, {len(nets_of(proto))} nets")
