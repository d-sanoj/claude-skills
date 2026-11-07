#!/usr/bin/env python3
"""Turn one spoken line per scene into audio clips, with the free system voice only.

This is the narration half of voice.py. There is no paid voice path in this skill:
drafts and finals both use the system voice (macOS `say`, Windows System.Speech,
Linux `espeak-ng`), so a film costs nothing to narrate and no API key exists to leak.

Every clip is kept under a name made from its words. A clip whose words did not
change is reused, so a re-run never re-records the same sentence.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return round(float(out.stdout), 2)


def free_voice(words, out):
    """Speak `words` into `out` with the system voice. Free; for drafts and finals."""
    if sys.platform == "darwin":
        subprocess.run(["say", "-o", str(out), words], check=True)
        return
    if sys.platform == "win32":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(words)
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{out}'); $s.Speak([IO.File]::ReadAllText('{f.name}')); $s.Dispose()")
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
        finally:
            import os
            os.unlink(f.name)
        return
    try:
        subprocess.run(["espeak-ng", "-w", str(out), words], check=True)
    except FileNotFoundError:
        sys.exit("espeak-ng not found: install it with `sudo apt install espeak-ng`, then run voice.py again")


def spoken(words):
    """The words as a person says them. A test found the voice read '#' and dots aloud.

    Markdown and other symbols are dropped, an arrow is said as 'to', and an @mention keeps its
    name ('@claude' is 'at Claude'). Sentence dots stay: they are pauses, not words.
    """
    words = re.sub(r"@(\w+)", lambda m: f"at {m.group(1).capitalize()}", words)
    words = re.sub(r"\s*(→|->)\s*", " to ", words)
    words = re.sub(r"[#*_`>|~\[\]{}]", "", words)
    return re.sub(r"\s+", " ", words).strip()


def clip_path(audio, name, words):
    tag = hashlib.sha256(f"system|default|{words}".encode()).hexdigest()[:12]
    ext = "aiff" if sys.platform == "darwin" else "wav"
    return audio / f"{name}.system.{tag}.{ext}"


def narrate(root, lines):
    """Make one clip per (scene, words) pair in `lines`, reusing every clip already made.

    Returns ({scene: {"file", "seconds"}}, new_clips).
    """
    lines = [(name, spoken(words)) for name, words in lines]
    root = Path(root)
    audio = root / "audio"
    audio.mkdir(exist_ok=True)
    out, new = {}, 0
    for name, words in lines:
        clip = clip_path(audio, name, words)
        if not clip.exists():
            new += 1
            free_voice(words, clip)
        if clip.exists():
            out[name] = {"file": clip.relative_to(root).as_posix(), "seconds": duration(clip)}
    return out, new


def report(new):
    print(f"{new} new clip(s) with the free system voice")
