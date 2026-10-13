"""Ovo surpresa 3D (Blender, headless): ovo balança, racha, a casca voa e um bicho pula de dentro.
Renderiza 6 s (180 quadros) com fundo transparente; ovo.py compõe o vídeo final.

blender -b --factory-startup -P ovo3d.py -- --egg 0 --out out/3d [--still 60,120]
"""
import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "qual-e-a-sombra"))
import bichos3d as b3  # noqa: E402
from bichos3d import cone, ell, eye, lin, mat, patch, pivot, tube  # noqa: E402

FRAMES, FPS = 180, 30
T_BURST = 3.0
KNOCKS = (1.0, 1.8, 2.5)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x):
    x = clamp(x)
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ------------------------------------------------------------------ bichos que nascem de ovo
def pintinho():
    yel, ora, pink = mat("#FFD93B"), mat("#FF9F1C"), mat("#FF9FB8", 0.5)
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0, 0), root)
    ell((0, 0, 0.75), (0.68, 0.62, 0.66), yel, body)
    wings = []
    for sx in (-1, 1):
        wp = pivot("wing", (sx * 0.6, 0, 0.95), body)
        ell((sx * 0.7, 0.05, 0.78), (0.14, 0.32, 0.27), yel, wp, rot=(0, sx * 0.45, 0))
        wings.append((wp, sx))
        ell((sx * 0.22, -0.32, 0.08), (0.13, 0.2, 0.06), ora, body)
    head = pivot("head", (0, -0.05, 1.25), body)
    ell((0, -0.1, 1.52), (0.5, 0.48, 0.47), yel, head)
    for k, ang in ((-1, -0.45), (0, 0.0), (1, 0.45)):
        ell((k * 0.07, -0.05, 2.02), (0.05, 0.05, 0.16), yel, head, rot=(0, ang, 0))
    cone((0, -0.64, 1.43), 0.12, 0.26, ora, head, rot=(math.pi / 2, 0, 0))
    eyes = [eye((sx * 0.2, -0.52, 1.64), 0.12, head) for sx in (-1, 1)]
    for sx in (-1, 1):
        ell((sx * 0.34, -0.47, 1.45), (0.09, 0.03, 0.06), pink, head, outline=False)
    return dict(root=root, body=body, head=head, tail=None, wings=wings, eyes=eyes, yaw=18, z=0.32)


def dinossauro():
    g, belly, sp = mat("#6BD66B"), mat("#D9F7A8"), mat("#FF9F43")
    pink = mat("#FF9FB8", 0.5)
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0, 0), root)
    ell((0, 0.1, 0.8), (0.6, 0.7, 0.65), g, body)
    ell((0, -0.33, 0.75), (0.42, 0.28, 0.5), belly, body, outline=False)
    for sx in (-1, 1):
        ell((sx * 0.36, -0.05, 0.25), (0.22, 0.28, 0.25), g, body)
        ell((sx * 0.38, -0.5, 0.98), (0.08, 0.16, 0.08), g, body, rot=(0.6, 0, 0))
    tail = pivot("tail", (0, 0.6, 0.7), body)
    tube([(0, 0.6, 0.75), (0, 1.05, 0.5), (0.15, 1.4, 0.3)], [0.3, 0.18, 0.07], g, tail)
    for (y, z, r) in ((0.05, 1.42, 0.12), (0.38, 1.35, 0.11), (0.68, 1.12, 0.1), (0.98, 0.82, 0.08)):
        cone((0, y, z), r, r * 2.2, sp, body, rot=(0.35, 0, 0))
    head = pivot("head", (0, -0.2, 1.3), body)
    ell((0, -0.35, 1.72), (0.5, 0.55, 0.45), g, head)
    ell((0, -0.78, 1.6), (0.38, 0.3, 0.28), g, head)
    cone((0, -0.3, 2.18), 0.11, 0.24, sp, head, rot=(0.25, 0, 0))
    tube([(-0.22, -1.0, 1.52), (0, -1.07, 1.47), (0.22, -1.0, 1.52)], [0.022, 0.022, 0.022],
         mat("#151520", 0.3), head, outline=False)
    for sx in (-1, 1):
        ell((sx * 0.1, -1.06, 1.7), (0.035, 0.02, 0.025), mat("#2E7D32"), head, outline=False)
        ell((sx * 0.33, -0.86, 1.55), (0.08, 0.03, 0.05), pink, head, outline=False)
    eyes = [eye((sx * 0.22, -0.72, 1.9), 0.13, head) for sx in (-1, 1)]
    return dict(root=root, body=body, head=head, tail=tail, wings=[], eyes=eyes, yaw=32, z=0.32)


