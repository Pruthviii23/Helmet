"""
Helmate prototype helmet pod: universal, intercom-style mount.

Run:  python hardware/enclosure/proto/helmate_pod.py
Out:  hardware/enclosure/proto/out/*.stl + *.step

Parts
  pod_body       main box (battery, perfboard, SuperMini, TP4056, boost, buzzer)
  pod_lid        outer face with flex button and 2 screw holes
  cradle_tape    slide-in cradle, curved back for 3M VHB tape (any shell)
  cradle_clamp   same cradle + clamp arm that pinches the helmet's bottom edge
  clamp_inner    thin plate that goes between shell and liner, with nut traps
  alc_pod        chin pod for the bare MQ-3 sensor (tape to chin bar or thread on strap)
  alc_grille     front grille for alc_pod
  hall_sleeve    slides onto the chin strap, holds the A3144
  magnet_sleeve  slides onto the other strap end, holds a 10x3 mm disc magnet

Axes (pod as mounted on the left side of the helmet):
  X = along the helmet (front-back), Y = up, Z = out of the shell.
  Z = 0 is the pod's back face; the cradle sits at Z < 0.
"""
from build123d import *
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ---------------- parameters (mm) ----------------
# Battery: 2000 mAh pouch. Default is the common 103450 size (10 x 34 x 50).
# MEASURE YOURS and change these three numbers; everything else follows.
BAT_L, BAT_W, BAT_T = 50.0, 34.0, 10.0
FIT = 1.0                     # slack around the battery

WALL = 2.0                    # side walls
FLOOR = 2.0                   # back wall (helmet side)
LID_T = 2.0
PCB_T = 1.6                   # perfboard
PCB_GAP = 0.4                 # air between battery and perfboard
PARTS_H = 7.0                 # tallest part on the perfboard (JST header, USB-C)
TOL = 0.25                    # sliding fit clearance per side (FDM)

CAV_L = BAT_L + FIT + 2 * 3.6 + 0.8       # + room for the two screw bosses
CAV_W = BAT_W + FIT + 2 * 1.5 + 1.0       # + perfboard ledges
BAT_TOP = FLOOR + BAT_T + FIT
LEDGE_Z = BAT_TOP + PCB_GAP
PCB_TOP = LEDGE_Z + PCB_T
BODY_H = PCB_TOP + PARTS_H + 0.4          # body height, lid sits on top
OUT_L, OUT_W = CAV_L + 2 * WALL, CAV_W + 2 * WALL
POD_H = BODY_H + LID_T

# Dovetail tongue on the pod back
DT_NARROW, DT_WIDE, DT_H = 26.0, 31.0, 2.5   # narrow at the pod, wide at the tip
DT_Y0, DT_Y1 = -OUT_W / 2 + 2.0, OUT_W / 2   # tongue stops 2 mm short of the bottom
NOTCH_Y = OUT_W / 2 - 7.0                    # latch notch center

# Cradle
CR_BASE = 3.5                 # cradle back plate thickness
CR_RAIL = 3.0                 # rail wall width beside the dovetail
CR_W = DT_WIDE + 2 * TOL + 2 * CR_RAIL + 4.0
SHELL_R = 130.0               # helmet side curvature for the tape cradle

# Clamp
CLAMP_DROP = 30.0             # pod bottom -> helmet rim
SHELL_T = 4.0                 # nominal shell thickness (clamp adjusts ~2.5..7)


def rbox(l, w, h, r=0.0, z0=0.0):
    b = Pos(0, 0, z0) * Box(l, w, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if r > 0:
        b = fillet(b.edges().filter_by(Axis.Z), r)
    return b


def prism_xz(pts, y0, y1):
    """Profile in X-Z, extruded along Y from y0 to y1."""
    p = extrude(Plane.XZ * Polygon(*pts, align=None), amount=y1 - y0)
    return Pos(0, y0 - p.bounding_box().min.Y, 0) * p


def prism_yz(pts, x0, x1):
    """Profile in Y-Z, extruded along X from x0 to x1."""
    p = extrude(Plane.YZ * Polygon(*pts, align=None), amount=x1 - x0)
    return Pos(x0 - p.bounding_box().min.X, 0, 0) * p


def dovetail(narrow, wide, h, z_base, y0, y1, grow=0.0):
    """Trapezoid: `narrow` at z_base, `wide` at z_base - h (pointing into the cradle)."""
    n, w = narrow / 2 + grow, wide / 2 + grow
    pts = [(-n, z_base + grow), (n, z_base + grow), (w, z_base - h - grow), (-w, z_base - h - grow)]
    return prism_xz(pts, y0, y1)


def hole_y(d, x, z, y0, y1):
    """Round hole along Y."""
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, abs(y1 - y0))


