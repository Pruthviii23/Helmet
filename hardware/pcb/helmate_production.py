"""
Helmate production electronics, helmet side. Rev A, 2026-11-27.

Three boards:
  HB-1  main board in the helmet pod (ESP32-C3-MINI-1, charger, LDO, buzzer, button, USB-C)
  AB-1  alcohol board in the chin pod (SPEC 110-202 electrochemical EtOH cell + LMP91000)
  SB-1  strap board on the chin strap (DRV5032 nanopower Hall switch)
The FSR (Interlink FSR 402) plugs straight into HB-1.

Run: python hardware/pcb/helmate_production.py
Out: hardware/pcb/production/*.kicad_sch, BOM csv, netlist summary
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from schgen import Part, build, check, bom_csv, nets_of

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production")
os.makedirs(OUT, exist_ok=True)

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"

# JLC basic-part LCSC numbers for passives (check in JLC's BOM tool before ordering)
LCSC_R = {"10k": "C25744", "5.1k": "C25905", "1M": "C26083", "100k": "C25741", "100": "C25076", "1k": "C11702"}
LCSC_C = {"100nF": "C1525", "1uF": "C52923", "10uF": "C19702", "47nF": "C1532"}


def R(ref, val, a, b, note=""):
    return Part(ref, "Device:R", val, R0402, {"1": a, "2": b}, LCSC_R.get(val, ""), note=note)


def C(ref, val, a, b, note=""):
    fp = C0603 if val == "10uF" else C0402
    return Part(ref, "Device:C", val, fp, {"1": a, "2": b}, LCSC_C.get(val, ""), note=note)


# =====================================================================
# HB-1  main board
# =====================================================================
esp_gnd = [1, 2, 11, 14] + list(range(36, 54))
esp_nc = [4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32, 33, 34, 35]
esp = {str(n): "GND" for n in esp_gnd}
esp.update({str(n): None for n in esp_nc})
esp.update({
    "3": "+3V3", "8": "EN",
    "12": "ALC_OUT",      # IO0  ADC1_CH0  alcohol board output
    "13": "FSR_SENSE",    # IO1  ADC1_CH1  head pad
    "5": "IO2_STRAP",     # IO2  strapping pin, held high
    "6": "VBAT_SENSE",    # IO3  ADC1_CH3  battery voltage /2
    "18": "HALL",         # IO4  strap latched = LOW (deep-sleep wake capable)
    "19": "CHG_INT",      # IO5  charger /INT, button events (deep-sleep wake capable)
    "20": "SDA",          # IO6
    "21": "SCL",          # IO7
    "22": "LED_K",        # IO8  strapping pin, LED to 3V3 keeps it high at boot
    "23": "BOOT",         # IO9  strapping, pulled high, test pad
    "16": "BUZ_DRV",      # IO10
    "26": "USB_DN",       # IO18
    "27": "USB_DP",       # IO19
    "30": None, "31": None,   # UART0 (flash over USB instead)
})

hb1 = [
    "## MCU  ESP32-C3-MINI-1 (pre-certified radio module)",
    Part("U1", "helmate:ESP32-C3-MINI-1-N4", "ESP32-C3-MINI-1-N4", "helmate:WIFIM-SMD_ESP32-C3-MINI-1", esp,
         "C2838502", note="Pre-certified module (FCC/CE/IC/TELEC/SRRC). Keep antenna end at board edge, no copper under it."),
    C("C1", "10uF", "+3V3", "GND"), C("C2", "100nF", "+3V3", "GND"),
    R("R1", "10k", "+3V3", "EN"), C("C3", "1uF", "EN", "GND", note="EN power-on delay"),
    R("R2", "10k", "+3V3", "IO2_STRAP"),
    R("R3", "10k", "+3V3", "BOOT"),

    "## USB-C  charging + firmware over native USB",
    Part("J1", "helmate:TYPE-C-31-M-12", "USB-C 16P", "helmate:USB-C_SMD-TYPE-C-31-M-12_1", {
        "A4B9": "VBUS", "B4A9": "VBUS", "A1B12": "GND", "B1A12": "GND",
        "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
        "A8": None, "B8": None, "1": "GND", "2": "GND", "3": "GND", "4": "GND"}, "C165948", "HRO TYPE-C-31-M-12"),
    R("R4", "5.1k", "CC1", "GND", note="USB-C sink identification"),
    R("R5", "5.1k", "CC2", "GND", note="USB-C sink identification"),
    Part("U2", "helmate:USBLC6-2SC6", "USBLC6-2SC6", "helmate:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
         {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "2": "GND", "5": "VBUS"}, "C7519",
         note="ESD on USB data + VBUS"),

    "## POWER  BQ25180 charger + power path + long-press button, RT9080 3.3 V",
    Part("U3", "helmate:BQ25180YBGR", "BQ25180YBGR", "helmate:DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL", {
        "A2": "VBUS", "B2": "VSYS", "C2": "VBAT", "D2": "GND",
        "B1": "SCL", "C1": "SDA", "A1": "CHG_INT", "D1": "TS_MR"}, "C3682423",
         note="1 A linear charger, power path, ship mode 3 uA, long-press on TS/MR = ship mode or reset"),
    C("C4", "1uF", "VBUS", "GND", note="IN cap"),
    C("C5", "10uF", "VSYS", "GND", note="SYS cap"),
    C("C6", "1uF", "VBAT", "GND", note="BAT cap"),
    R("R6", "10k", "TS_MR", "GND", note="Stands in for a 10k NTC. Use the pack's NTC wire here if the cell has one."),
    Part("SW1", "helmate:TS-1187A-B-A-B", "Power button", "helmate:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
         {"1": "TS_MR", "2": "TS_MR", "3": "GND", "4": "GND"}, "C318884",
         note="Long press = on/off (ship mode). Pads 1-2 and 3-4 are the internally joined pairs."),
    R("R7", "10k", "+3V3", "SCL"), R("R8", "10k", "+3V3", "SDA"), R("R9", "10k", "+3V3", "CHG_INT"),
    Part("J2", "helmate:S2B-PH-SM4-TB", "Battery", "helmate:CONN-SMD_P2.00_S2B-PH-SM4-TB-LF-SN",
         {"1": "VBAT", "2": "GND", "3": None, "4": None}, "C295747",
         note="JST-PH 2 pin. Check the cell's lead order: pin 1 = +. Cell must carry its own protection PCM."),

    Part("U4", "helmate:RT9080-33GJ5", "RT9080-33GJ5", "helmate:TSOT-23-5_L2.9-W1.6-P0.95-LS2.8-BL",
         {"1": "VSYS", "3": "VSYS", "2": "GND", "5": "+3V3", "4": None}, "C841192",
         note="600 mA LDO, 2 uA quiescent"),
    C("C7", "1uF", "VSYS", "GND"), C("C8", "10uF", "+3V3", "GND"),

    "## SENSORS  battery, head pad (FSR), strap (Hall), alcohol board",
    R("R10", "1M", "VBAT", "VBAT_SENSE"), R("R11", "1M", "VBAT_SENSE", "GND"), C("C9", "100nF", "VBAT_SENSE", "GND"),

    Part("J3", "helmate:SM02B-SRSS-TB", "FSR", "helmate:CONN-SMD_2P-P1.00_SM02B-SRSS-TB-LF-SN",
         {"1": "+3V3", "2": "FSR_SENSE", "3": None, "4": None}, "C160402", note="JST-SH 2 pin to Interlink FSR 402"),
    R("R12", "10k", "FSR_SENSE", "GND"), C("C10", "100nF", "FSR_SENSE", "GND"),

    Part("J4", "helmate:SM03B-SRSS-TB", "HALL", "helmate:CONN-SMD_SM03B-SRSS-TB-LF-SN-P",
         {"1": "+3V3", "2": "HALL", "3": "GND", "4": None, "5": None}, "C160403", note="JST-SH 3 pin to SB-1"),
    C("C11", "100nF", "HALL", "GND", note="cable filter"),

    Part("J5", "helmate:SM06B-SRSS-TB", "ALC", "helmate:CONN-SMD_SM06B-SRSS-TB-LF-SN",
         {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "ALC_OUT", "6": "GND", "7": None, "8": None},
         "C160405", note="JST-SH 6 pin to AB-1"),
    C("C12", "100nF", "ALC_OUT", "GND", note="with AB-1's 1k = 1.6 kHz low-pass"),

    "## WARNING  buzzer (PWM 2.7 kHz) + status LED",
    Part("Q1", "helmate:AO3400A", "AO3400A", "helmate:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
         {"1": "BUZ_G", "2": "GND", "3": "BUZ_N"}, "C20917"),
    R("R13", "100", "BUZ_DRV", "BUZ_G"), R("R14", "100k", "BUZ_G", "GND", note="keeps it off during boot"),
    Part("BZ1", "helmate:MLT-8530", "MLT-8530", "helmate:BUZ-SMD_4P-L8.5-W8.5-P8.50-BR",
         {"1": "VSYS", "2": "BUZ_N", "3": None, "4": None}, "C94599",
         note="VERIFY PADS against the datasheet drawing before ordering: coil assumed on pads 1-2"),
    Part("D1", "Device:D", "1N4148WS", "Diode_SMD:D_SOD-323", {"1": "VSYS", "2": "BUZ_N"}, "C2128",
         note="flyback across the buzzer coil"),

    Part("D2", "Device:LED", "Green", "LED_SMD:LED_0603_1608Metric", {"1": "LED_K", "2": "LED_A"}, "C72043"),
    R("R15", "1k", "+3V3", "LED_A"),
]

# =====================================================================
# AB-1  alcohol board (chin pod)
# =====================================================================
ab1 = [
    "## AB-1  alcohol board: SPEC 110-202 electrochemical cell + LMP91000 potentiostat",
    Part("J1", "helmate:SM06B-SRSS-TB", "ALC", "helmate:CONN-SMD_SM06B-SRSS-TB-LF-SN",
         {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "ALC_OUT", "6": "GND", "7": None, "8": None}, "C160405"),
    Part("U1", "helmate:LMP91000SDX_NOPB", "LMP91000SDX/NOPB", "helmate:WSON-14_L4.0-W4.0-P0.50-BL-EP-1", {
        "6": "+3V3", "7": "GND", "1": "GND", "15": "GND", "4": "SDA", "3": "SCL", "2": "GND",
        "8": "VOUT", "9": "TIA_C2", "10": "TIA_C1", "11": "+3V3", "12": "WE", "13": "RE", "14": "CE", "5": None},
         "C2651584", note="Potentiostat AFE, I2C addr 0x48. MENB tied low = always on (~10 uA). VREF = VDD."),
    C("C1", "100nF", "+3V3", "GND"), C("C2", "10uF", "+3V3", "GND"),
    C("C3", "47nF", "TIA_C1", "TIA_C2", note="TIA low-pass, tune per SPEC app note"),
    R("R1", "1k", "VOUT", "ALC_OUT", note="cable driver isolation"),
    Part("S1", "Connector_Generic:Conn_01x03", "SPEC 110-202 EtOH", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
         {"1": "WE", "2": "RE", "3": "CE"}, "C6970020",
         note="PLACEHOLDER FOOTPRINT: draw from SPEC 110-202 mechanical drawing before layout"),
]

# =====================================================================
# SB-1  strap board
# =====================================================================
sb1 = [
    "## SB-1  strap board: DRV5032 nanopower Hall switch",
    Part("J1", "helmate:SM03B-SRSS-TB", "HALL", "helmate:CONN-SMD_SM03B-SRSS-TB-LF-SN-P",
         {"1": "+3V3", "2": "HALL", "3": "GND", "4": None, "5": None}, "C160403"),
    Part("U1", "helmate:DRV5032FBDBZR", "DRV5032FB", "helmate:SOT-23_L2.9-W1.3-P1.90-LS2.4-BR",
         {"1": "+3V3", "2": "HALL", "3": "GND"}, "C2655033", note="0.5 uA omnipolar Hall switch, 5 Hz, push-pull"),
    C("C1", "100nF", "+3V3", "GND"),
]

if __name__ == "__main__":
    for name, parts, title in [("HB-1_main", hb1, "Helmate HB-1 main board"),
                               ("AB-1_alcohol", ab1, "Helmate AB-1 alcohol board"),
                               ("SB-1_strap", sb1, "Helmate SB-1 strap Hall board")]:
        bad = check(parts)
        if bad:
            print(name, "SINGLE-PIN NETS:", bad)
        build(parts, os.path.join(OUT, f"{name}.kicad_sch"), title, name,
              comment="Generated from hardware/pcb/helmate_production.py, edit there")
        bom_csv(parts, os.path.join(OUT, f"{name}_BOM.csv"))
        json.dump(nets_of(parts), open(os.path.join(OUT, f"{name}_nets.json"), "w"), indent=1)
        print(f"{name}: {len([p for p in parts if not isinstance(p, str)])} parts, {len(nets_of(parts))} nets")
