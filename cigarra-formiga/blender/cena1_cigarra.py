"""Cena 1 de "A Cigarra e a Formiga" no Blender (Cycles): a Cigarra toca ukulele numa pedra com musgo,
em escala de inseto, entre flores reais (Poly Haven, CC0) com o lago do HDRI desfocado ao fundo.

blender -b --factory-startup -P cena1_cigarra.py -- --out ../out/blender [--still 1,72] [--res 1920] [--samples 64] [--frames 144] [--range 1,5]
"""
import argparse
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                                   # shorts-infantis/
ASSETS = ROOT / "assets" / "polyhaven"
sys.path.insert(0, str(ROOT / "qual-e-a-sombra"))
import bichos3d as b3  # noqa: E402

FPS = 24
SUN_DIR = Vector((-0.45, 1.0, 0.18))                      # de onde vem o sol (atrás e à esquerda da personagem)
HDRI_SUN_U = 0.585                                          # coluna do sol no HDRI (medida no .exr)
CHAR_SCALE = 0.032                                          # boneco de ~2.2 unidades -> ~7 cm


# ------------------------------------------------------------------ materiais
def pmat(name, hexstr, rough=0.45, sss=0.0, coat=0.15, transmission=0.0, ior=1.45, alpha=1.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = b3.lin(hexstr)
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.4)
        b.inputs["Subsurface Scale"].default_value = 0.004
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = ior
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def ground_mat():
    m = bpy.data.materials.new("ground")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.9
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = b3.lin("#3A2A1C")
    ramp.color_ramp.elements[1].color = b3.lin("#56702E")
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ------------------------------------------------------------------ primitivas (sem contorno de desenho)
def E(loc, size, m, parent=None, **kw):
    return b3.ell(loc, size, m, parent, outline=False, **kw)


def T(pts, radii, m, parent=None, caps=True):
    return b3.tube(pts, radii, m, parent, outline=False, caps=caps)


