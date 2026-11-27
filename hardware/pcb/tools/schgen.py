"""
Generate a KiCad schematic from a Python netlist.

Every pin gets a net label at its tip (label-style schematic, like many production designs),
so the drawing and the netlist can never disagree. NC pins get a no-connect flag.
"""
import os, uuid, math
from sexpr import parse, dump, find, find1, Sym

KICAD_SYM = os.environ.get("KICAD_SYMBOL_DIR",
                           r"C:\Users\india\AppData\Local\Programs\KiCad\10.0\share\kicad\symbols")
HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_LIB = os.path.join(HERE, "..", "lib", "helmate.kicad_sym")

_cache = {}


def _lib(name):
    if name not in _cache:
        path = LOCAL_LIB if name == "helmate" else os.path.join(KICAD_SYM, f"{name}.kicad_sym")
        _cache[name] = parse(open(path, encoding="utf-8").read())
    return _cache[name]


def _clean(node):
    """Strip legacy bits that newer parsers dislike."""
    if not isinstance(node, list):
        return node
    out = []
    for c in node:
        if isinstance(c, list) and c and c[0] == "id":
            continue
        out.append(_clean(c))
    return out


def get_symbol(lib_id):
    lib, name = lib_id.split(":")
    L = _lib(lib)
    for s in find(L, "symbol"):
        if s[1] == name:
            s = _clean(s)
            ext = find1(s, "extends")
            if ext:
                raise ValueError(f"{lib_id} extends {ext[1]}: pick the base symbol")
            return s
    # easyeda2kicad replaces '/' with '_' in names
    for s in find(L, "symbol"):
        if s[1] == name.replace("/", "_"):
            return _clean(s)
    raise KeyError(lib_id)


def sym_pins(sym):
    pins = []
    for unit in find(sym, "symbol"):
        for p in find(unit, "pin"):
            at = find1(p, "at")
            pins.append(dict(num=str(find1(p, "number")[1]), name=str(find1(p, "name")[1]),
                             x=float(at[1]), y=float(at[2]), a=int(float(at[3])) if len(at) > 3 else 0))
    return pins


def U():
    return str(uuid.uuid4())


def snap(v, g=1.27):
    return round(v / g) * g


class Part:
    def __init__(self, ref, lib_id, value, footprint, nets, lcsc="", mpn="", note=""):
        self.ref, self.lib_id, self.value, self.footprint = ref, lib_id, value, footprint
        self.nets = {str(k): v for k, v in nets.items()}   # pin number -> net name, or None = no-connect
        self.lcsc, self.mpn, self.note = lcsc, mpn, note


