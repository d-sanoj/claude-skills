#!/usr/bin/env python3
"""Check that this machine can run motion-reel, and say how to fix what is missing.

    python scripts/check.py

Read-only: it runs each tool's version command and installs nothing. Exit code 0
when everything is ready, 1 when something is missing.
"""
import os
import platform
import re
import shutil
import subprocess
import sys

OS = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")

# How to install each tool, per OS. Shown only for what is missing.
HOW = {
    "python": {"mac": "brew install python", "windows": "winget install --id Python.Python.3.12 -e", "linux": "sudo apt install python3"},
    "node": {"mac": "brew install node", "windows": "winget install --id OpenJS.NodeJS.LTS -e", "linux": "see https://nodejs.org/en/download (Node 22 or later)"},
    "chrome": {"mac": "brew install --cask google-chrome", "windows": "winget install --id Google.Chrome -e", "linux": "install google-chrome or chromium, or set CHROME_PATH"},
    "ffmpeg": {"mac": "brew install ffmpeg", "windows": "winget install --id Gyan.FFmpeg -e  (then open a new shell)", "linux": "sudo apt install ffmpeg"},
    "espeak-ng": {"linux": "sudo apt install espeak-ng"},
}

CHROME_PATHS = [
    os.environ.get("CHROME_PATH"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def version(cmd):
    """The first version number a command prints, or None when it is not installed."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out.stdout + out.stderr)
    return m.group(0) if m else "found"


def check_python():
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {platform.python_version()}" + ("" if ok else " (need 3.10 or later)")


def check_node():
    v = version(["node", "--version"])
    if not v:
        return False, "Node not found"
    ok = int(v.split(".")[0]) >= 22
    return ok, f"Node {v}" + ("" if ok else " (need 22 or later)")


def check_chrome():
    path = next((p for p in CHROME_PATHS if p and os.path.exists(p)), None)
    return bool(path), f"Chrome at {path}" if path else "Chrome not found (set CHROME_PATH to its executable)"


def check_tool(name, cmd):
    v = version(cmd)
    return bool(v), f"{name} {v}" if v else f"{name} not found on PATH"


def check_voice():
    if OS == "linux":
        return check_tool("espeak-ng", ["espeak-ng", "--version"])
    return True, "system voice: " + ("say" if OS == "mac" else "Windows System.Speech")


CHECKS = {
    "python": check_python,
    "node": check_node,
    "chrome": check_chrome,
    "ffmpeg": lambda: check_tool("ffmpeg", ["ffmpeg", "-version"]),
    "ffprobe": lambda: check_tool("ffprobe", ["ffprobe", "-version"]),
    "voice": check_voice,
}

INSTALL_FOR = {"ffprobe": "ffmpeg", "voice": "espeak-ng"}


def main():
    results, missing = {}, set()
    print("\nmotion-reel")
    ready = True
    for item, check in CHECKS.items():
        if item not in results:
            results[item] = check()
        ok, text = results[item]
        print(f"  {'ok     ' if ok else 'MISSING'}  {text}")
        if not ok:
            ready = False
            missing.add(INSTALL_FOR.get(item, item))
    print(f"  -> {'ready' if ready else 'not ready'}")
    if missing:
        print(f"\nInstall ({OS}):")
        for tool in sorted(missing):
            print(f"  {tool}: {HOW.get(tool, {}).get(OS, 'see the skill README')}")
        print("Then open a new shell and run this check again.")
        sys.exit(1)
    print("\nAll set. Next: copy example/ to a film folder and read the SKILL.md.")


if __name__ == "__main__":
    main()
