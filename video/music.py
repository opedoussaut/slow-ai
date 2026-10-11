#!/usr/bin/env python3
"""Original, procedurally generated soundtrack for the SlowAI v3 video.

Every sound is synthesised here from sine and noise sources: no samples and no
third-party music. The result can be released with the project (CC0).
It follows the scene timings in video/scene-v3.html.

    python video/music.py --output /tmp/slowai-music.wav
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48_000
DUR = 92.0
rng = np.random.default_rng(20261011)


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n: int, attack: float, release: float) -> np.ndarray:
    a, r = int(attack * SR), int(release * SR)
    e = np.ones(n)
    if a: e[:a] = np.linspace(0, 1, a) ** 2
    if r: e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return sosfilt(butter(2, cutoff, fs=SR, output="sos"), x)


def pad(notes, start, length, gain=0.06, bright=1600):
    """Warm detuned pad: three slightly detuned sines plus a soft octave per note."""
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in notes:
        f = hz(m)
        for d in (-0.08, 0.0, 0.07):
            fd = f * 2 ** (d / 12)
            out += np.sin(2 * np.pi * fd * t + rng.uniform(0, 6.28))
            out += 0.25 * np.sin(2 * np.pi * 2 * fd * t + rng.uniform(0, 6.28))
    out *= env(n, min(3.0, length / 3), min(3.5, length / 3)) * gain / len(notes)
    out *= 1 + 0.12 * np.sin(2 * np.pi * 0.11 * t)            # slow breathing
    return int(start * SR), lowpass(out, bright)


def pluck(m, start, gain=0.05, decay=0.9):
    n = int((decay + 0.3) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t))
    x *= np.exp(-t / (decay / 4)) * env(n, 0.004, 0.05) * gain
    return int(start * SR), lowpass(x, 3500)


def pulse(start, gain=0.10):
    """Soft low heartbeat: a sine thump with fast pitch drop."""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 55 * (1 + 1.5 * np.exp(-t * 30))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * gain
    return int(start * SR), x


def tick(start, gain=0.05):
    """Card landing in its lane: short filtered click with a bright sine tail."""
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t * 90) * 0.6 + np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 18)
    return int(start * SR), lowpass(x, 6000) * gain


def riser(start, length, gain=0.04):
    n = int(length * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    for i, c in enumerate(np.linspace(300, 3000, 8)):            # stepped filter sweep
        a, b = i * n // 8, (i + 1) * n // 8
        out[a:b] = lowpass(noise, c)[a:b]
    return int(start * SR), out * np.linspace(0, 1, n) ** 2 * env(n, 0.05, 0.4) * gain


def add(track, item):
    i, x = item
    j = min(len(track), i + len(x))
    track[i:j] += x[: j - i]


def reverb(x):
    """Small Schroeder reverb: four combs and two all-passes."""
    out = np.zeros_like(x)
    for d, g in ((1557, .80), (1617, .79), (1491, .81), (1422, .78)):
        d = int(d * SR / 44100)
        y = np.copy(x)
        for k in range(d, len(y), d):                           # block-wise feedback comb
            y[k:k + d] += g * y[k - d:k][: len(y[k:k + d])]
        out += y
    out /= 4
    for d, g in ((225, .7), (556, .7)):
        d = int(d * SR / 44100)
        y = np.copy(out)
        y[d:] += -g * out[:-d]
        out = y
    return out


def build() -> np.ndarray:
    n = int(DUR * SR)
    dry = np.zeros(n)
    D, F, A, C, E, G, Bb = 50, 53, 57, 60, 64, 55, 58
    # Harmony by scene (start, length, chord)
    for s, l, chord, g in [
        (0, 15, [D - 12, D, A, C + 12, E + 12], .07),            # title, campus: Dm9, calm
        (14, 10, [Bb - 12, Bb - 12 + 12, F + 12, A + 12], .075),   # stress: Bbmaj7
        (23, 10, [G - 12, G, Bb, D + 12, F + 12], .07),           # curate: Gm9
        (32, 10, [D - 12, D, F, A, C + 12], .06),                 # router: Dm7
        (41, 10, [Bb - 12, F, A, D + 12], .06),                   # Bbmaj7
        (50, 10, [F - 12, F, A, C + 12, E + 12], .06),            # Fmaj7
        (59, 12, [C - 12, G, Bb, E + 12], .06),                   # C7sus feel
        (70, 8, [F - 12, F, A, C + 12, G + 12], .065),            # record: Fmaj9, warm
        (77, 8.5, [Bb - 12, Bb, D + 12, F + 12, A + 12], .07),    # pyramid: Bbmaj7 swell
        (84.5, 7.5, [D - 12, D, A, E + 12, F + 12 + 1], .075),    # end: D major add9 resolve
    ]:
        add(dry, pad(chord, s, l, gain=g, bright=1800 if s < 70 else 2400))
    # Stress: heartbeat at 72 bpm, rising noise into the curation scene
    for k in range(int(9 / (60 / 72))):
        add(dry, pulse(14.3 + k * 60 / 72, gain=0.09 + 0.004 * k))
    add(dry, riser(19.5, 3.6))
    # Router: steady pentatonic arpeggio at 100 bpm (eighth notes), D minor pentatonic
    scale = [D + 12, F + 12, G + 12, A + 12, C + 24, D + 24]
    step = 60 / 100 / 2
    k = 0
    t = 32.0
    while t < 69.5:
        m = scale[[0, 2, 4, 3, 1, 3, 5, 2][k % 8]]
        add(dry, pluck(m, t, gain=0.028 + (0.008 if k % 4 == 0 else 0)))
        k += 1
        t += step
    # Card landings (match the question cards in scene-v3.html)
    for q0 in (32.5, 40.0, 47.0, 54.5, 62.5):
        add(dry, tick(q0 + 2.35))
    add(dry, tick(47.0 + 3.6, gain=0.04))                         # escalation move
    # Pyramid: arpeggio returns, rising
    t, k = 77.3, 0
    while t < 84.8:
        add(dry, pluck(scale[k % 6] + (12 if k > 14 else 0), t, gain=0.03))
        k += 1
        t += 60 / 112 / 2
    add(dry, riser(82.6, 2.2, gain=0.03))
    wet = reverb(dry)
    mix = 0.72 * dry + 0.55 * wet
    mix = lowpass(mix, 9000)
    mix *= env(n, 0.8, 2.5)
    mix /= np.max(np.abs(mix)) / 0.5                             # peak at -6 dBFS: background music
    return mix


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--output", type=Path, default=Path("slowai-music.wav"))
    a = p.parse_args()
    x = build()
    stereo = np.stack([x, np.roll(x, int(0.011 * SR))], axis=1)  # slight width
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(a.output), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(f"wrote {a.output} ({DUR:.0f} s)")


if __name__ == "__main__":
    main()
