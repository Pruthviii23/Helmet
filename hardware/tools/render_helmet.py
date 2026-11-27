"""
Render the helmet scene for the interactive viewer.

  blender -b helmate_on_helmet.blend -P render_helmet.py -- <outdir> <mode> [opts]

mode:
  review  : a handful of views at low res -> <outdir>/review_*.png
  turn    : full turntable, all variants -> <outdir>/raw/<variant>_e<row>_a<az>.png + hotspots.json
  stills  : close-up shots -> <outdir>/stills/*.png
opts (key=value): res=1600x1200 samples=48 az_step=10 els=-15,10,35 variants=outside,xray only=<variant>
"""
import bpy, sys, os, math, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

args = sys.argv[sys.argv.index("--") + 1:]
OUT, MODE = args[0], args[1]
opt = dict(a.split("=", 1) for a in args[2:])
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
cam = scene.camera
rig = cam.parent
W, H = map(int, opt.get("res", "1600x1200").split("x"))
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.cycles.samples = int(opt.get("samples", 48))
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"

COLS = {c.name: c for c in bpy.data.collections}
DIST = float(opt.get("dist", 1.55))
TARGET = Vector((0, 0.0, -0.045))


def set_view(az_deg, el_deg, dist=DIST, target=TARGET, lens=85):
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    rig.location = target
    cam.location = d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


# ---------------------------------------------------------------- variants
def ghost(name, color, alpha, rough=0.2):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Alpha"].default_value = alpha
    for key in ("Coat Weight", "Clearcoat"):
        if key in p.inputs:
            p.inputs[key].default_value = 0.0
    for key in ("Transmission Weight", "Transmission"):
        if key in p.inputs:
            p.inputs[key].default_value = 0.0
    m.blend_method = "BLEND"
    return m


ORIG = {}
for ob in COLS["Helmet"].objects:
    if ob.type == "MESH":
        ORIG[ob.name] = [s.material for s in ob.material_slots]