def cyl(loc, r, depth, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    bev = o.modifiers.new("bevel", "BEVEL")
    bev.width = min(r, depth) * 0.25
    bev.segments = 4
    o.modifiers.new("wn", "WEIGHTED_NORMAL")
    return b3.finish_obj(o, m, False, parent)


# ------------------------------------------------------------------ Cigarra (detalhada, estilo filme)
def cigarra():
    green = pmat("cig_green", "#5BC236", rough=0.4, sss=0.25, coat=0.3)
    dark = pmat("cig_dark", "#3E8F25", rough=0.45, sss=0.2, coat=0.3)
    belly = pmat("cig_belly", "#D4EE96", rough=0.5, sss=0.3)
    pink = pmat("cig_pink", "#FF8FA8", rough=0.6, sss=0.3)
    ink = pmat("cig_ink", "#2A1A14", rough=0.4)
    straw = pmat("straw", "#F0A23C", rough=0.7)
    band = pmat("band", "#D9483B", rough=0.5)
    wing = pmat("wing", "#DFF6FF", rough=0.08, transmission=1.0, ior=1.3, coat=0.0)
    wood = pmat("wood", "#C98B4F", rough=0.35, coat=0.6)
    wood2 = pmat("wood2", "#7A4A24", rough=0.45, coat=0.4)
    string = pmat("string", "#F4F1E8", rough=0.3)

    root = b3.pivot("root", (0, 0, 0))
    body = b3.pivot("body", (0, 0, 0), root)
    E((0, 0.12, 0.5), (0.42, 0.5, 0.52), green, body, rot=(0.25, 0, 0))          # abdômen
    for z in (0.3, 0.48, 0.66):                                                   # anéis
        E((0, 0.14, z), (0.425, 0.505, 0.035), dark, body, rot=(0.25, 0, 0))
    E((0, -0.22, 0.55), (0.3, 0.2, 0.38), belly, body)
    E((0, -0.05, 0.98), (0.46, 0.4, 0.36), green, body)                           # tórax
    for sx in (-1, 1):                                                            # asas de vidro
        E((sx * 0.22, 0.42, 0.95), (0.05, 0.36, 0.62), wing, body, rot=(-0.35, 0, sx * 0.25))
        E((sx * 0.3, 0.4, 0.75), (0.04, 0.28, 0.45), wing, body, rot=(-0.55, 0, sx * 0.4))
        T([(sx * 0.22, -0.2, 0.32), (sx * 0.34, -0.55, 0.28), (sx * 0.3, -0.72, -0.18)],
          [0.07, 0.065, 0.06], dark, body)                                        # pernas penduradas
        E((sx * 0.3, -0.8, -0.24), (0.1, 0.15, 0.07), dark, body)

    head = b3.pivot("head", (0, -0.05, 1.22), body)
    E((0, -0.1, 1.52), (0.58, 0.5, 0.46), green, head)
    eyes = [b3.eye((sx * 0.26, -0.52, 1.6), 0.2, head, iris="#F5A623") for sx in (-1, 1)]
    for sx in (-1, 1):
        E((sx * 0.43, -0.45, 1.42), (0.09, 0.03, 0.055), pink, head)
        T([(sx * 0.13, -0.42, 1.86), (sx * 0.22, -0.5, 2.08), (sx * 0.36, -0.58, 2.25)],
          [0.022, 0.02, 0.018], dark, head, caps=False)                           # antenas
        E((sx * 0.37, -0.59, 2.27), (0.055, 0.055, 0.055), dark, head)
    T([(-0.13, -0.58, 1.38), (0, -0.61, 1.33), (0.13, -0.58, 1.38)], [0.016] * 3, ink, head)
    hat = b3.pivot("hat", (0, -0.08, 1.92), head)
    cyl((0, -0.08, 1.92), 0.56, 0.035, straw, hat)
    cyl((0, -0.08, 2.06), 0.31, 0.26, straw, hat)
    cyl((0, -0.08, 1.98), 0.317, 0.07, band, hat)
    hat.rotation_euler = (0.12, -0.15, 0)

    # ukulele: construído no espaço local (braço ao longo de +X) e posicionado na frente do peito
    uk = b3.pivot("uke", (0, 0, 0), body)
    E((0, 0, 0), (0.27, 0.075, 0.23), wood, uk)
    E((0.25, 0, 0), (0.2, 0.075, 0.17), wood, uk)
    E((0.08, -0.08, 0), (0.07, 0.012, 0.07), ink, uk)
    E((0.62, 0, 0), (0.36, 0.035, 0.045), wood2, uk)
    E((1.0, 0, 0), (0.09, 0.035, 0.07), wood2, uk)
    for dz in (-0.024, -0.008, 0.008, 0.024):
        T([(-0.16, -0.085, dz), (0.98, -0.045, dz * 0.7)], [0.0055, 0.0055], string, uk, caps=False)
    u_loc, u_rot = Vector((-0.05, -0.62, 0.78)), Euler((0, -0.5, 0.15))
    uk.location, uk.rotation_euler = u_loc, u_rot
    bpy.context.view_layer.update()
    M = Matrix.Translation(u_loc) @ u_rot.to_matrix().to_4x4()

    arms = {}
    for sx, side in ((1, "L"), (-1, "R")):
        sh = Vector((sx * 0.4, -0.12, 1.02))
        ap = b3.pivot(f"arm_{side}", sh, body)
        hand = M @ (Vector((0.72, -0.05, 0)) if side == "L" else Vector((0.06, -0.12, 0.05)))
        elbow = sh.lerp(hand, 0.5) + Vector((sx * 0.18, -0.05, -0.12))
        T([tuple(sh), tuple(elbow), tuple(hand)], [0.075, 0.065, 0.06], green, ap)
        E(tuple(hand), (0.1, 0.09, 0.09), dark, ap)
        arms[side] = ap
    root.scale = (CHAR_SCALE,) * 3
    return dict(root=root, body=body, head=head, eyes=eyes, arms=arms)


def animate_cigarra(P, frames):
    for f in range(1, frames + 1):
        t = (f - 1) / FPS
        beat = 2 * math.pi * 2.0 * t                                  # 120 bpm
        P["body"].rotation_euler = (0, math.radians(3 * math.sin(2 * math.pi * 0.5 * t)), 0)
        P["body"].scale = (1, 1, 1 + 0.02 * math.sin(beat / 2))
        P["head"].rotation_euler = (math.radians(4 * max(0, math.sin(beat / 2))), 0,
                                    math.radians(6 * math.sin(2 * math.pi * 0.25 * t)))
        P["arms"]["R"].rotation_euler = (math.radians(14 * math.sin(beat * 2)), 0, 0)   # dedilhado
        P["arms"]["L"].rotation_euler = (0, 0, math.radians(2 * math.sin(beat)))
        for o in ("body", "head"):
            P[o].keyframe_insert("rotation_euler", frame=f)
        P["body"].keyframe_insert("scale", frame=f)
        for a in P["arms"].values():
            a.keyframe_insert("rotation_euler", frame=f)
        bl = {0: 0.5, 1: 0.1, 2: 0.1, 3: 0.5}.get(f - 1 - int(3.0 * FPS), 1.0)
        for e in P["eyes"]:
            e.scale = (1, 1, bl)
            e.keyframe_insert("scale", frame=f)


# ------------------------------------------------------------------ ambiente Poly Haven
def load_templates(name):
    path = ASSETS / name / f"{name}_1k.blend"

    def keep(n):
        bad = ("geonodes", "geometry_nodes", "Plane")
        return ("LOD0" in n or "LOD" not in n) and not any(b in n for b in bad)
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if keep(n)]
    return [o for o in dst.objects if o is not None and o.type == "MESH" and o.dimensions.z > 1e-4]


