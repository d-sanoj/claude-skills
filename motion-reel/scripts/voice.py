#!/usr/bin/env python3
"""Narrate a film: one clip per scene from film.json "narration", written to voice.json.

usage: voice.py <film_dir>

Free system voice only, for drafts and finals alike. This skill has no paid voice:
there is no API key to set and nothing to bill. Clips are kept and reused, so
unchanged words are never re-recorded. The narration code is narrate.py, next to this file.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrate import narrate, report  # noqa: E402


def main():
    args = sys.argv[1:]
    root = Path(args[0]).resolve()
    film = json.loads((root / "film.json").read_text(encoding="utf-8"))
    lines = [(name, words.strip()) for name, words in film.get("narration", {}).items() if words.strip()]
    if not lines:
        sys.exit('film.json has no "narration" to speak')
    clips, new = narrate(root, lines)
    report(new)
    (root / "voice.json").write_text(json.dumps(clips, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