def holo(name, color, edge_strength, face_alpha):
    """Glass-outline look: transparent face-on, glowing at grazing angles."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeMath")
    ramp.operation = "POWER"
    ramp.inputs[1].default_value = 2.2
    nt.links.new(lw.outputs["Facing"], ramp.inputs[0])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "ADD"
    fac.use_clamp = True
    fac.inputs[1].default_value = face_alpha
    nt.links.new(ramp.outputs[0], fac.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = edge_strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND"
    return m


X_SHELL = holo("X shell", (0.55, 0.75, 1.0), 1.1, 0.03)
X_DARK = holo("X liner", (0.35, 0.45, 0.6), 0.35, 0.0)
X_STRAP = ghost("X strap", (0.03, 0.03, 0.035), 0.55)


def variant(v):
    for ob in COLS["Helmet"].objects:
        if ob.type != "MESH":
            continue
        for i, s in enumerate(ob.material_slots):
            orig = ORIG[ob.name][i]
            if v == "xray":
                if orig and orig.name.startswith("Shell paint"):
                    s.material = X_SHELL
                elif orig and orig.name.startswith("Strap"):
                    s.material = X_STRAP
                elif orig and orig.name.startswith("Ring"):
                    s.material = orig
                else:
                    s.material = X_DARK
            else:
                s.material = orig


# ---------------------------------------------------------------- hotspots
ANCH = [o for o in COLS["Anchors"].objects]
HELMET_OBS = {o.name for o in COLS["Helmet"].objects}


def visible(p, skip_helmet):
    dg = bpy.context.evaluated_depsgraph_get()
    o = cam.matrix_world.translation.copy()
    d = (p - o)
    dist = d.length
    d.normalize()
    start = o
    travelled = 0.0
    for _ in range(12):
        hit, loc, nrm, idx, ob, mtx = scene.ray_cast(dg, start, d, distance=dist - travelled)
        if not hit:
            return True
        t = (loc - o).length
        if t >= dist - 0.006:
            return True
        if skip_helmet and ob.name in HELMET_OBS:
            travelled = t + 0.0005
            start = o + d * travelled
            continue
        # tolerance: hitting the anchored part itself close to the anchor counts as visible
        if (loc - p).length < 0.012:
            return True
        return False
    return True


def hotspots():
    out = {}
    for a in ANCH:
        p = a.matrix_world.translation
        v = world_to_camera_view(scene, cam, p)
        name = a.name[2:]
        out[name] = [round(v.x, 4), round(1 - v.y, 4), int(visible(p, False)), int(visible(p, True))]
    return out


def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- modes
if MODE == "review":
    views = [("outside", 55, 12), ("outside", 90, 5), ("outside", 140, 15), ("outside", 0, 8),
             ("outside", 60, -20), ("xray", 55, 12), ("xray", 110, 20), ("xray", 300, 10)]
    for v, az, el in views:
        variant(v)
        set_view(az, el)
        render(os.path.join(OUT, f"review_{v}_a{az}_e{el}.png"))
    print("REVIEW_DONE")

elif MODE == "turn":
    step = int(opt.get("az_step", 10))
    els = [int(e) for e in opt.get("els", "-15,10,35").split(",")]
    variants = opt.get("variants", "outside,xray").split(",")
    raw = os.path.join(OUT, "raw")
    os.makedirs(raw, exist_ok=True)
    hs_path = os.path.join(OUT, "hotspots.json")
    hs = json.load(open(hs_path)) if os.path.exists(hs_path) else {}
    hs.update({"az_step": step, "els": els, "res": [W, H]})
    frames = hs.setdefault("frames", {})
    for v in variants:
        variant(v)
        for ei, el in enumerate(els):
            for az in range(0, 360, step):
                key = f"e{ei}_a{az:03d}"
                path = os.path.join(raw, f"{v}_{key}.png")
                set_view(az, el)
                if v == variants[0] or key not in frames:
                    frames[key] = hotspots()
                if not os.path.exists(path):
                    render(path)
                json.dump(hs, open(hs_path, "w"))
                print("FRAME", v, key, flush=True)
    print("TURN_DONE")

elif MODE == "stills":
    sd = os.path.join(OUT, "stills")
    os.makedirs(sd, exist_ok=True)
    only = opt.get("only", "")
    A = {a.name[2:]: a.matrix_world.translation.copy() for a in ANCH}
    obj = bpy.data.objects

    def show(name, on):
        o = obj.get(name)
        if o:
            o.hide_render = not on

    def cut_right_half(on):
        """Cutaway: hide the rider's right half (x < 0) of every helmet part."""
        cutter = obj.get("cutaway_box")
        if cutter is None:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.25, 0, 0))
            cutter = bpy.context.active_object
            cutter.name = "cutaway_box"
            cutter.scale = (0.5 - 0.0004, 1.0, 1.0)
            cutter.hide_render = True
        for o in COLS["Helmet"].objects:
            if o.type != "MESH":
                continue
            m = o.modifiers.get("cutaway")
            if on and not m:
                m = o.modifiers.new("cutaway", "BOOLEAN")
                m.operation = "DIFFERENCE"
                m.object = cutter
                m.solver = "EXACT"
            if m:
                m.show_render = on

    def shot(name, v, az, el, target, dist, lens=85):
        if only and name not in only.split(","):
            return
        variant(v)
        set_view(az, el, dist=dist, target=target, lens=lens)
        render(os.path.join(sd, f"{name}.png"))

    pod_c = (A["pod"] + A["ports"]) / 2
    # 1. pod close-up, tape cradle
    shot("pod_closeup", "outside", 78, 6, pod_c, 0.42)
    # 2. clamp version
    show("Cradle (tape)", False); show("Cradle (clamp)", True); show("Clamp inner plate", True)
    shot("clamp_outside", "outside", 70, -8, pod_c + Vector((0, 0, -0.02)), 0.5)
    shot("clamp_xray", "xray", 110, 4, pod_c + Vector((0, 0, -0.02)), 0.5)
    show("Cradle (tape)", True); show("Cradle (clamp)", False); show("Clamp inner plate", False)
    # 3. cutaway: look from the right at the inside of the left half
    cut_right_half(True)
    shot("cutaway", "outside", 262, 6, Vector((0.02, -0.01, -0.04)), 1.25)
    shot("cutaway_chin", "outside", 238, -4, A["chin"], 0.55)
    show("Crown pad", False)
    shot("cutaway_crown", "outside", 245, -32, A["fsr"] + Vector((0.0, 0.0, -0.035)), 0.62)
    show("Crown pad", True)
    cut_right_half(False)
    # 4. strap sensors from below
    shot("strap_sensors", "outside", 15, -42, (A["hall"] + A["magnet"]) / 2, 0.55)
    print("STILLS_DONE")
