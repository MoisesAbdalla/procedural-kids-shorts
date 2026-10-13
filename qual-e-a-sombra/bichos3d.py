"""Bichos 3D estilo brinquedo (Blender, headless). Renderiza um loop de idle com fundo transparente.

blender -b --factory-startup -P bichos3d.py -- --animal gato --out out/3d [--still] [--frames 60]

Também é importado como biblioteca (primitivas, bichos, luz, câmera) por ../ovo-surpresa/ovo3d.py.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

RES_X, RES_Y = 800, 1000
INK = "#22223B"
OUTW = 0.035


# ------------------------------------------------------------------ util
def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


_mats = {}


def mat(hexstr, rough=0.42, coat=0.3, emit=0.0):
    key = (hexstr, rough, coat, emit)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m_{hexstr}")
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = lin(hexstr)
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = lin(hexstr)
        b.inputs["Emission Strength"].default_value = emit
    _mats[key] = m
    return m


def outline_mat():
    if "outline" in _mats:
        return _mats["outline"]
    m = bpy.data.materials.new("outline")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(INK)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = True
    _mats["outline"] = m
    return m


def link_parent(o, parent):
    if parent is None:
        return
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = parent
    o.matrix_world = mw


def finish_obj(o, m, outline, parent):
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    if outline:
        o.data.materials.append(outline_mat())
        mod = o.modifiers.new("outline", "SOLIDIFY")
        mod.thickness = OUTW
        mod.offset = 1.0
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.material_offset = 1
    link_parent(o, parent)
    return o


def select_only(o):
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def ell(loc, size, m, parent=None, outline=True, rot=(0, 0, 0), quat=None, seg=40):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc)
    o = bpy.context.active_object
    if quat is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = quat
    else:
        o.rotation_euler = rot
    o.scale = size
    select_only(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_obj(o, m, outline, parent)


def cone(loc, r, depth, m, parent=None, outline=True, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r, radius2=r * 0.12, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    return finish_obj(o, m, outline, parent)


def tube(pts, radii, m, parent=None, outline=True, caps=True):
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 8
    cu.resolution_u = 16
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p, r in zip(sp.bezier_points, pts, radii):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
        bp.radius = r
    o = bpy.data.objects.new("tube", cu)
    bpy.context.collection.objects.link(o)
    select_only(o)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    finish_obj(o, m, outline, parent)
    if caps:
        for p, r in ((pts[0], radii[0]), (pts[-1], radii[-1])):
            ell(p, (r, r, r), m, parent, outline)
    return o


def pivot(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(e)
    e.matrix_world = Matrix.Translation(loc)
    link_parent(e, parent)
    return e


def patch(center, radii, d, r, m, parent, thick=0.035):
    """Mancha achatada colada na superfície de um elipsoide (direção d a partir do centro)."""
    d = Vector(d).normalized()
    c, R = Vector(center), Vector(radii)
    p = c + Vector((R.x * d.x, R.y * d.y, R.z * d.z))
    n = Vector((d.x / R.x, d.y / R.y, d.z / R.z)).normalized()
    return ell(p - n * thick * 0.3, (r, r * 0.8, thick), m, parent, outline=False, quat=n.to_track_quat("Z", "Y"))


def eye(loc, r, head, iris=None):
    x, y, z = loc
    piv = pivot("eye", loc, head)
    ell((x, y, z), (r, r * 0.55, r * 1.12), mat("#FFFFFF", 0.25), piv, outline=False)
    py = y - r * 0.45
    if iris:
        ell((x, py, z - r * 0.05), (r * 0.78, r * 0.3, r * 0.88), mat(iris, 0.3), piv, outline=False)
        ell((x, py - r * 0.18, z - r * 0.05), (r * 0.3, r * 0.2, r * 0.7), mat("#151520", 0.2), piv, outline=False)
    else:
        ell((x, py, z - r * 0.08), (r * 0.62, r * 0.3, r * 0.72), mat("#151520", 0.2), piv, outline=False)
    ell((x - r * 0.25, py - r * 0.3, z + r * 0.28), (r * 0.2,) * 3, mat("#FFFFFF", 0.3, emit=2.0), piv, outline=False)
    return piv


# ------------------------------------------------------------------ bichos
def elefante():
    body_c, ear_c, pink, dark = mat("#8EA8D6"), mat("#9FB6E0"), mat("#F7A8C4", 0.5), mat("#6A86B0")
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0.25, 0), root)
    ell((0, 0.25, 1.15), (0.95, 1.15, 0.85), body_c, body)
    for x in (-0.5, 0.5):
        for y in (-0.35, 0.85):
            ell((x, y, 0.45), (0.31, 0.31, 0.47), body_c, body)
        for k in (-1, 0, 1):
            ell((x + k * 0.11, -0.6, 0.2), (0.055, 0.04, 0.06), mat("#FFFFFF", 0.3), body, outline=False)
    tail = pivot("tail", (0, 1.35, 1.3), body)
    tube([(0, 1.3, 1.3), (0, 1.6, 1.0), (0.05, 1.68, 0.72)], [0.05, 0.05, 0.05], body_c, tail, caps=False)
    ell((0.05, 1.7, 0.65), (0.09, 0.09, 0.13), dark, tail)
    head = pivot("head", (0, -0.6, 1.5), body)
    ell((0, -0.85, 1.75), (0.72, 0.68, 0.66), body_c, head)
    ears = []
    for sx in (-1, 1):
        ep = pivot("ear", (sx * 0.55, -0.5, 1.9), head)
        ell((sx * 0.82, -0.45, 1.85), (0.52, 0.12, 0.6), ear_c, ep, rot=(0, 0, -sx * 0.35))
        ell((sx * 0.84, -0.55, 1.85), (0.36, 0.05, 0.43), pink, ep, outline=False, rot=(0, 0, -sx * 0.35))
        ears.append((ep, sx))
    tube([(0, -1.3, 1.65), (0, -1.62, 1.3), (0, -1.78, 0.92), (0, -2.02, 0.8), (0, -2.12, 0.98)],
         [0.27, 0.23, 0.19, 0.16, 0.15], body_c, head)
    eyes = [eye((sx * 0.27, -1.42, 1.98), 0.15, head) for sx in (-1, 1)]
    for sx in (-1, 1):
        ell((sx * 0.46, -1.33, 1.62), (0.12, 0.04, 0.08), pink, head, outline=False)
    return dict(root=root, body=body, head=head, tail=tail, ears=ears, eyes=eyes, yaw=60)


def gato():
    orange, cream, pink = mat("#F7A440"), mat("#FFE3C2"), mat("#FF9FB8", 0.5)
    dark = mat("#D9802A")
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0, 0), root)
    ell((0, 0, 0.85), (0.75, 0.68, 0.88), orange, body)
    ell((0, -0.45, 0.8), (0.48, 0.28, 0.6), cream, body, outline=False)
    for sx in (-1, 1):
        ell((sx * 0.32, -0.55, 0.14), (0.24, 0.32, 0.15), cream, body)
    tail = pivot("tail", (0.45, 0.5, 0.35), body)
    tube([(0.45, 0.5, 0.35), (0.95, 0.35, 0.45), (1.05, 0.05, 1.0), (0.85, -0.05, 1.45)],
         [0.12, 0.12, 0.11, 0.11], orange, tail)
    head = pivot("head", (0, -0.1, 1.55), body)
    hc, hr = (0, -0.2, 2.05), (0.85, 0.72, 0.7)
    ell(hc, hr, orange, head)
    ears = []
    for sx in (-1, 1):
        ep = pivot("ear", (sx * 0.5, -0.2, 2.45), head)
        cone((sx * 0.5, -0.2, 2.68), 0.3, 0.6, orange, ep, rot=(0, sx * 0.35, 0))
        cone((sx * 0.49, -0.27, 2.6), 0.16, 0.36, pink, ep, outline=False, rot=(-0.15, sx * 0.35, 0))
        ears.append((ep, sx))
    for dx in (-0.22, 0.0, 0.22):
        patch(hc, hr, (dx, -0.35, 1.0), 0.08 if dx else 0.1, dark, head)
    for sx in (-1, 1):
        ell((sx * 0.16, -0.86, 1.9), (0.2, 0.13, 0.15), cream, head, outline=False)
        ell((sx * 0.55, -0.72, 1.92), (0.12, 0.04, 0.07), pink, head, outline=False)
        for dz in (0.06, -0.06):
            tube([(sx * 0.3, -0.92, 1.9 + dz * 0.3), (sx * 0.9, -0.88, 1.9 + dz * 1.6)], [0.012, 0.01],
                 mat("#151520", 0.3), head, outline=False, caps=False)
    ell((0, -0.97, 2.0), (0.08, 0.05, 0.06), pink, head, outline=False)
    eyes = [eye((sx * 0.32, -0.8, 2.15), 0.19, head, iris="#7ED957") for sx in (-1, 1)]
    return dict(root=root, body=body, head=head, tail=tail, ears=ears, eyes=eyes, yaw=22)


def girafa():
    global OUTW
    OUTW = 0.05
    yel, light, spot = mat("#F9C846"), mat("#FCE3A0"), mat("#C9732A", 0.5)
    hoof, pink = mat("#6B3E1E"), mat("#FF9FB8", 0.5)
    root = pivot("root", (0, 0, 0))
    body = pivot("body", (0, 0.2, 0), root)
    bc, br = (0, 0.2, 1.65), (0.62, 1.0, 0.55)
    ell(bc, br, yel, body)
    for x in (-0.36, 0.36):
        for y in (-0.42, 0.82):
            ell((x, y, 0.72), (0.13, 0.13, 0.7), yel, body)
            ell((x, y, 0.08), (0.15, 0.15, 0.09), hoof, body)
    for d, r in [((1, -0.3, 0.4), 0.17), ((1, 0.35, 0.1), 0.2), ((1, 0.8, 0.5), 0.15), ((1, -0.7, -0.1), 0.14),
                 ((-1, -0.3, 0.4), 0.17), ((-1, 0.35, 0.1), 0.2), ((-1, 0.8, 0.5), 0.15), ((-1, -0.7, -0.1), 0.14),
                 ((0.3, 0.1, 1), 0.16), ((-0.3, 0.6, 1), 0.15), ((0.2, -0.6, 1), 0.13)]:
        patch(bc, br, d, r, spot, body)
    tail = pivot("tail", (0, 1.15, 1.75), body)
    tube([(0, 1.15, 1.75), (0, 1.32, 1.4), (0, 1.36, 1.05)], [0.04, 0.04, 0.04], yel, tail, caps=False)
    ell((0, 1.37, 0.97), (0.07, 0.07, 0.12), spot, tail)
    neck = [(0, -0.5, 1.85), (0, -0.72, 2.6), (0, -0.82, 3.3)]
    tube(neck, [0.24, 0.2, 0.17], yel, body)
    def neck_at(t):
        a, b, c = (Vector(q) for q in neck)
        return a.lerp(b, t * 2) if t < 0.5 else b.lerp(c, t * 2 - 1)
    for t, dx, dy, r in [(0.12, 1, -0.3, 0.09), (0.2, -1, -0.4, 0.08), (0.32, 0.3, -1, 0.09), (0.45, 1, 0.2, 0.08),
                         (0.5, -0.8, -0.6, 0.08), (0.62, 0.6, -0.8, 0.07), (0.75, -1, 0.1, 0.06), (0.85, 0.9, -0.4, 0.06)]:
        rad = 0.24 + (0.17 - 0.24) * t
        patch(neck_at(t), (rad, rad, 0.4), (dx, dy, 0), r, spot, body)
    for t in (0.1, 0.3, 0.5, 0.7, 0.9):
        a = neck_at(t)
        ell(a + Vector((0, 0.2 - 0.05 * t, 0)), (0.05, 0.08, 0.12), spot, body)
    head = pivot("head", (0, -0.82, 3.3), body)
    ell((0, -0.95, 3.55), (0.38, 0.45, 0.36), yel, head)
    ell((0, -1.32, 3.45), (0.3, 0.25, 0.25), light, head)
    for sx in (-1, 1):
        tube([(sx * 0.14, -0.88, 3.8), (sx * 0.17, -0.88, 4.12)], [0.05, 0.05], yel, head, caps=False)
        ell((sx * 0.17, -0.88, 4.16), (0.09, 0.09, 0.09), spot, head)
        ell((sx * 0.11, -1.55, 3.48), (0.03, 0.02, 0.02), hoof, head, outline=False)
        ell((sx * 0.3, -1.22, 3.42), (0.08, 0.03, 0.05), pink, head, outline=False)
    ears = []
    for sx in (-1, 1):
        ep = pivot("ear", (sx * 0.3, -0.85, 3.72), head)
        ell((sx * 0.45, -0.85, 3.74), (0.2, 0.06, 0.09), yel, ep, rot=(0, -sx * 0.4, 0))
        ears.append((ep, sx))
    eyes = [eye((sx * 0.2, -1.25, 3.7), 0.11, head) for sx in (-1, 1)]
    return dict(root=root, body=body, head=head, tail=tail, ears=ears, eyes=eyes, yaw=32)


# ------------------------------------------------------------------ cena
def animate(P, frames):
    for f in range(1, frames + 1):
        t = (f - 1) / frames
        s = math.sin(2 * math.pi * t)
        s2 = math.sin(4 * math.pi * t)
        P["body"].scale = (1 + 0.015 * s, 1 + 0.015 * s, 1 + 0.03 * s)
        P["body"].keyframe_insert("scale", frame=f)
        P["head"].rotation_euler = (math.radians(3 * s2), math.radians(6 * s), 0)
        P["head"].keyframe_insert("rotation_euler", frame=f)
        P["tail"].rotation_euler = (0, 0, math.radians(25 * s2))
        P["tail"].keyframe_insert("rotation_euler", frame=f)
        for ep, sx in P["ears"]:
            ep.rotation_euler = (0, 0, sx * math.radians(10 * s2))
            ep.keyframe_insert("rotation_euler", frame=f)
        u = (f - 1) % frames
        blink = {38: 0.6, 39: 0.15, 40: 0.1, 41: 0.15, 42: 0.6}.get(u, 1.0) if frames >= 45 else 1.0
        for e in P["eyes"]:
            e.scale = (1, 1, blink)
            e.keyframe_insert("scale", frame=f)


def setup_render(samples, frames):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.eevee.taa_render_samples = samples
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.fps = 30
    sc.frame_start, sc.frame_end = 1, frames


def setup_world_lights():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("world")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.78, 0.8, 0.88, 1)
    bg.inputs["Strength"].default_value = 0.9

    def sun(name, pos, energy, shadow=True, angle=0.25):
        L = bpy.data.lights.new(name, "SUN")
        L.energy = energy
        L.angle = angle
        L.use_shadow = shadow
        o = bpy.data.objects.new(name, L)
        sc.collection.objects.link(o)
        o.rotation_euler = (-Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    sun("key", (-0.6, -1.0, 1.3), 3.2)
    sun("fill", (1.0, -0.6, 0.2), 0.9, shadow=False)
    sun("rim", (0.4, 1.0, 0.9), 2.2, shadow=False)


def mesh_points(objs=None):
    """Cantos das bounding boxes (avaliadas) em coordenadas de mundo."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs or [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        ev = o.evaluated_get(dg)
        pts += [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    return pts


def fit_camera(pts, fill=0.9, bottom=0.04):
    """Câmera ortográfica levemente de cima, enquadrando `pts` com a base a `bottom` da borda inferior."""
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    center = sum(pts, Vector()) / len(pts)
    direction = Vector((0, -1, 0.24)).normalized()
    cam.location = center + direction * 40
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    cp = [inv @ p for p in pts]
    minx, maxx = min(p.x for p in cp), max(p.x for p in cp)
    miny, maxy = min(p.y for p in cp), max(p.y for p in cp)
    w_, h_ = maxx - minx, maxy - miny
    S = max(h_ / fill, w_ / (fill * RES_X / RES_Y))
    cd.ortho_scale = S
    cd.clip_end = 200
    shift = Vector(((minx + maxx) / 2, miny + S * (0.5 - bottom), 0))
    cam.location = cam.matrix_world @ shift
    return cam


def setup_scene(P, samples, frames):
    setup_render(samples, frames)
    setup_world_lights()
    P["root"].rotation_euler = (0, 0, math.radians(P["yaw"]))
    bpy.context.view_layer.update()
    fit_camera(mesh_points())


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--animal", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--samples", type=int, default=32)
    args = ap.parse_args(argv)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    P = {"elefante": elefante, "gato": gato, "girafa": girafa}[args.animal]()
    animate(P, args.frames)
    setup_scene(P, args.samples, args.frames)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    if args.still:
        sc.frame_set(1)
        sc.render.filepath = str(out / f"{args.animal}_still.png")
        bpy.ops.render.render(write_still=True)
    else:
        (out / args.animal).mkdir(exist_ok=True)
        sc.render.filepath = str(out / args.animal / "f_####")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
