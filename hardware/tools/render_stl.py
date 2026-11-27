"""
Headless Blender renderer for STL parts.

  blender -b -P hardware/tools/render_stl.py -- scene.json

scene.json:
{
  "out": "path.png", "res": [1600, 1100], "samples": 48,
  "camera": {"loc": [x,y,z], "target": [x,y,z], "lens": 50},
  "parts": [{"stl": "a.stl", "color": [r,g,b], "offset": [x,y,z], "rot": [rx,ry,rz], "rough": 0.5}]
}
Units in the STL are mm; the scene works in mm too (scaled down 1:1000 to metres).
"""
import bpy, json, sys, math
from mathutils import Vector

cfg = json.load(open(sys.argv[sys.argv.index("--") + 1]))
S = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = cfg.get("samples", 48)
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = cfg.get("res", [1600, 1100])
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = cfg.get("bg", [0.035, 0.04, 0.05, 1])
bg.inputs[1].default_value = cfg.get("bg_strength", 0.15)


def mat(color, rough=0.5, metal=0.0, name="m"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    return m


def import_stl(path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    return [o for o in bpy.data.objects if o not in before][0]


lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for i, p in enumerate(cfg["parts"]):
    ob = import_stl(p["stl"])
    ob.scale = (S, S, S)
    r = p.get("rot", [0, 0, 0])
    ob.rotation_euler = [math.radians(a) for a in r]
    ob.location = [v * S for v in p.get("offset", [0, 0, 0])]
    ob.data.materials.append(mat(p.get("color", [0.8, 0.8, 0.8]), p.get("rough", 0.5), p.get("metal", 0.0), f"m{i}"))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    if hasattr(ob.data, "use_auto_smooth"):
        ob.data.use_auto_smooth = True
        ob.data.auto_smooth_angle = math.radians(35)
    ob.select_set(False)
    bpy.context.view_layer.update()
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))

# ground plane
if cfg.get("ground", True):
    bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, lo.z - 0.0005))
    g = bpy.context.active_object
    g.data.materials.append(mat(cfg.get("ground_color", [0.05, 0.055, 0.065]), 0.8, name="ground"))

cam_cfg = cfg["camera"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.location = [v * S for v in cam_cfg["loc"]]
cam.data.lens = cam_cfg.get("lens", 50)
cam.data.clip_start = 0.001
tgt = Vector([v * S for v in cam_cfg.get("target", list((lo + hi) / 2 / S))])
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

for loc, energy, size in cfg.get("lights", [[[-0.25, -0.3, 0.45], 14, 0.25], [[0.35, -0.1, 0.25], 5, 0.2], [[0.0, 0.4, 0.3], 7, 0.3]]):
    L = bpy.data.objects.new("l", bpy.data.lights.new("l", "AREA"))
    L.data.energy = energy
    L.data.size = size
    L.location = loc
    L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(L)

scene.render.filepath = cfg["out"]
bpy.ops.render.render(write_still=True)
print("RENDERED", cfg["out"])
