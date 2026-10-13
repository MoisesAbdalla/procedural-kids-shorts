"""Ovo surpresa — Short infantil 9:16. Compõe os renders 3D de ovo3d.py (out/3d/ovo<N>/) com fundo,
textos, "TOC!", confete e áudio. Reaproveita os utilitários de ../qual-e-a-sombra/sombra.py.

Uso:  python ovo.py   -> out/ovo_surpresa_01.mp4 (+ out/check/*.png)
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "qual-e-a-sombra"))
from sombra import (FPS, H, SR, W, add, add_music, background, draw_confetti, ease_in_out,  # noqa: E402
                    ease_out_back, hexc, make_confetti, noise, paste_center, shadow_sprite, sweep,
                    text_sprite, tone, midi, write_wav)

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SEG = 6.0
T_BURST = 3.0
KNOCKS = (1.0, 1.8, 2.5)              # mesmos tempos do ovo3d.py
START = 0.3
CX, CY, BASE = 540, 1080, 0.92        # sprite 800x1000 -> 736x920
TITLE_Y = 300

EGGS = [
    dict(art="É UM", name="PINTINHO!", bg=("#FF9EC7", "#FF85B8")),
    dict(art="É UM", name="DINOSSAURO!", bg=("#7FD8F5", "#5BC6EF")),
    dict(art="É UMA", name="TARTARUGA!", bg=("#C9A7FF", "#B48CFF")),
]
N = len(EGGS)
DUR = N * SEG
TOC_POS = [(205, 760, 14), (875, 700, -12), (215, 640, 10)]


def build_assets():
    A = {"title": text_sprite([("O QUE TEM", 115), ("NO OVO?", 150)]),
         "toc": text_sprite([("TOC!", 105)], fill=hexc("#FFE14D")),
         "shadow": shadow_sprite(), "eggs": []}
    for i, e in enumerate(EGGS):
        frames = [Image.open(f).convert("RGBA") for f in sorted((OUT / "3d" / f"ovo{i}").glob("f_*.png"))]
        assert len(frames) == int(SEG * FPS), f"ovo{i}: rode ovo3d.py antes ({len(frames)} quadros)"
        A["eggs"].append(dict(frames=frames, name=text_sprite([(e["art"], 110), (e["name"], 160)]),
                              confetti=make_confetti(200 + i)))
    return A


def frame_at(t, A):
    seg = int(t // SEG) % N
    lt = t - int(t // SEG) * SEG
    e, nxt, asset = EGGS[seg], EGGS[(seg + 1) % N], A["eggs"][seg]

    f = background(t, *e["bg"])
    if lt > 5.7:
        f = Image.blend(f, background(t, *nxt["bg"]), ease_in_out((lt - 5.7) / 0.3))

    s = BASE * (ease_out_back(lt / 0.35) if lt < 0.35 else 1.0)
    if lt > 5.7:
        s *= 1 - ease_in_out((lt - 5.7) / 0.3)
    sprite = asset["frames"][min(int(lt * FPS), len(asset["frames"]) - 1)]
    paste_center(f, A["shadow"], CX, CY + (500 - 70) * s, scale=s / BASE * 1.05)
    paste_center(f, sprite, CX, CY, scale=s)

    r = lt - T_BURST
    if 0 <= r < 0.3:
        f = Image.blend(f, Image.new("RGB", f.size, (255, 255, 255)), 0.8 * (1 - r / 0.3))
    if 0 <= r and lt < 5.7:
        draw_confetti(f, asset["confetti"], r)

    for k, kt in enumerate(KNOCKS):                         # balões "TOC!"
        u = lt - kt
        if 0 <= u < 0.6:
            sc = ease_out_back(u / 0.18) if u < 0.45 else 1 - (u - 0.45) / 0.15
            x, y, ang = TOC_POS[k]
            paste_center(f, A["toc"], x, y - 40 * u, max(0, sc), angle=ang)

    if lt < T_BURST:
        paste_center(f, A["title"], 540, TITLE_Y, 1 + 0.035 * math.sin(lt * 2 * math.pi * 1.5))
    elif lt < 5.85:
        ns = ease_out_back((lt - T_BURST - 0.05) / 0.35) if lt < 5.7 else 1 - (lt - 5.7) / 0.15
        paste_center(f, asset["name"], 540, TITLE_Y, max(0, ns))
    else:
        paste_center(f, A["title"], 540, TITLE_Y, ease_out_back((lt - 5.85) / 0.15))
    return f


def build_audio(path):
    buf = np.zeros(int(SR * DUR) + SR)
    add_music(buf)
    for s in range(N):
        b0 = s * SEG
        add(buf, sweep(240, 720, 0.32, 0.35, wobble=0.06), b0)               # boing
        for kt in KNOCKS:                                                     # toc toc
            add(buf, tone(520, 0.15, "tri", 35, 0.5), b0 + kt)
            add(buf, tone(780, 0.1, "sine", 45, 0.2), b0 + kt)
        for k in range(14):                                                   # rachando...
            add(buf, noise(0.025, 120, 0.25 + 0.02 * k, seed=300 + s * 20 + k), b0 + 2.2 + k * 0.055)
        add(buf, noise(0.1, 40, 0.7, seed=99 + s, hp=False), b0 + T_BURST)    # pop
        for k, m in enumerate((84, 88, 91, 96)):                              # tchan!
            add(buf, tone(midi(m), 0.9, "tri", 4, 0.22), b0 + T_BURST + k * 0.05)
        add(buf, noise(0.7, 5, 0.07, seed=7 + s), b0 + T_BURST + 0.02)        # brilho
        add(buf, sweep(900, 260, 0.3, 0.18), b0 + 5.7)                        # swoosh
    write_wav(path, np.roll(buf[:int(SR * DUR)], -int(SR * START)))


def main():
    (OUT / "check").mkdir(parents=True, exist_ok=True)
    audio = OUT / "audio.wav"
    build_audio(audio)
    A = build_assets()
    mp4 = OUT / "ovo_surpresa_01.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    checks = {round(x * FPS) for x in (0.0, 1.1, 2.6, 3.05, 3.4, 4.5, 5.85, 7.0, 9.2, 10.5, 15.2, 16.5)}
    total = int(DUR * FPS)
    for i in range(total):
        fr = frame_at((i / FPS + START) % DUR, A)
        if i in checks:
            fr.save(OUT / "check" / f"f_{i:04d}.png")
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    print("ok ->", mp4)


if __name__ == "__main__":
    main()
