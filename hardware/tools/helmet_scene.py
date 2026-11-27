"""
Builds the "Helmate on a helmet" Blender scene.

  blender -b -P hardware/tools/helmet_scene.py -- <out.blend> [preview.png]

World axes (metres): rider faces -Y, +Z up, rider's LEFT side = +X.
The helmet is a generic full-face shape modelled here; the Helmate parts are the real STLs.
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROTO = os.path.join(HW, "enclosure", "proto", "out")
OUT_BLEND = ARGS[0] if ARGS else os.path.join(HW, "renders", "helmet", "helmate_on_helmet.blend")
PREVIEW = ARGS[1] if len(ARGS) > 1 else None
MM = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
C = bpy.context


# ---------------------------------------------------------------- helpers
def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


COL = {n: coll(n) for n in ["Helmet", "Helmate", "Cables", "Anchors", "Cutters"]}


def link(ob, cname):
    for c in ob.users_collection:
        c.objects.unlink(ob)
    COL[cname].objects.link(ob)
    return ob


def activate(ob):
    for o in C.view_layer.objects:
        o.select_set(False)
    C.view_layer.objects.active = ob
    ob.select_set(True)


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def ellipsoid(name, center, semi, seg=96, rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1.0, location=center)
    ob = C.active_object
    ob.name = name
    ob.scale = semi
    activate(ob)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob


def box(name, center, size, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center, rotation=rot)
    ob = C.active_object
    ob.name = name
    ob.scale = size
    activate(ob)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        m = ob.modifiers.new("bev", "BEVEL")
        m.width = bevel
        m.segments = 8
        apply_mods(ob)
    return ob


def boolean(target, cutter, op="DIFFERENCE"):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"
    if hasattr(m, "material_mode"):
        m.material_mode = "TRANSFER"
    apply_mods(target)


def remesh_smooth(ob, voxel=0.0025, smooth_iters=12):
    m = ob.modifiers.new("r", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    s = ob.modifiers.new("s", "SMOOTH")
    s.factor = 0.8
    s.iterations = smooth_iters
    apply_mods(ob)


def shade_smooth(ob, angle=40):
    activate(ob)
    bpy.ops.object.shade_smooth()
    if hasattr(ob.data, "use_auto_smooth"):
        ob.data.use_auto_smooth = True
        ob.data.auto_smooth_angle = math.radians(angle)


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, transmission=0.0, alpha=1.0, emit=None, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    for key in ("Coat Weight", "Clearcoat"):
        if key in p.inputs:
            p.inputs[key].default_value = coat
            break
    for key in ("Transmission Weight", "Transmission"):
        if key in p.inputs:
            p.inputs[key].default_value = transmission
            break
    p.inputs["IOR"].default_value = ior
    p.inputs["Alpha"].default_value = alpha
    if emit:
        for key in ("Emission Color", "Emission"):
            if key in p.inputs:
                p.inputs[key].default_value = (*emit[0], 1)
                break
        if "Emission Strength" in p.inputs:
            p.inputs["Emission Strength"].default_value = emit[1]
    if alpha < 1:
        m.blend_method = "BLEND"
    return m


def set_mat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def import_stl(path, name):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    ob = [o for o in bpy.data.objects if o not in before][0]
    ob.name = name
    return ob


def frame_matrix(origin, x, y, z):
    R = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation(origin) @ R @ Matrix.Scale(MM, 4)


def bvh_of(ob):
    dg = C.evaluated_depsgraph_get()
    return BVHTree.FromObject(ob, dg)


def anchor(name, loc, inside=False):
    e = bpy.data.objects.new("A_" + name, None)
    e.location = loc
    e["inside"] = inside
    COL["Anchors"].objects.link(e)
    return e


# ---------------------------------------------------------------- materials
M = {
    "paint": mat("Shell paint", (0.80, 0.81, 0.83), rough=0.28, coat=1.0),
    "trim": mat("Rubber trim", (0.012, 0.012, 0.013), rough=0.55),
    "liner": mat("Liner fabric", (0.03, 0.032, 0.036), rough=0.92),
    "visor": mat("Visor smoke", (0.04, 0.045, 0.05), rough=0.07, transmission=1.0, ior=1.5),
    "strap": mat("Strap webbing", (0.02, 0.02, 0.022), rough=0.85),
    "metal": mat("Ring metal", (0.55, 0.56, 0.58), rough=0.4, metal=1.0),
    "pod": mat("Pod PETG", (0.045, 0.048, 0.055), rough=0.42),
    "cradle": mat("Cradle orange", (0.95, 0.42, 0.05), rough=0.45),
    "grille": mat("Grille", (0.55, 0.58, 0.62), rough=0.35),
    "fsr": mat("FSR film", (0.72, 0.55, 0.28), rough=0.4),
    "magnet": mat("Magnet sleeve", (0.15, 0.42, 0.85), rough=0.4),
    # cable colours match the HTML legend
    "c_fsr": mat("Cable FSR", (1.0, 0.62, 0.10), rough=0.4),
    "c_hall": mat("Cable HALL", (0.10, 0.75, 1.0), rough=0.4),
    "c_alc": mat("Cable ALC", (0.95, 0.25, 0.55), rough=0.4),
}

# ---------------------------------------------------------------- helmet shell
# Outer form: one superellipsoid, chin swept forward/down and narrowed. Same function makes the cavity.
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def helmet_form(name, center, semi, p=2.4, chin=(0.046, 0.026, 0.05), seg=160, rings=120):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1.0)
    ob = C.active_object
    ob.name = name
    cy, cz, cx = chin
    for v in ob.data.vertices:
        u = v.co.normalized()
        s = 1.0 / ((abs(u.x / semi[0]) ** p + abs(u.y / semi[1]) ** p + abs(u.z / semi[2]) ** p) ** (1 / p))
        P = u * s
        w = smoothstep(0.05, 0.8, -u.y) * smoothstep(-0.05, -0.7, u.z)
        P.y -= cy * w
        P.z -= cz * w
        P.x *= 1 - cx * w
        # tuck the lower back in slightly toward the neck
        wb = smoothstep(0.1, 0.9, u.y) * smoothstep(-0.2, -0.9, u.z)
        P.y -= 0.012 * wb
        v.co = P + Vector(center)
    sm = ob.modifiers.new("s", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = 4
    apply_mods(ob)
    return ob


DOME_C, DOME_S = Vector((0, 0.010, -0.014)), Vector((0.130, 0.158, 0.158))
CAV_C, CAV_S = Vector((0, 0.013, -0.006)), Vector((0.103, 0.130, 0.137))
outer = helmet_form("Shell", DOME_C, DOME_S)
outer_proxy = outer.copy()
outer_proxy.data = outer.data.copy()
outer_proxy.name = "outer_proxy"
COL["Cutters"].objects.link(outer_proxy)
set_mat(outer, M["paint"])

cav = helmet_form("cavity", CAV_C, CAV_S, p=2.3, chin=(0.036, 0.024, 0.05))
cav_proxy = cav.copy()
cav_proxy.data = cav.data.copy()
cav_proxy.name = "cavity_proxy"
COL["Cutters"].objects.link(cav_proxy)
set_mat(cav, M["liner"])
link(cav, "Cutters")

# Bottom opening: plane tilted so the chin is lower than the back
RIM_BACK_Z, RIM_FRONT_Z = -0.118, -0.178
tilt = math.atan2(RIM_BACK_Z - RIM_FRONT_Z, 0.34)
BOT_CZ = -0.150 - 0.25
bottom = box("bottom_cut", (0, 0, BOT_CZ), (0.6, 0.8, 0.5), rot=(tilt, 0, 0))
set_mat(bottom, M["trim"])
link(bottom, "Cutters")


def rim_z(y):
    """z of the bottom cut plane at a given y."""
    yl = (y + 0.25 * math.sin(tilt)) / math.cos(tilt)
    return BOT_CZ + yl * math.sin(tilt) + 0.25 * math.cos(tilt)


# Eye port
EYE = box("eyeport", (0, -0.16, -0.004), (0.20, 0.2, 0.086), bevel=0.022)
set_mat(EYE, M["trim"])
link(EYE, "Cutters")

boolean(outer, cav, "DIFFERENCE")
boolean(outer, bottom, "DIFFERENCE")
boolean(outer, EYE, "DIFFERENCE")


def assign_cut_materials(ob):
    """Booleans don't reliably carry cutter materials over, so classify faces by which cutter made them."""
    dg = C.evaluated_depsgraph_get()
    bv = {"liner": BVHTree.FromObject(cav_proxy, dg), "bot": BVHTree.FromObject(bottom, dg),
          "eye": BVHTree.FromObject(EYE, dg)}
    ob.data.materials.clear()
    for m in (M["paint"], M["liner"], M["trim"]):
        ob.data.materials.append(m)
    mw = ob.matrix_world
    for f in ob.data.polygons:
        c = mw @ f.center
        idx = 0
        if bv["liner"].find_nearest(c)[3] < 0.0012:
            idx = 1
        elif bv["bot"].find_nearest(c)[3] < 0.0012 or bv["eye"].find_nearest(c)[3] < 0.0012:
            idx = 2
        f.material_index = idx


