"""Tiny S-expression reader/writer for KiCad files."""
import re

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:\\.|[^"\\])*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"bad token at {pos}: {text[pos:pos+40]!r}")
        pos = m.end()
        lp, rp, st, at = m.groups()
        if lp:
            stack.append(cur)
            cur = []
        elif rp:
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif st is not None:
            cur.append(st[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        elif at is not None:
            cur.append(Sym(at))
    return cur[0] if len(cur) == 1 else cur


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def dump(x, indent=0):
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        if simple and len(x) < 8:
            h = str(x[0]) if isinstance(x[0], str) else dump(x[0])
            return "(" + " ".join([h] + [dump(e) for e in x[1:]]) + ")"
        pad = "  " * (indent + 1)
        head = str(x[0]) if isinstance(x[0], str) else dump(x[0])
        rest = "\n".join(pad + dump(e, indent + 1) for e in x[1:])
        return f"({head}\n{rest}\n{'  ' * indent})"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, float)):
        return f"{x:.4f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)
    return q(x)


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
