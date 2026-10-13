"""Qual é a sombra? — Short infantil 9:16 gerado 100% por código (PIL + numpy + ffmpeg).

Começa START s adiantado para o 1º quadro já mostrar a silhueta (gancho/miniatura);
o loop continua perfeito porque vídeo e áudio são rotacionados juntos.

Uso:  python sombra.py            -> out/qual_e_a_sombra_01.mp4 (bichos 2D desenhados aqui)
      python sombra.py --3d       -> out/qual_e_a_sombra_01_3d.mp4 (loops de out/3d/<bicho>/, gerados por bichos3d.py)
"""
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
W, H, FPS = 1080, 1920, 30
SEG = 6.0                      # segundos por bicho
SS = 2                         # supersampling do desenho dos bichos
FONT_PATH = "C:/Windows/Fonts/ariblk.ttf"
INK = (34, 34, 59)             # contorno e silhueta
PURPLE = (59, 31, 107)
WHITE = (255, 255, 255)

ANIM_CX, ANIM_CY, BASE = 540, 1100, 0.85   # sprite 800x1000 -> 680x850 na tela
TITLE_Y, COUNT_Y = 300, 565


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x):
    x = clamp(x)
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_in_out(x):
    return 0.5 - 0.5 * math.cos(math.pi * clamp(x))


# ------------------------------------------------------------------ desenho
class Pen:
    def __init__(self, w=800, h=1000):
        self.img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def ellipse(self, cx, cy, rx, ry, fill, ow=0):
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS],
                       fill=fill, outline=INK if ow else None, width=ow * SS)

    def circle(self, cx, cy, r, fill, ow=0):
        self.ellipse(cx, cy, r, r, fill, ow)

    def poly(self, pts, fill, ow=0):
        self.d.polygon(self._p(pts), fill=fill, outline=INK if ow else None, width=ow * SS)

    def rrect(self, x0, y0, x1, y1, r, fill, ow=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS,
                                 fill=fill, outline=INK if ow else None, width=ow * SS)

    def line(self, pts, width, fill=INK):
        self.d.line(self._p(pts), fill=fill, width=int(width * SS), joint="curve")
        for x, y in (pts[0], pts[-1]):
            self.circle(x, y, width / 2, fill)

    def tube(self, pts, r0, r1, fill):
        n = len(pts)
        for i, (x, y) in enumerate(pts):
            self.circle(x, y, r0 + (r1 - r0) * i / max(1, n - 1), fill)

    def eye(self, cx, cy, r, look=(0, 0), iris=None):
        self.circle(cx, cy, r, WHITE, ow=4)
        px, py = cx + look[0], cy + look[1]
        if iris:
            self.circle(px, py, r * 0.8, iris)
            self.ellipse(px, py, r * 0.3, r * 0.7, INK)
        else:
            self.circle(px, py, r * 0.62, INK)
        self.circle(px - r * 0.25, py - r * 0.3, r * 0.24, WHITE)


def bezier(p0, p1, p2, p3, n=80):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def clip_layer(pen, draw_fn):
    """Desenha numa camada recortada pelo que já existe (ex.: manchas da girafa)."""
    layer = Pen()
    draw_fn(layer)
    a = ImageChops.multiply(layer.img.split()[3], pen.img.split()[3])
    layer.img.putalpha(a)
    pen.img.alpha_composite(layer.img)