assign_cut_materials(outer)
shade_smooth(outer, 50)
link(outer, "Helmet")

# Visor: a slightly larger copy of the outer form, clipped to the eye port area
vis = outer_proxy.copy()
vis.data = outer_proxy.data.copy()
vis.name = "Visor"
COL["Helmet"].objects.link(vis)
for c in list(vis.users_collection):
    if c.name == "Cutters":
        c.objects.unlink(vis)
vis.scale = (1.012, 1.012, 1.012)
activate(vis)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
vclip = box("visor_clip", (0, -0.16, 0.0), (0.236, 0.2, 0.112), bevel=0.03)
link(vclip, "Cutters")
boolean(vis, vclip, "INTERSECT")
vcav = helmet_form("visor_inner", DOME_C, DOME_S * 0.992)
link(vcav, "Cutters")
boolean(vis, vcav, "DIFFERENCE")
set_mat(vis, M["visor"])
shade_smooth(vis, 60)

dg = C.evaluated_depsgraph_get()
BV_OUT = BVHTree.FromObject(outer_proxy, dg)
BV_IN = BVHTree.FromObject(cav_proxy, dg)


def pivot(side):
    sx = 1 if side == "L" else -1
    loc, nrm, idx, d = BV_OUT.ray_cast(Vector((sx * 0.4, -0.048, 0.0)), Vector((-sx, 0, 0)))
    nrm = nrm.normalized()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0175, depth=0.0035, vertices=64)
    pv = C.active_object
    pv.name = f"Visor pivot {side}"
    bev = pv.modifiers.new("bev", "BEVEL")
    bev.width = 0.0012
    bev.segments = 4
    apply_mods(pv)
    pv.matrix_world = Matrix.Translation(loc + nrm * 0.0008) @ nrm.to_track_quat("Z", "Y").to_matrix().to_4x4()
    set_mat(pv, M["trim"])
    shade_smooth(pv)
    link(pv, "Helmet")