def tartaruga():
    shell, plate, rim = mat("#5CC46E"), mat("#3E9E50"), mat("#F4E3A1")
    skin, pink = mat("#A8E07A"), mat("#FF9FB8", 0.5)
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0, 0), root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ell((sx * 0.55, sy * 0.5, 0.25), (0.2, 0.22, 0.2), skin, body)
    sc, sr = (0, 0, 0.5), (0.8, 0.85, 0.6)
    ell(sc, sr, shell, body)
    ell((0, 0, 0.42), (0.9, 0.95, 0.12), rim, body)
    for d, r in [((0, 0, 1), 0.2), ((0.6, 0, 0.8), 0.17), ((-0.6, 0, 0.8), 0.17), ((0, -0.6, 0.8), 0.17),
                 ((0, 0.6, 0.8), 0.17), ((0.5, -0.5, 0.6), 0.14), ((-0.5, -0.5, 0.6), 0.14),
                 ((0.5, 0.5, 0.6), 0.14), ((-0.5, 0.5, 0.6), 0.14)]:
        patch(sc, sr, d, r, plate, body)
    tail = pivot("tail", (0, 0.85, 0.35), body)
    cone((0, 0.98, 0.33), 0.08, 0.25, skin, tail, rot=(-math.pi / 2, 0, 0))
    head = pivot("head", (0, -0.75, 0.55), body)
    ell((0, -0.95, 0.62), (0.16, 0.25, 0.16), skin, head)
    ell((0, -1.15, 0.85), (0.34, 0.34, 0.31), skin, head)
    tube([(-0.17, -1.43, 0.75), (0, -1.48, 0.71), (0.17, -1.43, 0.75)], [0.018, 0.018, 0.018],
         mat("#151520", 0.3), head, outline=False)
    for sx in (-1, 1):
        ell((sx * 0.24, -1.38, 0.8), (0.07, 0.03, 0.045), pink, head, outline=False)
    eyes = [eye((sx * 0.15, -1.38, 0.95), 0.1, head) for sx in (-1, 1)]
    return dict(root=root, body=body, head=head, tail=tail, wings=[], eyes=eyes, yaw=28, z=0.85)


EGGS = [
    dict(animal=pintinho, shell="#FFF4DC", dot="#FF8FB1"),
    dict(animal=dinossauro, shell="#DDF7EC", dot="#FFC93C"),
    dict(animal=tartaruga, shell="#EFE4FF", dot="#59C3F5"),
]


# ------------------------------------------------------------------ ovo
EC, ER = Vector((0, 0, 1.15)), Vector((0.88, 0.88, 1.15))


def cut_z(x, y):
    """Altura da rachadura em zigue-zague em torno do ovo."""
    a = (math.atan2(y, x) / (2 * math.pi)) * 7
    tri = 2 * abs(2 * (a - math.floor(a + 0.5))) - 1
    return 1.28 + 0.13 * tri


def egg_material(shell_hex):
    """Casca colorida por fora, branca por dentro (Backfacing)."""
    m = bpy.data.materials.new("egg")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.35
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.3
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    cols = [i for i in mix.inputs if i.type == "RGBA" and i.enabled]
    cols[0].default_value = lin(shell_hex)
    cols[1].default_value = lin("#FFFFFF")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    out = next(o for o in mix.outputs if o.type == "RGBA" and o.enabled)
    nt.links.new(out, bsdf.inputs["Base Color"])
    return m


def egg(shell_hex, dot_hex):
    root = pivot("egg_root", (0, 0, 0))
    halves = {}
    m = egg_material(shell_hex)
    for name in ("bottom", "top"):
        piv = pivot(f"egg_{name}", (0, 0, 1.28) if name == "top" else (0, 0, 0), root)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=192, v_segments=96, radius=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * ER.x, v.co.y * ER.y, v.co.z * ER.z)) + EC
        kill = []
        for f in bm.faces:
            c = f.calc_center_median()
            is_top = c.z > cut_z(c.x, c.y)
            if is_top != (name == "top"):
                kill.append(f)
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        me = bpy.data.meshes.new(f"egg_{name}")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"egg_{name}", me)
        bpy.context.collection.objects.link(o)
        b3.finish_obj(o, m, True, piv)
        halves[name] = piv
    dots = mat(dot_hex, 0.4)
    n = 22
    for i in range(n):                                  # bolinhas (espiral de Fibonacci)
        zf = 1 - 2 * (i + 0.5) / n
        if abs(zf) > 0.82:
            continue
        r = math.sqrt(1 - zf * zf)
        th = i * math.pi * (3 - math.sqrt(5))
        d = Vector((r * math.cos(th), r * math.sin(th), zf))
        p = EC + Vector((ER.x * d.x, ER.y * d.y, ER.z * d.z))
        cz = cut_z(p.x, p.y)
        if abs(p.z - cz) < 0.16:
            continue
        patch(EC, ER, d, 0.15, dots, halves["top" if p.z > cz else "bottom"], thick=0.03)
    return root, halves