def build(parts, out_path, title, project, rev="A", comment=""):
    sheet_uuid = U()
    lib_syms, seen = [], set()
    for p in parts:
        if isinstance(p, str):
            continue
        if p.lib_id not in seen:
            s = [x for x in get_symbol(p.lib_id)]
            s[1] = p.lib_id
            lib_syms.append(s)
            seen.add(p.lib_id)

    # ---- flow layout on A3, new row per "## section" marker ----
    X0, Y0, XMAX = 25.0, 30.0, 395.0
    x, y, row_h = X0, Y0, 0.0
    items, heads = [], []
    for p in parts:
        if isinstance(p, str):
            if x > X0:
                x, y, row_h = X0, y + row_h + 6.0, 0.0
            heads.append((p.lstrip("# "), x, y))
            y += 6.0
            continue
        pins = sym_pins(get_symbol(p.lib_id))
        missing = [k for k in p.nets if k not in {q["num"] for q in pins}]
        if missing:
            raise ValueError(f"{p.ref}: pins {missing} not in symbol {p.lib_id}")
        xs = [q["x"] for q in pins] or [0]
        ys = [q["y"] for q in pins] or [0]
        angs = {q["a"] for q in pins}
        lm = 15.0 if 0 in angs else 5.0
        rm = 15.0 if 180 in angs else 5.0
        tm = 9.0 if 270 in angs else 5.0
        bm = 9.0 if 90 in angs else 5.0
        w = (max(xs) - min(xs)) + lm + rm
        h = (max(ys) - min(ys)) + tm + bm
        if x + w > XMAX:
            x, y, row_h = X0, y + row_h, 0.0
        ox = snap(x + lm - min(xs))
        oy = snap(y + tm + max(ys))
        items.append((p, pins, ox, oy))
        x += w
        row_h = max(row_h, h)
    parts = [p for p in parts if not isinstance(p, str)]

    body = []
    for p, pins, ox, oy in items:
        props = [
            ["property", "Reference", p.ref, ["at", ox, oy - 2.54 - (max(q["y"] for q in pins) if pins else 0), 0],
             ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", "Value", p.value, ["at", ox, oy + 2.54 - (min(q["y"] for q in pins) if pins else 0), 0],
             ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", "Footprint", p.footprint, ["at", ox, oy, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", Sym("yes")]]],
            ["property", "Datasheet", "", ["at", ox, oy, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", Sym("yes")]]],
            ["property", "LCSC", p.lcsc, ["at", ox, oy, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", Sym("yes")]]],
            ["property", "MPN", p.mpn or p.value, ["at", ox, oy, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", Sym("yes")]]],
        ]
        if p.note:
            props.append(["property", "Note", p.note, ["at", ox, oy, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", Sym("yes")]]])
        inst = ["symbol", ["lib_id", p.lib_id], ["at", ox, oy, 0], ["unit", 1],
                ["exclude_from_sim", Sym("no")], ["in_bom", Sym("yes")], ["on_board", Sym("yes")], ["dnp", Sym("no")],
                ["uuid", U()], *props]
        for q in pins:
            inst.append(["pin", q["num"], ["uuid", U()]])
        inst.append(["instances", ["project", project, ["path", "/" + sheet_uuid, ["reference", p.ref], ["unit", 1]]]])
        body.append(inst)

        for q in pins:
            px, py = round(ox + q["x"], 4), round(oy - q["y"], 4)
            if q["num"] not in p.nets:
                raise ValueError(f"{p.ref} pin {q['num']} ({q['name']}) not assigned (use None for NC)")
            net = p.nets[q["num"]]
            if net is None:
                body.append(["no_connect", ["at", px, py], ["uuid", U()]])
                continue
            la = (q["a"] + 180) % 360
            just = "left" if la in (0, 90) else "right"
            body.append(["label", net, ["at", px, py, la],
                         ["effects", ["font", ["size", 1.0, 1.0]], ["justify", Sym(just)]], ["uuid", U()]])

    doc = ["kicad_sch", ["version", 20231120], ["generator", "helmate_schgen"], ["generator_version", "1.0"],
           ["uuid", sheet_uuid], ["paper", "A3"],
           ["title_block", ["title", title], ["date", "2026-11-27"], ["rev", rev], ["company", "Helmate"],
            ["comment", 1, comment]],
           ["lib_symbols", *lib_syms], *body,
           *[["text", t, ["exclude_from_sim", Sym("no")], ["at", hx, hy + 3, 0],
              ["effects", ["font", ["size", 2.2, 2.2], ["bold", Sym("yes")]], ["justify", Sym("left")]], ["uuid", U()]]
             for t, hx, hy in heads],
           ["sheet_instances", ["path", "/", ["page", "1"]]]]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(dump(doc) + "\n")
    return out_path


def nets_of(parts):
    parts = [p for p in parts if not isinstance(p, str)]
    nets = {}
    for p in parts:
        for pin, n in p.nets.items():
            if n is not None:
                nets.setdefault(n, []).append(f"{p.ref}.{pin}")
    return nets


def check(parts):
    """Every net must touch at least two pins."""
    bad = {n: v for n, v in nets_of(parts).items() if len(v) < 2}
    return bad


def bom_csv(parts, path):
    parts = [p for p in parts if not isinstance(p, str)]
    import csv
    groups = {}
    for p in parts:
        key = (p.value, p.footprint, p.lcsc)
        groups.setdefault(key, []).append(p.ref)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Qty", "Note"])
        for (val, fp, lcsc), refs in groups.items():
            note = next((p.note for p in parts if p.ref == refs[0]), "")
            w.writerow([val, ",".join(sorted(refs)), fp.split(":")[-1], lcsc, len(refs), note])
    return path