def hit_outer(origin, direction):
    loc, nrm, idx, d = BV_OUT.ray_cast(Vector(origin), Vector(direction).normalized())
    return loc, nrm


def snap(p, bv, offset):
    loc, nrm, idx, d = bv.find_nearest(Vector(p))
    # normals of the proxy point outward; for the cavity "outward" = away from the head
    return loc + nrm * offset, nrm


pivot("L")
pivot("R")

# ---------------------------------------------------------------- Helmate pod on the left side
POD_Y, POD_Z, POD_TILT = 0.030, -0.085, math.radians(-12)   # behind the ear, intercom spot
hit, n = hit_outer((0.4, POD_Y, POD_Z), (-1, 0, 0))
n = n.normalized()
up = (Vector((0, 0, 1)) - n * n.z).normalized()
x_ax = up.cross(n).normalized()
# tilt the pod forward like an intercom
q = Matrix.Rotation(POD_TILT, 3, n)
x_ax, up = q @ x_ax, q @ up
CRADLE_GAP = 7.9 * MM    # cradle back sag + 1 mm VHB
pod_origin = hit + n * CRADLE_GAP
POD_M = frame_matrix(pod_origin, x_ax, up, n)


def pod_pt(x, y, z):
    return POD_M @ Vector((x, y, z))