def place(tpl, loc, height, rng, coll):
    o = tpl.copy()
    coll.objects.link(o)
    o.parent = None
    o.location = loc
    o.rotation_euler = (tpl.rotation_euler.x, tpl.rotation_euler.y, rng.uniform(0, 2 * math.pi))
    k = height / tpl.dimensions.z
    o.scale = tuple(s * k for s in tpl.scale)
    return o


def build_environment(rng):
    coll = bpy.context.scene.collection
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(ground_mat())

    T_ = {n: load_templates(n) for n in ("grass_medium_01", "grass_medium_02", "dandelion_01", "periwinkle_plant",
                                         "flower_gazania", "shrub_sorrel_01", "fern_02", "rock_moss_set_01",
                                         "moss_01", "stone_01")}
    rocks = sorted(T_["rock_moss_set_01"], key=lambda o: -o.dimensions.x * o.dimensions.y)
    hero = place(rocks[0], (0, 0, 0), 0.042, rng, coll)
    hero.rotation_euler.z = 0.6

    def clear(x, y):
        """Dentro do cone de visão da câmera (y≈-0.23, meia-abertura ~0.2) e na frente da personagem."""
        return y < 0.04 and abs(x) < 0.2 * (y + 0.23) + 0.13

    seeds = iter(range(100, 200))

    def scatter(names, n, rmin, rmax, hmin, hmax, ymin=-9.0, low=False):
        rng = random.Random(next(seeds))          # sorteio próprio: mexer num grupo não reembaralha os outros
        pool = [t for nm in names for t in T_[nm]]
        k = 0
        while k < n:
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(rmin, rmax)
            x, y = r * math.cos(a), r * math.sin(a) + 0.15
            if (clear(x, y) and not low) or y < ymin:
                continue
            place(rng.choice(pool), (x, y, 0), rng.uniform(hmin, hmax), rng, coll)
            k += 1
    scatter(["moss_01"], 900, 0.03, 0.45, 0.01, 0.025, low=True)      # musgo baixo pode ficar na frente
    scatter(["grass_medium_01", "grass_medium_02"], 260, 0.06, 1.2, 0.07, 0.22)
    scatter(["periwinkle_plant", "flower_gazania", "shrub_sorrel_01"], 45, 0.1, 0.9, 0.08, 0.17, ymin=0.0)
    scatter(["dandelion_01"], 25, 0.1, 1.0, 0.1, 0.18, ymin=0.0)
    scatter(["fern_02"], 18, 0.35, 1.4, 0.2, 0.4, ymin=0.25)
    scatter(["grass_medium_01", "grass_medium_02", "periwinkle_plant"], 90, 0.25, 0.9, 0.15, 0.32, ymin=0.2)
    scatter(["rock_moss_set_01", "stone_01"], 8, 0.15, 0.7, 0.02, 0.06, ymin=0.05)
    for x, y, nm, h in ((-0.11, -0.13, "dandelion_01", 0.1), (0.12, -0.12, "grass_medium_01", 0.11)):                 # primeiro plano desfocado
        place(rng.choice(T_[nm]), (x, y, 0), h, rng, coll)
    return hero


