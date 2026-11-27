"""
Helmate production pod, concept v1 (injection-molded PC/ABS look).

Sized around HB-1 (about 36 x 26 mm board, ESP32-C3-MINI-1) and an 800 mAh 603040 LiPo.
Uses the SAME dovetail as the prototype, so prototype cradles still fit.

Run: python hardware/enclosure/production/helmate_pod_v1.py
"""
from build123d import *
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "proto"))
import helmate_pod as proto

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

L, W, H = 50.0, 38.0, 15.0     # outside: 50 x 38 x 15 mm (prototype: 63 x 43 x 24)
WALL = 1.6


def shell():
    b = Box(L, W, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    b = fillet(b.edges().filter_by(Axis.Z), 9.0)
    b = fillet(b.edges().group_by(Axis.Z)[-1], 4.0)
    b = fillet(b.edges().group_by(Axis.Z)[0], 1.2)
    # gentle dome on the outer face
    dome = Pos(0, 0, H - 140) * Sphere(140 + 0.0)
    b = b & (dome + Pos(0, 0, -50) * Box(200, 200, 50 + H - 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return b


def make_body():
    b = shell()
    # parting line groove (top cover / base split)
    groove = Box(L + 2, W + 2, 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    inner = fillet(Box(L - 0.8, W - 0.8, 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN)).edges().filter_by(Axis.Z), 8.6)
    b -= Pos(0, 0, 5.0) * (groove - inner)
    # button: ring recess + cap
    bx, by = 9.0, 2.0
    ztop = H
    b -= Pos(bx, by, ztop - 1.0) * Cylinder(6.0, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cap = Pos(bx, by, ztop - 1.0) * Cylinder(5.0, 0.9, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cap = fillet(cap.edges().group_by(Axis.Z)[-1], 0.4)
    # LED light pipe
    b -= Pos(-12.0, 8.0, ztop - 2) * Cylinder(0.9, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # bottom face: USB-C + three JST-SH ports
    y0 = -W / 2
    b -= Pos(-12, y0, 4.8) * Box(9.4, 6, 3.4)
    for x, n in ((3, 2), (10, 3), (18, 6)):
        b -= Pos(x, y0, 4.0) * Box(n * 1.0 + 3.2, 6, 2.6)
    # dovetail tongue (same as prototype, shortened)
    tongue = proto.dovetail(proto.DT_NARROW, proto.DT_WIDE, proto.DT_H, 0.0, -W / 2 + 2.0, W / 2 - 1.0)
    tongue -= Pos(0, W / 2 - 7.0, -proto.DT_H) * Box(9, 5, 2.4)
    return b + tongue, cap


def make_chin_pod():
    """SPEC 110-202 (20 x 20 x 3) + LMP91000 board: 26 x 26 x 8 mm puck."""
    p = Box(26, 26, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    p = fillet(p.edges().filter_by(Axis.Z), 6.0)
    p = fillet(p.edges().group_by(Axis.Z)[-1], 2.5)
    for i in range(-3, 4):
        p -= Pos(i * 2.4, 0, 7.4) * Box(1.0, 14 - abs(i) * 2.2, 2)
    p -= Pos(0, -13, 3) * Box(3.5, 4, 2.4)
    return p


if __name__ == "__main__":
    body, cap = make_body()
    chin = make_chin_pod()
    for n, prt in (("pod_body", body), ("pod_button", cap), ("chin_pod", chin)):
        bb = prt.bounding_box()
        print(f"{n:11s} {bb.size.X:5.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f}  valid={prt.is_valid}")
        export_stl(prt, os.path.join(OUT, f"{n}.stl"))
        export_step(prt, os.path.join(OUT, f"{n}.step"))