for nm, f, m in (("Pod body", "pod_body.stl", M["pod"]), ("Pod lid", "pod_lid.stl", M["pod"]),
                 ("Cradle (tape)", "cradle_tape.stl", M["cradle"])):
    ob = import_stl(os.path.join(PROTO, f), nm)
    ob.matrix_world = POD_M
    set_mat(ob, m)
    shade_smooth(ob, 35)
    link(ob, "Helmate")

# clamp version, hidden by default (used for close-ups)
for nm, f in (("Cradle (clamp)", "cradle_clamp.stl"), ("Clamp inner plate", "clamp_inner.stl")):
    ob = import_stl(os.path.join(PROTO, f), nm)
    ob.matrix_world = POD_M
    set_mat(ob, M["cradle"])
    shade_smooth(ob, 35)
    link(ob, "Helmate")
    ob.hide_render = True
    ob.hide_viewport = True

POD_H = 24.4
anchor("pod", pod_pt(0, 0, POD_H))
anchor("button", pod_pt(14, 2, POD_H))
anchor("ports", pod_pt(4, -21.5, 18.2))
anchor("charge", pod_pt(-17.5, -21.5, 18.2))
anchor("cradle", pod_pt(0, 26, -4))

# ---------------------------------------------------------------- straps + buckle
BUCKLE = Vector((0.018, -0.083, -0.214))


def strap_path(side):
    sx = 1 if side == "L" else -1
    pts = [Vector((sx * 0.090, 0.012, -0.108)), Vector((sx * 0.084, -0.006, -0.150)),
           Vector((sx * 0.066, -0.032, -0.190)), Vector((sx * 0.040, -0.060, -0.212))]
    pts.append(BUCKLE + Vector((sx * 0.010, 0.004, 0.0)))
    return pts


def catmull(pts, n=12):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def ribbon(name, pts, width, thick, normal_fn, material):
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        nn = normal_fn(p)
        w = t.cross(nn).normalized()
        nn = w.cross(t).normalized()
        a = p + w * width / 2
        b = p - w * width / 2
        rows.append([bm.verts.new(a), bm.verts.new(b), bm.verts.new(b + nn * thick), bm.verts.new(a + nn * thick)])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    set_mat(ob, material)
    return ob


STRAP_AXIS = Vector((0, -0.03, -0.12))
strap_pts = {}
for side in ("L", "R"):
    pts = catmull(strap_path(side), 10)
    strap_pts[side] = pts
    ob = ribbon(f"Chin strap {side}", pts, 0.022, 0.0016,
                lambda p: (p - Vector((0, p.y * 0.3 - 0.02, -0.10))).normalized(), M["strap"])
    COL["Helmet"].objects.link(ob)
    shade_smooth(ob, 30)

# D-rings
for i in range(2):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.010, minor_radius=0.0014, location=BUCKLE + Vector((0.0, 0.0, -0.002 * i)),
                                     rotation=(math.radians(70), 0, math.radians(-30)))
    r = C.active_object
    r.name = f"D-ring {i + 1}"
    set_mat(r, M["metal"])
    shade_smooth(r)
    link(r, "Helmet")


def place_on_strap(name, stl, side, frac, material, lift=0.0016):
    pts = strap_pts[side]
    i = int(frac * (len(pts) - 1))
    p = pts[i]
    t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
    nn = (p - Vector((0, p.y * 0.3 - 0.02, -0.10))).normalized()
    w = t.cross(nn).normalized()
    nn = w.cross(t).normalized()
    # sleeve: X along strap, Y across strap, Z away from the jaw. Slot sits 1.4 mm above sleeve floor.
    origin = p - nn * (1.4 * MM)
    ob = import_stl(os.path.join(PROTO, stl), name)
    ob.matrix_world = frame_matrix(origin, t, w, nn)
    set_mat(ob, material)
    shade_smooth(ob, 35)
    link(ob, "Helmate")
    return p + nn * (6.6 * MM)