# ------------------------------------------------------------------ animação
def animate(eroot, halves, P):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FPS
        # ovo
        if t < T_BURST:
            amp = math.radians(3 + 12 * clamp((t - 0.4) / 2.5)) if t > 0.4 else 0.0
            ang = amp * math.sin(2 * math.pi * 2.3 * t)
            hop = sum(0.16 * math.sin(math.pi * (t - k) / 0.22) for k in KNOCKS if 0 <= t - k < 0.22)
            eroot.rotation_euler = (ang * 0.35, ang, 0)
            eroot.location = (0, 0, hop)
            bs = 1.0
        else:
            u = t - T_BURST
            eroot.rotation_euler = (0, 0, 0)
            eroot.location = (0, 0, 0)
            bs = 1 - 0.18 * math.exp(-7 * u) * math.cos(22 * u)
        eroot.keyframe_insert("rotation_euler", frame=f)
        eroot.keyframe_insert("location", frame=f)
        halves["bottom"].scale = (2 - bs, 2 - bs, bs)
        halves["bottom"].keyframe_insert("scale", frame=f)

        top = halves["top"]
        base = Vector((0, 0, 1.28))
        if t < 2.2:
            top.location, top.rotation_euler, top.scale = base, (0, 0, 0), (1, 1, 1)
        elif t < T_BURST:
            k = (t - 2.2) / 0.8
            top.location = base + Vector((0, 0, 0.03 + 0.05 * k + 0.02 * math.sin(t * 70)))
            top.rotation_euler = (0, math.radians(4 * k * math.sin(t * 45)), 0)
            top.scale = (1, 1, 1)
        else:
            u = t - T_BURST
            # gira e encolhe até sumir antes de sair do quadro (senão o render corta a casca)
            top.location = base + Vector((1.3 * u, -0.3 * u, 2.6 * u))
            top.rotation_euler = (0, 8 * u, 2 * u)
            top.scale = (max(0.001, 1 - (u / 0.45) ** 2),) * 3
        for prop in ("location", "rotation_euler", "scale"):
            top.keyframe_insert(prop, frame=f)

        # bicho
        r = P["root"]
        if t < T_BURST:
            r.scale = (0.001,) * 3
            r.location = (0, 0, P["z"] - 0.5)
        else:
            u = t - T_BURST
            e = ease_out_back(u / 0.45)
            r.scale = (max(0.001, e),) * 3
            r.location = (0, 0, P["z"] - 0.2 * (1 - clamp(u / 0.35)) + 0.25 * math.sin(math.pi * clamp(u / 0.45)))
        r.keyframe_insert("scale", frame=f)
        r.keyframe_insert("location", frame=f)
        s = math.sin(2 * math.pi * t / 2)
        s2 = math.sin(2 * math.pi * t)
        P["body"].scale = (1 + 0.015 * s, 1 + 0.015 * s, 1 + 0.03 * s)
        P["body"].keyframe_insert("scale", frame=f)
        P["head"].rotation_euler = (math.radians(3 * s2), math.radians(8 * s), 0)
        P["head"].keyframe_insert("rotation_euler", frame=f)
        if P["tail"]:
            P["tail"].rotation_euler = (0, 0, math.radians(22 * s2))
            P["tail"].keyframe_insert("rotation_euler", frame=f)
        flap = 35 * max(0.0, math.sin(2 * math.pi * 3 * (t - T_BURST))) if T_BURST + 0.4 < t < T_BURST + 1.4 else 0
        for wp, sx in P["wings"]:
            wp.rotation_euler = (0, -sx * math.radians(flap), 0)
            wp.keyframe_insert("rotation_euler", frame=f)
        blink = {0: 0.6, 1: 0.15, 2: 0.1, 3: 0.15, 4: 0.6}.get(f - 1 - int(4.4 * FPS), 1.0)
        for e_ in P["eyes"]:
            e_.scale = (1, 1, blink)
            e_.keyframe_insert("scale", frame=f)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--egg", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", default="")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--range", default="", help="ex.: 91,120 renderiza só esse trecho")
    args = ap.parse_args(argv)

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    cfg = EGGS[args.egg]
    b3.OUTW = 0.035
    eroot, halves = egg(cfg["shell"], cfg["dot"])
    P = cfg["animal"]()
    P["root"].location = (0, 0, P["z"])  # bicho "sentado" na casca de baixo
    P["root"].rotation_euler = (0, 0, math.radians(P["yaw"]))
    b3.setup_render(args.samples, FRAMES)
    b3.setup_world_lights()
    bpy.context.view_layer.update()
    b3.fit_camera(b3.mesh_points(), fill=0.8, bottom=0.06)   # enquadra ovo inteiro + bicho já fora
    animate(eroot, halves, P)

    out = Path(args.out).resolve() / f"ovo{args.egg}"
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    if args.still:
        for fr in (int(x) for x in args.still.split(",")):
            sc.frame_set(fr)
            sc.render.filepath = str(out / f"still_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        if args.range:
            sc.frame_start, sc.frame_end = (int(x) for x in args.range.split(","))
        sc.render.filepath = str(out / "f_####")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
