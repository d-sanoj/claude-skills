#!/usr/bin/env python3
"""Synthesise the score for a motion-reel film: notes, pads and hits, no samples.

Adapted from motion-video/scripts/motion.py in motion-skills
(https://github.com/verbodh-pte-ltd/motion-skills, MIT). Only the synth is kept:
the Manim film builder from that file is not part of this skill.

Score events (time "at" is seconds from the start of the named scene):
  {"type": "note", "scene": "Reach", "at": 0.5, "pitch": "E4", "len": 0.4, "wave": "triangle", "gain": 0.3}
  {"type": "pad",  "scene": "Wake",  "at": 0, "pitches": ["C3", "G3", "E4"], "len": 4, "gain": 0.12}
  {"type": "hit",  "scene": "Fence", "at": 1.2, "sound": "thud" | "pop" | "tick" | "whoosh", "gain": 0.5}
A "len" of "scene" lasts to the end of that scene.
"""
import array
import math
import random
import sys
import wave
from pathlib import Path

RATE = 44100
NOTE = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def freq(pitch):
    """'A4' -> 440.0; accepts sharps and flats ('F#3', 'Bb2')."""
    name, octave = pitch[:-1], int(pitch[-1])
    semis = NOTE[name[0].upper()] + name[1:].count("#") - name[1:].count("b")
    return 440.0 * 2 ** ((semis + 12 * (octave - 4)) / 12)


def osc(wave_name, phase):
    if wave_name == "sine":
        return math.sin(phase)
    x = (phase / (2 * math.pi)) % 1.0
    if wave_name == "square":
        return 1.0 if x < 0.5 else -1.0
    if wave_name == "saw":
        return 2 * x - 1
    return 4 * abs(x - 0.5) - 1  # triangle


def add_tone(buf, start, length, hz, wave_name, gain, attack=0.01, release=0.15):
    n0, n = int(start * RATE), int(length * RATE)
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    step = 2 * math.pi * hz / RATE
    for i in range(min(n, len(buf) - n0)):
        env = min(1.0, i / a, (n - i) / r)
        buf[n0 + i] += gain * env * osc(wave_name, step * i)


def add_hit(buf, start, sound, gain):
    n0 = int(start * RATE)
    rnd = random.Random(7)  # fixed seed: the same film always gets the same noise
    shapes = {  # seconds, pitch start -> end (Hz, 0 = noise), decay speed
        "thud": (0.35, 120, 45, 12), "pop": (0.12, 900, 400, 30),
        "tick": (0.04, 2500, 2500, 80), "whoosh": (0.6, 0, 0, 4),
    }
    length, f0, f1, decay = shapes[sound]
    n, phase = int(length * RATE), 0.0
    for i in range(min(n, len(buf) - n0)):
        t = i / RATE
        if sound == "whoosh":  # noise that swells, then fades
            env = math.sin(math.pi * i / n) ** 2
            s = rnd.uniform(-1, 1) * env
        else:
            phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / RATE
            s = math.sin(phase) * math.exp(-decay * t)
        buf[n0 + i] += gain * s


def synth(score, starts, ends, total):
    buf = array.array("f", bytes(4 * int(total * RATE)))
    for e in score.get("events", []):
        t0 = starts[e["scene"]] + e.get("at", 0)
        length = ends[e["scene"]] - t0 if e.get("len") == "scene" else e.get("len", 0.4)
        if e["type"] == "note":
            add_tone(buf, t0, length, freq(e["pitch"]), e.get("wave", "triangle"), e.get("gain", 0.3))
        elif e["type"] == "pad":
            for p in e["pitches"]:
                add_tone(buf, t0, length, freq(p), e.get("wave", "sine"), e.get("gain", 0.1), attack=0.6, release=1.0)
        elif e["type"] == "hit":
            add_hit(buf, t0, e["sound"], e.get("gain", 0.5))
        else:
            sys.exit(f"unknown score event type: {e['type']}")
    peak = max((abs(s) for s in buf), default=0) or 1.0
    scale = score.get("master", 0.8) / peak  # normalise, so stacked notes never clip
    return array.array("h", (int(s * scale * 32767) for s in buf))


def write_wav(path, pcm):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