hall_at = place_on_strap("Hall sleeve", "hall_sleeve.stl", "L", 0.84, M["pod"])
mag_at = place_on_strap("Magnet sleeve", "magnet_sleeve.stl", "R", 0.84, M["magnet"])
anchor("hall", hall_at)
anchor("magnet", mag_at)

# ---------------------------------------------------------------- chin pod (MQ-3) inside the chin bar
src = Vector((0, -0.02, -0.088))
loc, nrm, idx, d = BV_IN.ray_cast(src, Vector((0, -1, 0)))
inward = (-nrm).normalized()            # cavity normals point outward from the face -> flip
cx = Vector((1, 0, 0))
cy = inward.cross(cx).normalized()
cx = cy.cross(inward).normalized()
chin_origin = loc + inward * (1.0 * MM)
CH_M = frame_matrix(chin_origin, cx, cy, inward)
for nm, f, m, zoff in (("Chin pod", "alc_pod.stl", M["pod"], 0), ("Chin pod grille", "alc_grille.stl", M["grille"], 27.6)):
    ob = import_stl(os.path.join(PROTO, f), nm)
    ob.matrix_world = CH_M @ Matrix.Translation((0, 0, zoff))
    set_mat(ob, m)
    shade_smooth(ob, 35)
    link(ob, "Helmate")
anchor("chin", CH_M @ Vector((0, 0, 29)), inside=True)

# ---------------------------------------------------------------- FSR under the crown pad
top_src = Vector((0, 0.015, 0.0))
loc, nrm, idx, d = BV_IN.ray_cast(top_src, Vector((0, 0, 1)))
down = (-nrm).normalized()
fx = Vector((1, 0, 0))
fy = down.cross(fx).normalized()
fx = fy.cross(down).normalized()
fsr_c = loc + down * (6 * MM)   # sits under the ~6 mm comfort pad
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, radius=9.5 * MM, segments=48)
geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
bmesh.ops.translate(bm, verts=[v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)], vec=(0, 0, 0.45 * MM))
me = bpy.data.meshes.new("FSR")
bm.to_mesh(me)
fsr = bpy.data.objects.new("FSR 402", me)
fsr.matrix_world = Matrix.Translation(fsr_c) @ Matrix((fx, fy, -down)).transposed().to_4x4()
set_mat(fsr, M["fsr"])
COL["Helmate"].objects.link(fsr)
tail = box("FSR tail", (0, 0, 0), (0.007, 0.034, 0.0004))
tail.matrix_world = Matrix.Translation(fsr_c + fy * 0.026) @ Matrix((fx, fy, -down)).transposed().to_4x4()
set_mat(tail, M["fsr"])
link(tail, "Helmate")
anchor("fsr", fsr_c, inside=True)

# comfort/crown pad (shows where the FSR hides)
pad = ellipsoid("Crown pad", CAV_C, CAV_S * 0.965, 64, 48)
pclip = box("pad_clip", (0, 0.02, 0.10), (0.16, 0.2, 0.08))
link(pclip, "Cutters")
boolean(pad, pclip, "INTERSECT")
pin = ellipsoid("pad_in", CAV_C, CAV_S * 0.92, 64, 48)
link(pin, "Cutters")
boolean(pad, pin, "DIFFERENCE")
set_mat(pad, M["liner"])
shade_smooth(pad)
link(pad, "Helmet")
pad["inner"] = True

# ---------------------------------------------------------------- cables
def densify(pts, step=0.004):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((b - a).length / step))
        for k in range(1, n + 1):
            out.append(a.lerp(b, k / n))
    return out


