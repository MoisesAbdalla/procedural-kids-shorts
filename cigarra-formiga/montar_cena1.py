"""Monta a cena 1 renderizada no Blender (out/blender/cena1/f_####.png) em MP4 com trilha e legenda.

Trilha 100% gerada aqui: ukulele (corda pinçada Karplus-Strong, C-Am-F-G a 120 bpm), passarinhos e vento.
Uso:  python montar_cena1.py  -> out/cena1_blender.mp4
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parent / "qual-e-a-sombra"))
from sombra import SR, add, midi, write_wav  # noqa: E402

FPS, DUR = 24, 6.0
W, H = 1080, 1920
LEGENDA = "Era verão, e a Cigarra passava o dia inteiro cantando e tocando."
FONT = "C:/Windows/Fonts/seguibl.ttf"


def pluck(freq, dur, vol, bright=0.5, seed=0):
    """Corda pinçada (Karplus-Strong), calculada em blocos de um período."""
    n, N = int(SR * dur), int(SR / freq)
    rng = np.random.default_rng(seed)
    buf = rng.uniform(-1, 1, N)
    buf = bright * buf + (1 - bright) * np.convolve(buf, np.ones(3) / 3, "same")
    out = np.empty(n)
    pos = 0
    while pos < n:
        k = min(N, n - pos)
        out[pos:pos + k] = buf[:k]
        buf = 0.996 * 0.5 * (buf + np.roll(buf, -1))
        pos += k
    return out * vol


def build_audio(path):
    buf = np.zeros(int(SR * (DUR + 1)))
    chords = {"C": (67, 60, 64, 72), "Am": (69, 60, 64, 69), "F": (69, 60, 65, 69), "G": (67, 62, 67, 71)}
    prog = ["C", "Am", "F", "G", "C", "Am"]
    for b in range(int(DUR * 4)):                                   # colcheias a 120 bpm
        t0 = b * 0.25
        notes = chords[prog[int(t0) % len(prog)]]
        down = b % 2 == 0
        order = notes if down else notes[::-1]
        for i, m in enumerate(order):
            add(buf, pluck(midi(m), 0.9, 0.16 if down else 0.09, 0.6, seed=b * 7 + i), t0 + i * 0.012)
    rng = np.random.default_rng(3)
    for tb in (0.7, 1.1, 2.6, 3.0, 4.4, 5.3):                       # passarinhos
        for k in range(rng.integers(2, 4)):
            d = 0.07
            tt = np.arange(int(SR * d)) / SR
            f = 3200 + 1600 * tt / d + 300 * np.sin(2 * np.pi * 40 * tt)
            ph = 2 * np.pi * np.cumsum(f) / SR
            add(buf, np.sin(ph) * np.sin(np.pi * tt / d) * 0.05, tb + k * 0.11)
    wind = np.convolve(rng.standard_normal(len(buf)), np.ones(400) / 400, "same")   # vento (ruído filtrado)
    buf += wind / np.max(np.abs(wind)) * 0.03
    n = int(SR * DUR)
    buf = buf[:n]
    fade = int(SR * 0.4)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    write_wav(path, buf)


def legenda_png(path, texto):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 64)
    linhas, atual = [], ""
    for palavra in texto.split():                                   # quebra por largura
        teste = f"{atual} {palavra}".strip()
        if d.textlength(teste, font=f) > 900 and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    linhas.append(atual)
    y = 1380
    for ln in linhas:
        d.text((W // 2, y), ln, font=f, fill="white", anchor="mm", stroke_width=6, stroke_fill=(30, 25, 20))
        y += 84
    img.save(path)


def main():
    frames = sorted((OUT / "blender" / "cena1").glob("f_*.png"))
    assert len(frames) >= int(FPS * DUR), f"render incompleto ({len(frames)} quadros)"
    audio, sub = OUT / "cena1_audio.wav", OUT / "cena1_legenda.png"
    build_audio(audio)
    legenda_png(sub, LEGENDA)
    mp4 = OUT / "cena1_blender.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-framerate", str(FPS), "-i", str(OUT / "blender" / "cena1" / "f_%04d.png"),
           "-loop", "1", "-framerate", str(FPS), "-i", str(sub), "-i", str(audio),
           "-filter_complex", "[1]format=rgba,fade=in:st=0.5:d=0.4:alpha=1[s];[0][s]overlay=0:0:shortest=1[v]",
           "-map", "[v]", "-map", "2:a", "-t", str(DUR),
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(mp4)]
    subprocess.run(cmd, check=True)
    print("ok ->", mp4)


if __name__ == "__main__":
    main()