def finish(pen, overlay=None):
    """Contorno externo grosso + downscale. Retorna (colorido, silhueta).
    `overlay` desenha detalhes finos (bigodes) por cima, fora do contorno."""
    a = pen.img.split()[3]
    grown = a.filter(ImageFilter.GaussianBlur(7 * SS)).point(lambda v: 255 if v > 6 else 0)
    grown = grown.filter(ImageFilter.GaussianBlur(1.2 * SS))
    out = Image.new("RGBA", pen.img.size, INK + (0,))
    out.putalpha(grown)
    out.alpha_composite(pen.img)
    if overlay:
        top = Pen()
        overlay(top)
        out.alpha_composite(top.img)
    out = out.resize((out.width // SS, out.height // SS), Image.LANCZOS)
    sil = Image.new("RGBA", out.size, INK + (0,))
    sil.putalpha(out.split()[3])
    return out, sil


def draw_elefante():
    p = Pen()
    body, dark, ear = hexc("#8EA8D6"), hexc("#7390C2"), hexc("#A3BAE2")
    pink = hexc("#F7A8C4")
    for x in (330, 590):                                   # pernas do fundo
        p.rrect(x, 640, x + 75, 900, 32, dark)
    p.tube(bezier((670, 580), (700, 610), (720, 650), (735, 690), 30), 11, 9, body)
    p.ellipse(738, 705, 16, 24, dark)
    p.ellipse(440, 600, 255, 180, body)                     # corpo
    for x in (250, 500):                                   # pernas da frente
        p.rrect(x, 650, x + 82, 915, 34, body)
        for k in range(3):
            p.ellipse(x + 18 + k * 23, 900, 9, 7, WHITE)
    p.tube(bezier((120, 470), (40, 600), (60, 760), (150, 745), 90), 54, 27, body)  # tromba
    p.circle(230, 430, 165, body)                           # cabeça
    p.ellipse(370, 435, 118, 148, ear, ow=5)                # orelha
    p.ellipse(380, 440, 78, 108, pink)
    p.ellipse(158, 488, 30, 18, pink)                       # bochecha
    p.eye(200, 395, 38, look=(-7, 2))
    p.line([(232, 520), (262, 534), (292, 524)], 7)         # sorriso
    return finish(p)


def draw_gato():
    p = Pen()
    orange, dark, light = hexc("#F7A440"), hexc("#D9802A"), hexc("#FFE3C2")
    pink, green = hexc("#FF9FB8"), hexc("#7ED957")
    p.tube(bezier((560, 880), (770, 870), (770, 600), (640, 520)), 34, 30, orange)  # rabo
    p.ellipse(400, 720, 210, 220, orange)                   # corpo
    p.ellipse(400, 775, 120, 150, light)                    # barriga
    for x in (315, 485):
        p.ellipse(x, 925, 75, 45, light, ow=5)              # patinhas
    for sx in (1, -1):                                      # orelhas
        m = (lambda x: x) if sx == 1 else (lambda x: 800 - x)
        p.poly([(m(205), 370), (m(215), 135), (m(360), 265)], orange)
        p.poly([(m(235), 325), (m(240), 190), (m(320), 272)], pink)
    p.ellipse(400, 420, 225, 185, orange)                   # cabeça
    for x0 in (382, 330, 434):                              # listras
        p.rrect(x0, 240, x0 + 36, 300 if x0 == 382 else 285, 16, dark)
    for x in (360, 440):
        p.ellipse(x, 505, 55, 40, light)                    # focinho
    p.poly([(378, 470), (422, 470), (400, 494)], pink)      # nariz
    p.line([(400, 494), (400, 515)], 6)
    p.line([(400, 515), (380, 530), (362, 518)], 6)
    p.line([(400, 515), (420, 530), (438, 518)], 6)
    p.ellipse(268, 478, 28, 16, pink)
    p.ellipse(532, 478, 28, 16, pink)
    p.eye(320, 405, 50, look=(0, 3), iris=green)
    p.eye(480, 405, 50, look=(0, 3), iris=green)

    def bigodes(o):
        for m in (lambda x: x, lambda x: 800 - x):
            o.line([(m(300), 500), (m(150), 475)], 6)
            o.line([(m(300), 520), (m(145), 532)], 6)
    return finish(p, bigodes)


def draw_girafa():
    p = Pen()
    yellow, far, light = hexc("#F9C846"), hexc("#E3AE35"), hexc("#FCE3A0")
    spot, hoof, pink = hexc("#C9732A"), hexc("#6B3E1E"), hexc("#FF9FB8")
    for x in (355, 620):                                    # pernas do fundo
        p.rrect(x, 700, x + 46, 955, 20, far)
        p.rrect(x, 915, x + 46, 960, 12, hoof)
    p.tube(bezier((675, 640), (695, 690), (710, 740), (718, 780), 30), 8, 7, yellow)
    p.ellipse(720, 798, 15, 26, spot)
    p.ellipse(470, 660, 212, 115, yellow)                   # corpo
    for x in (290, 545):                                    # pernas da frente
        p.rrect(x, 700, x + 52, 965, 22, yellow)
        p.rrect(x, 925, x + 52, 970, 12, hoof)
    p.poly([(335, 232), (362, 230), (428, 592), (402, 602)], spot)  # crina
    p.poly([(268, 645), (402, 605), (334, 228), (222, 248)], yellow)  # pescoço

    def spots(l):
        for (x, y, rx, ry) in [(380, 625, 42, 30), (470, 690, 46, 32), (565, 620, 40, 28),
                               (630, 705, 30, 24), (330, 705, 34, 25), (505, 590, 30, 20),
                               (300, 570, 30, 24), (320, 470, 28, 22), (290, 375, 24, 20),
                               (320, 300, 20, 16), (360, 535, 22, 18), (400, 740, 26, 18)]:
            l.ellipse(x, y, rx, ry, spot)
    clip_layer(p, spots)

    p.tube(bezier((238, 150), (234, 120), (230, 95), (225, 72), 20), 11, 10, yellow)  # ossicones
    p.tube(bezier((292, 150), (295, 120), (298, 95), (300, 74), 20), 11, 10, yellow)
    p.circle(225, 64, 20, spot)
    p.circle(300, 66, 20, spot)
    p.ellipse(348, 172, 50, 22, yellow, ow=5)               # orelha
    p.ellipse(352, 172, 30, 11, pink)
    p.ellipse(250, 210, 115, 78, yellow)                    # cabeça
    p.ellipse(162, 240, 74, 56, light)                      # focinho
    p.ellipse(128, 228, 9, 6, hoof)
    p.line([(118, 268), (155, 282), (195, 274)], 6)
    p.ellipse(205, 250, 22, 13, pink)
    p.eye(250, 192, 28, look=(-5, 1))
    return finish(p)


ANIMALS = [
    dict(key="elefante", name="ELEFANTE", art="O", draw=draw_elefante, bg=("#FFD84D", "#FFC530")),
    dict(key="gato", name="GATO", art="O", draw=draw_gato, bg=("#7FD8F5", "#5BC6EF")),
    dict(key="girafa", name="GIRAFA", art="A", draw=draw_girafa, bg=("#B8E986", "#9BDA66")),
]
N = len(ANIMALS)
DUR = N * SEG
START = 0.3                    # deslocamento do loop (ver docstring)
MODE3D = "--3d" in sys.argv


# ------------------------------------------------------------------ texto/sprites
_fonts = {}


def font(sz):
    if sz not in _fonts:
        _fonts[sz] = ImageFont.truetype(FONT_PATH, sz)
    return _fonts[sz]


def text_sprite(lines, fill=WHITE, stroke=PURPLE, sw=14, gap=6, maxw=1000):
    imgs = []
    for txt, sz in lines:
        f = font(sz)
        bb = f.getbbox(txt, stroke_width=sw)
        im = Image.new("RGBA", (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4))
        ImageDraw.Draw(im).text((-bb[0] + 2, -bb[1] + 2), txt, font=f, fill=fill,
                                stroke_width=sw, stroke_fill=stroke)
        imgs.append(im)
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    body = Image.new("RGBA", (w, h))
    y = 0
    for im in imgs:
        body.paste(im, ((w - im.width) // 2, y))
        y += im.height + gap
    out = Image.new("RGBA", (w, h + 12))                    # sombra projetada
    sh = Image.new("RGBA", body.size, INK + (0,))
    sh.putalpha(body.split()[3].point(lambda v: v * 0.35))
    out.alpha_composite(sh, (0, 12))
    out.alpha_composite(body, (0, 0))
    if out.width > maxw:
        out = out.resize((maxw, int(out.height * maxw / out.width)), Image.LANCZOS)
    return out


def count_sprite(n):
    r = 88
    im = Image.new("RGBA", (2 * r * SS + 40, 2 * r * SS + 40))
    d = ImageDraw.Draw(im)
    c = im.width // 2
    d.ellipse([c - r * SS, c - r * SS, c + r * SS, c + r * SS], fill=WHITE, outline=PURPLE, width=12 * SS)
    f = ImageFont.truetype(FONT_PATH, 120 * SS)
    d.text((c, c + 4 * SS), str(n), font=f, fill=hexc("#FF5A5F"), anchor="mm")
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)


def shadow_sprite():
    im = Image.new("RGBA", (640, 140))
    ImageDraw.Draw(im).ellipse([40, 30, 600, 110], fill=INK + (70,))
    return im.filter(ImageFilter.GaussianBlur(12))


def paste_center(frame, img, cx, cy, scale=1.0, angle=0.0):
    if scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if abs(angle) > 0.05:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    frame.paste(img, (int(cx - img.width / 2), int(cy - img.height / 2)), img)


def background(t, c1, c2):
    small = Image.new("RGB", (W // 2, H // 2), hexc(c1))
    d = ImageDraw.Draw(small)
    cx, cy, R = ANIM_CX // 2, ANIM_CY // 2, 1400
    a0 = math.radians(t * 14)
    for k in range(12):
        a = a0 + k * math.pi / 6
        b = a + math.pi / 12
        d.polygon([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a)),
                   (cx + R * math.cos(b), cy + R * math.sin(b))], fill=hexc(c2))
    return small.resize((W, H), Image.BILINEAR)


def make_confetti(seed):
    rng = random.Random(seed)
    cols = ["#FF5A5F", "#FFD84D", "#4DD599", "#4DA6FF", "#B57BFF", "#FF9F43", "#FFFFFF"]
    parts = []
    for _ in range(140):
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
        sp = rng.uniform(700, 1650)
        parts.append(dict(x=ANIM_CX + rng.uniform(-60, 60), y=ANIM_CY + rng.uniform(-80, 40),
                          vx=math.cos(ang) * sp, vy=math.sin(ang) * sp,
                          rot=rng.uniform(0, 6.28), vr=rng.uniform(-12, 12),
                          w=rng.uniform(14, 24), h=rng.uniform(8, 14), c=hexc(rng.choice(cols))))
    return parts


def draw_confetti(frame, parts, r):
    d = ImageDraw.Draw(frame)
    for p in parts:
        x = p["x"] + p["vx"] * r * (1 - 0.25 * r)
        y = p["y"] + p["vy"] * r + 0.5 * 2300 * r * r
        if y > H + 40:
            continue
        a = p["rot"] + p["vr"] * r
        w, h = p["w"] * abs(math.cos(a * 1.7)) + 3, p["h"]
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x + dx * ca - dy * sa, y + dx * sa + dy * ca)
               for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
        d.polygon(pts, fill=p["c"])


# ------------------------------------------------------------------ cena
def build_assets():
    A = {"title": text_sprite([("QUAL É A", 120), ("SOMBRA?", 150)]),
         "q": text_sprite([("?", 190)], fill=hexc("#FFFFFF")),
         "count": {n: count_sprite(n) for n in (1, 2, 3)},
         "shadow": shadow_sprite(), "animals": []}
    for i, an in enumerate(ANIMALS):
        if MODE3D:
            col = [Image.open(f).convert("RGBA") for f in sorted((OUT / "3d" / an["key"]).glob("f_*.png"))]
            assert col, f"rode bichos3d.py para {an['key']} antes"
        else:
            col = [an["draw"]()[0]]
        sil = []
        for c in col:
            sl = Image.new("RGBA", c.size, INK + (0,))
            sl.putalpha(c.split()[3])
            sil.append(sl)
        A["animals"].append(dict(col=col, sil=sil,
                                 name=text_sprite([(f"É {an['art']}", 110), (f"{an['name']}!", 165)]),
                                 confetti=make_confetti(100 + i)))
    return A


def frame_at(t, A):
    seg = int(t // SEG) % N
    lt = t - int(t // SEG) * SEG
    an, nxt = ANIMALS[seg], ANIMALS[(seg + 1) % N]
    asset = A["animals"][seg]

    f = background(t, *an["bg"])
    if lt > 5.7:
        f = Image.blend(f, background(t, *nxt["bg"]), ease_in_out((lt - 5.7) / 0.3))

    revealed = lt >= 3.5
    r = lt - 3.5
    s = BASE * (ease_out_back(lt / 0.5) if lt < 0.5 else 1.0)
    angle, dy = 0.0, 0.0
    if not revealed and lt >= 0.5:
        angle = 4 * math.sin((lt - 0.5) * 2 * math.pi * 0.8)
    if revealed:
        s = BASE * (1 + 0.16 * math.exp(-5 * r) * math.sin(14 * r))
        if r > 0.8:
            dy = -48 * abs(math.sin((r - 0.8) * math.pi * 1.6))
    if lt > 5.7:
        s *= 1 - ease_in_out((lt - 5.7) / 0.3)

    fi = int(round(t * FPS)) % len(asset["col"])
    sprite = (asset["col"] if revealed else asset["sil"])[fi]
    ground = ANIM_CY + 1000 * s / 2 - 25 * (s / BASE)
    paste_center(f, A["shadow"], ANIM_CX, ground, scale=(s / BASE) * (1 + dy / 300))
    paste_center(f, sprite, ANIM_CX, ANIM_CY + dy, scale=s, angle=angle)

    if 0 <= r < 0.3:                                        # flash da revelação
        f = Image.blend(f, Image.new("RGB", f.size, WHITE), 0.85 * (1 - r / 0.3))
    if revealed and lt < 5.7:
        draw_confetti(f, asset["confetti"], r)

    # "?" flutuando durante o palpite
    if 0.3 <= lt < 3.5:
        qs = ease_out_back((lt - 0.3) / 0.35)
        paste_center(f, A["q"], 150, 930 + 22 * math.sin(lt * 4), qs, angle=12)
        paste_center(f, A["q"], 935, 1020 + 22 * math.sin(lt * 4 + 2), qs, angle=-12)

    # título / nome
    if lt < 3.5:
        paste_center(f, A["title"], 540, TITLE_Y, 1 + 0.035 * math.sin(lt * 2 * math.pi * 1.5))
    elif lt < 5.85:
        ns = ease_out_back((lt - 3.55) / 0.35) if lt < 5.7 else 1 - (lt - 5.7) / 0.15
        paste_center(f, asset["name"], 540, TITLE_Y, max(0, ns))
    else:
        paste_center(f, A["title"], 540, TITLE_Y, ease_out_back((lt - 5.85) / 0.15))

    # contagem 3-2-1
    if 0.5 <= lt < 3.5:
        k = int(lt - 0.5)
        u = (lt - 0.5) - k
        paste_center(f, A["count"][3 - k], 540, COUNT_Y, 1 + 0.35 * math.exp(-10 * u))
    return f


# ------------------------------------------------------------------ áudio
SR = 44100


def env_t(dur):
    return np.arange(int(SR * dur)) / SR


def tone(freq, dur, kind="sine", decay=8.0, vol=0.5):
    t = env_t(dur)
    ph = 2 * np.pi * freq * t
    w = {"sine": np.sin(ph), "tri": 2 / np.pi * np.arcsin(np.sin(ph)),
         "square": 0.5 * np.sign(np.sin(ph))}[kind]
    return w * np.exp(-decay * t) * np.minimum(1, t / 0.004) * vol


def sweep(f0, f1, dur, vol, wobble=0.0):
    t = env_t(dur)
    fr = f0 * (f1 / f0) ** (t / dur) * (1 + wobble * np.sin(2 * np.pi * 18 * t))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * np.sin(np.pi * t / dur) * vol


def noise(dur, decay, vol, seed=0, hp=True):
    rng = np.random.default_rng(seed)
    n = rng.standard_normal(int(SR * dur))
    if hp:
        n = np.diff(n, prepend=0)
    return n * np.exp(-decay * env_t(dur)) * vol * 0.5


def add(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[:j - i]


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def add_music(buf):
    """Trilha de 18 s (9 compassos a 120 bpm) que fecha o loop voltando para Dó."""
    bar, beat = 2.0, 0.5
    prog = [(60, "M"), (57, "m"), (53, "M"), (55, "M"), (60, "M"), (57, "m"), (53, "M"), (55, "M"), (55, "M")]
    for b, (root, q) in enumerate(prog):
        third = 4 if q == "M" else 3
        arp = [0, third, 7, 12, 7, third, 7, 12]
        t0 = b * bar
        for k, iv in enumerate(arp):
            add(buf, tone(midi(root + 12 + iv), 0.4, "tri", 7, 0.10), t0 + k * beat / 2)
        for k in range(4):
            if k % 2 == 0:
                add(buf, sweep(130, 45, 0.14, 0.45), t0 + k * beat)
                add(buf, tone(midi(root - 12), 0.45, "sine", 4, 0.22), t0 + k * beat)
            add(buf, noise(0.05, 70, 0.05, seed=b * 10 + k), t0 + k * beat + beat / 2)


def build_audio(path):
    buf = np.zeros(int(SR * DUR) + SR)
    add_music(buf)
    for s in range(N):
        b0 = s * SEG
        add(buf, sweep(240, 720, 0.32, 0.35, wobble=0.06), b0)              # boing
        for k in range(3):
            fq = 1400 if k == 2 else 1000
            add(buf, tone(fq, 0.12, "tri", 40, 0.38) + tone(fq * 1.5, 0.12, "sine", 50, 0.12), b0 + 0.5 + k)
        add(buf, noise(0.08, 50, 0.6, seed=99 + s, hp=False), b0 + 3.5)     # pop
        for k, m in enumerate((84, 88, 91, 96)):                             # tchan!
            add(buf, tone(midi(m), 0.9, "tri", 4, 0.22), b0 + 3.5 + k * 0.05)
        add(buf, noise(0.7, 5, 0.07, seed=7 + s), b0 + 3.52)                 # brilho
        add(buf, sweep(900, 260, 0.3, 0.18), b0 + 5.7)                       # swoosh
    write_wav(path, np.roll(buf[:int(SR * DUR)], -int(SR * START)))


def write_wav(path, buf):
    buf = buf / np.max(np.abs(buf)) * 0.9
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ main
def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "check").mkdir(exist_ok=True)
    audio = OUT / "audio.wav"
    build_audio(audio)
    A = build_assets()
    for i, a in enumerate(A["animals"]):
        a["col"][0].save(OUT / "check" / f"bicho_{i}.png")
    mp4 = OUT / ("qual_e_a_sombra_01_3d.mp4" if MODE3D else "qual_e_a_sombra_01.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    checks = {round(x * FPS) for x in (0.0, 0.25, 1.0, 2.7, 3.55, 3.8, 4.8, 5.8, 7.0, 10.0, 13.0, 16.0)}
    total = int(DUR * FPS)
    for i in range(total):
        fr = frame_at((i / FPS + START) % DUR, A)
        if i in checks:
            fr.save(OUT / "check" / f"f_{i:04d}.png")
        ff.stdin.write(fr.tobytes())
        if i % 90 == 0:
            print(f"frame {i}/{total}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("ok ->", mp4)


if __name__ == "__main__":
    main()