def smooth(pts, it=6):
    p = list(pts)
    for _ in range(it):
        p = [p[0]] + [(p[i - 1] + 2 * p[i] + p[i + 1]) / 4 for i in range(1, len(p) - 1)] + [p[-1]]
    return p


RIM_IN_OFF, RIM_OUT_OFF = -0.0026, 0.0026


def route(port, inner_path, end, lead_out=0.006):
    """port (outside, on pod bottom) -> down the shell -> wrap under the rim edge -> inner_path on the liner -> end."""
    pts = [port, port + (-up) * lead_out]
    p = pts[-1]
    # 1. bend toward the shell, then down the outside to 3 mm above the rim.
    #    Project sideways (keeps height) instead of nearest-point (which drags points upward).
    rz = rim_z(p.y)

    def on_shell(q):
        loc, nrm, i, d = BV_OUT.ray_cast(Vector((q.x + 0.25, q.y, q.z)), Vector((-1, 0, 0)))
        return loc + nrm.normalized() * RIM_OUT_OFF

    first = on_shell(Vector((p.x, p.y, p.z - 0.010)))
    bend = Vector(((p.x + first.x) / 2, (p.y + first.y) / 2, p.z - 0.007))
    seg = densify([Vector((p.x, p.y, z)) for z in (p.z - 0.010, rz + 0.003)], 0.003)
    pts += densify([p, bend], 0.003)[1:] + [on_shell(q) for q in seg]
    q_out = pts[-1]
    # 2. explicit wrap under the edge: out -> below rim -> across -> inside
    rz = rim_z(pts[-1].y)
    q_in, _ = snap(Vector((q_out.x * 0.80, q_out.y, rz + 0.004)), BV_IN, RIM_IN_OFF)
    below = rz - 0.0045
    wrap = [Vector((q_out.x + 0.0005, q_out.y, rz - 0.001)),
            Vector((q_out.x - 0.002, q_out.y, below)),
            Vector(((q_out.x + q_in.x) / 2, q_out.y, below - 0.001)),
            Vector((q_in.x + 0.002, q_in.y, below)),
            Vector((q_in.x - 0.0005, q_in.y, rz - 0.001)), q_in]
    pts += densify([q_out] + wrap, 0.003)[1:]
    # 3. along the liner
    if inner_path:
        seg = densify([q_in] + [Vector(v) for v in inner_path], 0.003)
        seg = [snap(v, BV_IN, RIM_IN_OFF)[0] for v in seg]
        pts += seg[1:]
    pts += densify([pts[-1], Vector(end)], 0.003)[1:]
    pts = densify(pts, 0.003)
    return smooth(pts, 7)


def cable(name, pts, material, r=1.4 * MM):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, v in enumerate(pts):
        sp.points[i].co = (*v, 1)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(material)
    COL["Cables"].objects.link(ob)
    return sum((b - a).length for a, b in zip(pts, pts[1:]))


lengths = {}
p_fsr, p_hall, p_alc = pod_pt(-4, -21.5, 18.2), pod_pt(7, -21.5, 18.2), pod_pt(20, -21.5, 18.2)
# FSR: up the inside of the left side to the crown
lengths["fsr"] = cable("Cable FSR", route(p_fsr, [(0.09, 0.03, -0.02), (0.07, 0.03, 0.08), (0.03, 0.03, 0.12)],
                                          fsr_c + fy * 0.042), M["c_fsr"])
# HALL: under the rim, then down along the left strap to the sleeve
hp = [v + Vector((0, 0, 0.003)) for v in strap_pts["L"][2:int(0.84 * (len(strap_pts['L']) - 1)) - 1]]
route_h = route(p_hall, [], hp[0])
route_h = smooth(route_h[:-1] + hp + [hall_at], 3)
lengths["hall"] = cable("Cable HALL", route_h, M["c_hall"])
# ALC: forward along the inside of the cheek to the chin pod
lengths["alc"] = cable("Cable ALC", route(p_alc, [(0.085, -0.02, -0.11), (0.06, -0.09, -0.115)],
                                          CH_M @ Vector((12, 0, 6))), M["c_alc"])