def setup_world_and_light():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("world")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(ASSETS / "hdri" / "golf_course_sunrise_2k.exr"))
    mp = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # Blender: u = 0.5 - atan2(y, x) / 2pi  ->  gira o HDRI para o sol dele cair em SUN_DIR
    theta_sun = (0.5 - HDRI_SUN_U) * 2 * math.pi
    mp.inputs["Rotation"].default_value = (0, 0, theta_sun - math.atan2(SUN_DIR.y, SUN_DIR.x))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0

    L = bpy.data.lights.new("sun", "SUN")
    L.energy = 4.0
    L.angle = math.radians(2.5)
    L.color = (1.0, 0.82, 0.6)
    o = bpy.data.objects.new("sun", L)
    sc.collection.objects.link(o)
    o.rotation_euler = (-SUN_DIR).to_track_quat("-Z", "Y").to_euler()   # contraluz dourado (= sol do HDRI)


def add_fill(target):
    """Luz de preenchimento suave e quente no rosto (como em filme de animação)."""
    L = bpy.data.lights.new("fill", "AREA")
    L.energy = 2.0
    L.size = 0.12
    L.color = (1.0, 0.9, 0.78)
    o = bpy.data.objects.new("fill", L)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(target) + Vector((-0.16, -0.2, 0.09))
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


def setup_camera(target, frames):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("cam")
    cd.lens = 50
    cd.sensor_width = 36
    cd.clip_start = 0.005
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.8
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    focus = bpy.data.objects.new("focus", None)
    sc.collection.objects.link(focus)
    focus.location = target
    cd.dof.focus_object = focus
    for f in (1, frames):                                             # dolly lento para dentro
        k = (f - 1) / max(1, frames - 1)
        cam.location = Vector(target) + Vector((0.015 - 0.025 * k, -0.23 + 0.04 * k, 0.004))
        cam.rotation_euler = (Vector(target) + Vector((0, 0, 0.004)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


def setup_cycles(res, samples, frames):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                break
        except TypeError:
            continue
    for d in prefs.devices:
        d.use = d.type != "CPU"
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.transparent_max_bounces = 24
    sc.render.use_persistent_data = True                       # não reconstrói a cena (1.500 plantas) a cada quadro
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = int(res * 9 / 16) // 2 * 2, res
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, frames
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.render.image_settings.file_format = "PNG"
    print("devices:", [(d.name, d.type, d.use) for d in prefs.devices])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", default="")
    ap.add_argument("--res", type=int, default=1920, help="altura em px (largura = 9:16); 1920 = Shorts")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--frames", type=int, default=144)
    ap.add_argument("--range", default="", help="ex.: 1,5 renderiza só esse trecho")
    args = ap.parse_args(argv)

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    rng = random.Random(7)
    hero = build_environment(rng)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((0, 0, 1)), Vector((0, 0, -1)))
    top = loc.z if hit else 0.04
    P = cigarra()
    P["root"].location = (0, 0, top + 0.006)
    P["root"].rotation_euler = (0, 0, math.radians(-12))
    animate_cigarra(P, args.frames)
    setup_world_and_light()
    mid_h = top + 0.006 + 1.0 * CHAR_SCALE                    # meio do corpo: personagem inteira no quadro
    setup_camera((0, -0.015, mid_h), args.frames)
    add_fill((0, -0.015, mid_h + 0.5 * CHAR_SCALE))
    setup_cycles(args.res, args.samples, args.frames)

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    t0 = time.time()
    if args.still:
        for fr in (int(x) for x in args.still.split(",")):
            sc.frame_set(fr)
            sc.render.filepath = str(out / f"cena1_still_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"still {fr}: {time.time() - t0:.1f}s")
    else:
        (out / "cena1").mkdir(exist_ok=True)
        if args.range:
            sc.frame_start, sc.frame_end = (int(x) for x in args.range.split(","))
        sc.render.filepath = str(out / "cena1" / "f_####")
        bpy.ops.render.render(animation=True)
    print(f"TOTAL {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