def hole_x(d, y, z, x0, x1):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, abs(x1 - x0))


def label(txt, size, depth):
    try:
        return extrude(Text(txt, size), amount=depth)
    except Exception:
        return None


# =====================================================================
# POD BODY
# =====================================================================
def make_pod_body():
    body = rbox(OUT_L, OUT_W, BODY_H, r=6.0)
    body = fillet(body.edges().group_by(Axis.Z)[0], 1.5)       # soften the back edge
    body -= rbox(CAV_L, CAV_W, BODY_H, r=4.0, z0=FLOOR)

    # screw bosses, merged into the two end walls (M2 self-tapping, 1.7 mm pilot)
    for sx in (-1, 1):
        bx = sx * (CAV_L / 2 - 0.8)
        boss = Pos(bx, 0, FLOOR) * Cylinder(2.8, BODY_H - FLOOR, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body += boss
        body -= Pos(bx, 0, BODY_H - 9) * Cylinder(0.85, 9.01, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # perfboard ledges along the long walls
    for sy in (-1, 1):
        ly = sy * (CAV_W / 2 - 0.75)
        body += Pos(0, ly, FLOOR) * Box(CAV_L - 10, 1.5, LEDGE_Z - FLOOR,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))

    # ---- openings on the BOTTOM wall (faces down, out of the rain) ----
    yb0, yb1 = -OUT_W / 2 - 1, -CAV_W / 2 + 1
    zc = PCB_TOP + 3.2
    cuts = [
        ("CHG", -OUT_L / 2 + 14.0, 10.5, 4.8),   # TP4056 USB-C
        ("FSR", -4.0, 2 * 1 + 4.8, 6.0),          # JST-PH 2 pin
        ("HALL", 7.0, 2 * 2 + 4.8, 6.0),          # JST-PH 3 pin
        ("ALC", 20.0, 2 * 3 + 4.8, 6.0),          # JST-PH 4 pin (pin 4 unused, it's the key)
    ]
    for name, x, w, h in cuts:
        body -= Pos(x, (yb0 + yb1) / 2, zc) * Box(w, yb1 - yb0, h)
    # buzzer sound holes
    for dx in (-2.5, 0, 2.5):
        body -= hole_y(1.6, OUT_L / 2 - 6.5 + dx, zc, yb0, yb1)

    # ---- left end wall: SuperMini USB-C (programming), right end: storage switch ----
    body -= Pos(-OUT_L / 2, CAV_W / 2 - 10, PCB_TOP + 3.0) * Box(8, 10.5, 6.0)
    body -= Pos(OUT_L / 2, CAV_W / 2 - 10, PCB_TOP + 3.0) * Box(8, 9.0, 4.0)

    # ---- dovetail tongue on the back, with the latch notch ----
    tongue = dovetail(DT_NARROW, DT_WIDE, DT_H, 0.0, DT_Y0, DT_Y1)
    tongue -= Pos(0, NOTCH_Y, -DT_H) * Box(9, 5, 2.4)          # notch the latch bump drops into
    body += tongue

    # ---- port labels, debossed on the bottom face ----
    for name, x, w, h in cuts:
        t = label(name, 3.0, 0.6)
        if t is not None:
            body -= Pos(x, -OUT_W / 2 + 0.59, zc - 5.2) * Rot(90, 0, 0) * t
    return body


# =====================================================================
# POD LID
# =====================================================================
BTN_X, BTN_Y = 14.0, 4.0     # center of the flex button (put the 6x6 tact switch under it)


def make_pod_lid():
    lid = rbox(OUT_L, OUT_W, LID_T, r=6.0, z0=BODY_H)
    lid = fillet(lid.edges().group_by(Axis.Z)[-1], 1.2)
    # locating lip that drops into the cavity
    lip = rbox(CAV_L - 2 * TOL, CAV_W - 2 * TOL, 1.6, r=4.0, z0=BODY_H - 1.6)
    lip -= rbox(CAV_L - 2 * TOL - 2.4, CAV_W - 2 * TOL - 2.4, 1.6, r=3.0, z0=BODY_H - 1.6)
    for sx in (-1, 1):
        lip -= Pos(sx * (CAV_L / 2 - 0.8), 0, BODY_H - 1.6) * Cylinder(3.5, 1.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lid += lip
    # screw holes + counterbores
    for sx in (-1, 1):
        x = sx * (CAV_L / 2 - 0.8)
        lid -= Pos(x, 0, BODY_H) * Cylinder(1.15, LID_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        lid -= Pos(x, 0, BODY_H + LID_T - 1.0) * Cylinder(2.1, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # flex button: U-shaped slot leaves a 12 x 11 tongue hinged at the top
    slot_w = 1.0
    for sx in (-1, 1):
        lid -= Pos(BTN_X + sx * 6.5, BTN_Y - 0.5, BODY_H) * Box(slot_w, 13, LID_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lid -= Pos(BTN_X, BTN_Y - 6.5, BODY_H) * Box(14, slot_w, LID_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # thin the tongue so it flexes, add a pusher nub underneath and a dimple on top
    lid -= Pos(BTN_X, BTN_Y - 0.5, BODY_H + LID_T - 0.6) * Box(12, 12, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lid += Pos(BTN_X, BTN_Y - 2.0, BODY_H - 1.8) * Cylinder(1.6, 1.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lid += Pos(BTN_X, BTN_Y - 2.0, BODY_H + LID_T - 0.6) * Cylinder(3.5, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return lid


# =====================================================================
# CRADLE (shared by tape + clamp versions)
# =====================================================================
CR_Y0, CR_Y1 = -OUT_W / 2, OUT_W / 2
TAB_W, TAB_Y0, TAB_Y1 = 9.0, 4.0, OUT_W / 2 + 5.0     # latch cantilever (root low, lever sticks out top)


def cradle_core(curved_back=True):
    z_back = -DT_H - CR_BASE
    cr = rbox(CR_W, OUT_W, CR_BASE + DT_H, r=4.0, z0=z_back)
    if curved_back:
        # concave back that hugs a convex shell (cylinder, axis along Y)
        sag = SHELL_R - (SHELL_R ** 2 - (CR_W / 2) ** 2) ** 0.5
        cr += rbox(CR_W, OUT_W, sag + 0.01, r=4.0, z0=z_back - sag)
        cr -= Pos(0, 0, z_back - SHELL_R) * Rot(90, 0, 0) * Cylinder(SHELL_R, OUT_W + 2)
    # dovetail channel, open at the top, stop at the bottom
    ch = dovetail(DT_NARROW, DT_WIDE, DT_H, 0.0, DT_Y0 - TOL, CR_Y1 + 1, grow=TOL)
    cr -= ch
    # latch cantilever: U-slot through the back plate, pocket behind it so it can flex
    z0 = -DT_H - CR_BASE
    for sx in (-1, 1):
        cr -= Pos(sx * (TAB_W / 2 + 0.6), (TAB_Y0 + CR_Y1) / 2, z0 - 5) * Box(1.2, CR_Y1 - TAB_Y0, CR_BASE + 10,
                                                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    cr -= Pos(0, TAB_Y0 - 0.6, z0 - 5) * Box(TAB_W + 2.4, 1.2, CR_BASE + 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cr -= Pos(0, (TAB_Y0 + CR_Y1) / 2 + 1, z0 - 5) * Box(TAB_W + 2.4, CR_Y1 - TAB_Y0 + 2, 5 + 1.5,
                                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    # lever extension above the cradle (tab is 2.0 thick: from z0+1.5 to z0+3.5)
    cr += Pos(0, (CR_Y1 + TAB_Y1) / 2, z0 + 1.5) * Box(TAB_W, TAB_Y1 - CR_Y1, 2.0,
                                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
    cr += Pos(0, TAB_Y1 - 1.5, z0 + 3.5) * Box(TAB_W, 3.0, 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN))  # finger ridge
    # ramped bump on the tab: ramp faces up (pod arrives from above), steep face down
    by = NOTCH_Y
    bump = prism_yz([(by - 2.0, -DT_H), (by + 2.5, -DT_H), (by + 0.5, -DT_H + 1.0), (by - 2.0, -DT_H + 1.0)],
                    -3.5, 3.5)
    cr += bump
    return cr


def make_cradle_tape():
    return cradle_core(curved_back=True)


def make_cradle_clamp():
    cr = cradle_core(curved_back=False)
    z_back = -DT_H - CR_BASE
    arm_w = 28.0
    y_rim = CR_Y0 - CLAMP_DROP
    arm = Pos(0, (CR_Y0 + y_rim - 10) / 2 + 1, z_back) * Box(arm_w, CR_Y0 - y_rim + 10 + 2, CR_BASE,
                                                            align=(Align.CENTER, Align.CENTER, Align.MIN))
    arm = fillet(arm.edges().filter_by(Axis.Z), 3.0)
    cr += arm
    # screw boss block below the rim, two M3 clearance holes with counterbores (from outside)
    blk = Pos(0, y_rim - 5, z_back) * Box(arm_w, 10, CR_BASE + 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cr += blk
    for sx in (-1, 1):
        cr -= Pos(sx * 8, y_rim - 5, z_back - 1) * Cylinder(1.7, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        cr -= Pos(sx * 8, y_rim - 5, z_back + CR_BASE + 3.0 - 3.0) * Cylinder(3.0, 3.01,
                                                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    return cr


def make_clamp_inner():
    z_back = -DT_H - CR_BASE
    y_rim = CR_Y0 - CLAMP_DROP
    zp1 = z_back - SHELL_T
    plate = Pos(0, y_rim + 16, zp1 - 1.8) * Box(24, 32, 1.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = fillet(plate.edges().filter_by(Axis.Z), 3.0)
    blk_h = SHELL_T + 1.8 - 1.0
    blk = Pos(0, y_rim - 5, zp1 - 1.8) * Box(28, 10, blk_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = plate + blk
    for sx in (-1, 1):
        part -= Pos(sx * 8, y_rim - 5, zp1 - 3) * Cylinder(1.7, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        nut = extrude(Pos(sx * 8, y_rim - 5, zp1 - 1.8) * RegularPolygon(3.25, 6), amount=2.6)
        part -= nut
    return part


# =====================================================================
# ALCOHOL CHIN POD (bare MQ-3: ~20 mm base, 6 pins)
# =====================================================================
MQ_D, MQ_H = 20.6, 17.0


def make_alc_pod():
    """Cup for the sensor on top of a strap base. Base back is flat: VHB/velcro it inside a chin bar,
    or thread the chin strap through the base slot on open-face helmets."""
    od, h = MQ_D + 5.0, MQ_H + 5.0
    base_h = STRAP_T + 3.0
    base = Box(od + 4, STRAP_W + 4, base_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    base = fillet(base.edges().filter_by(Axis.Z), 2.0)
    base -= Pos(0, 0, 1.2) * Box(od + 6, STRAP_W, STRAP_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cup = Pos(0, 0, base_h) * Cylinder(od / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pod = base + cup
    z0 = base_h + 1.6
    pod -= Pos(0, 0, z0 + 4.0) * Cylinder(MQ_D / 2 + 0.3, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pod -= Pos(0, 0, z0) * Cylinder(MQ_D / 2 - 2.2, 4.01, align=(Align.CENTER, Align.CENTER, Align.MIN))  # pin well
    pod -= hole_x(4.2, 0, z0 + 2.0, 0, od / 2 + 1)                   # cable exit
    return pod


def make_alc_grille():
    od = MQ_D + 5.0
    g = Cylinder(od / 2, 1.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    g = fillet(g.edges().group_by(Axis.Z)[-1], 0.8)
    lip = Pos(0, 0, -2.0) * Cylinder(MQ_D / 2 + 0.3 - TOL, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lip -= Pos(0, 0, -2.0) * Cylinder(MQ_D / 2 - 1.2, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    g += lip
    for i in range(-3, 4):
        g -= Pos(i * 2.6, 0, 0) * Box(1.2, 15 - abs(i) * 1.6, 8)
    return g


# =====================================================================
# STRAP SLEEVES (Hall sensor + magnet)
# =====================================================================
STRAP_W, STRAP_T = 26.0, 2.6     # fits webbing up to 26 mm wide, 2.6 mm thick


def strap_sleeve(pocket):
    l, w, h = 16.0, STRAP_W + 4.0, STRAP_T + 4.0
    s = Box(l, w, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = fillet(s.edges().filter_by(Axis.X), 1.2)
    s -= Pos(0, 0, 1.4) * Box(l + 1, STRAP_W, STRAP_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= pocket
    return s


def make_hall_sleeve():
    # A3144 (UA package ~4.1 x 3.0 x 1.6), flat face down toward the strap, wires out the side
    pocket = Pos(0, 0, h_top() - 1.8) * Box(4.6, 3.6, 1.81, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pocket += Pos(0, -9, h_top() - 1.8) * Box(3.0, 16, 1.81, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return strap_sleeve(pocket)


def make_magnet_sleeve():
    pocket = Pos(0, 0, h_top() - 3.2) * Cylinder(5.15, 3.21, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return strap_sleeve(pocket)


def h_top():
    return STRAP_T + 4.0


# =====================================================================
if __name__ == "__main__":
    parts = {
        "pod_body": make_pod_body(),
        "pod_lid": make_pod_lid(),
        "cradle_tape": make_cradle_tape(),
        "cradle_clamp": make_cradle_clamp(),
        "clamp_inner": make_clamp_inner(),
        "alc_pod": make_alc_pod(),
        "alc_grille": make_alc_grille(),
        "hall_sleeve": make_hall_sleeve(),
        "magnet_sleeve": make_magnet_sleeve(),
    }
    for name, p in parts.items():
        bb = p.bounding_box()
        print(f"{name:14s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm  valid={p.is_valid}")
        export_stl(p, os.path.join(OUT, f"{name}.stl"))
        export_step(p, os.path.join(OUT, f"{name}.step"))
    print(f"pod outside: {OUT_L:.1f} x {OUT_W:.1f} x {POD_H:.1f} mm (+{DT_H + CR_BASE:.1f} cradle)")