anchor("rim", Vector((p_hall.x, p_hall.y, rim_z(p_hall.y))))

# Alternative FSR spot, measured only (no cable drawn): under the left cheek pad, next to the pod.
cheek_pt, _ = snap(Vector((0.10, -0.035, -0.075)), BV_IN, -0.006)
alt = route(p_fsr, [(0.095, 0.0, -0.10)], cheek_pt)
lengths["fsr_cheek"] = sum((b - a).length for a, b in zip(alt, alt[1:]))

# ---------------------------------------------------------------- export positions + lengths
info = {"cable_length_cm": {k: round(v * 100, 1) for k, v in lengths.items()},
        "pod_center": list(pod_pt(0, 0, 12)), "helmet_center": [0, 0, -0.03]}
json.dump(info, open(os.path.splitext(OUT_BLEND)[0] + "_info.json", "w"), indent=1)
print("CABLES_CM", info["cable_length_cm"])

for o in COL["Cutters"].objects:
    o.hide_render = True
    o.hide_viewport = True

# ---------------------------------------------------------------- render setup
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU not available:", e)
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transparent_max_bounces = 16
scene.render.film_transparent = True
names = [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
scene.view_settings.view_transform = "AgX" if "AgX" in names else "Filmic"
scene.view_settings.look = "AgX - Medium High Contrast" if "AgX" in names else "None"

world = bpy.data.worlds.new("Studio")
scene.world = world
world.use_nodes = True
nt = world.node_tree
# studio gradient: dark floor, soft horizon, bright ceiling -> clean band reflections, no hot spots
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")
cr = ramp.color_ramp
cr.elements[0].position, cr.elements[0].color = 0.42, (0.012, 0.013, 0.016, 1)
cr.elements[1].position, cr.elements[1].color = 1.0, (0.95, 0.97, 1.0, 1)
e = cr.elements.new(0.52)
e.color = (0.16, 0.17, 0.19, 1)
e = cr.elements.new(0.62)
e.color = (0.07, 0.075, 0.085, 1)
mz = nt.nodes.new("ShaderNodeMath")
mz.operation = "MULTIPLY_ADD"
mz.inputs[1].default_value = 0.5
mz.inputs[2].default_value = 0.5
nt.links.new(sep.outputs["Z"], mz.inputs[0])
nt.links.new(mz.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], nt.nodes["Background"].inputs[0])
nt.nodes["Background"].inputs[1].default_value = 0.9

TARGET = Vector((0, 0, -0.035))
rig = bpy.data.objects.new("CamRig", None)
rig.location = TARGET
scene.collection.objects.link(rig)
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
cam.data.lens = 85
cam.data.clip_start = 0.01
cam.parent = rig
scene.collection.objects.link(cam)
scene.camera = cam
DIST = 1.05


def set_view(az_deg, el_deg, dist=DIST, target=TARGET):
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    rig.location = target
    cam.location = d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


# lights parented to the camera rig so lighting stays consistent while orbiting
def area(name, loc, energy, size, color=(1, 1, 1), size_y=None, glossy=True):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    L.data.energy = energy
    L.data.size = size
    if size_y:
        L.data.shape = "RECTANGLE"
        L.data.size_y = size_y
    L.data.color = color
    L.location = loc
    L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(L)
    L.visible_glossy = glossy
    return L


area("Key", (-0.9, -0.9, 1.0), 60, 1.6, size_y=0.45, glossy=False)
area("Fill", (1.0, -0.5, 0.3), 14, 1.0, (0.85, 0.9, 1.0), glossy=False)
area("Strip", (0.0, -0.55, 1.05), 22, 2.4, size_y=0.10)
area("Rim", (0.2, 1.1, 0.6), 50, 1.4, size_y=0.25)
area("Under", (0.0, -0.3, -0.9), 6, 1.0)

scene["set_view"] = "see tools/render_helmet.py"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
set_view(55, 12)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("SAVED", OUT_BLEND)

if PREVIEW:
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print("RENDERED", PREVIEW)
