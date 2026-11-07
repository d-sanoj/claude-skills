# motion-reel

A short animated explainer as code, on any Claude Code plan — including Pro,
where Claude Motion itself is not available.

Ask for a film in plain words — *"a 15-second animated explainer of our pricing
page: three plans, the middle one highlighted"* — and the skill builds a web page
animated with [Motion](https://motion.dev), shows you a draft, lets you edit the
words and colours in the browser, then renders it to MP4. Every film is code, so
a re-render gives the same film, frame for frame. Drafts are free: narration uses
your system voice, and there is no paid voice in this skill at all.

## Install

```bash
cp -r motion-reel ~/.claude/skills/        # every project
# or: cp -r motion-reel <project>/.claude/skills/   # one project
python ~/.claude/skills/motion-reel/scripts/check.py
```

It says, per tool, **ok** or **MISSING**, and prints the install command for each
missing tool on your OS. It installs nothing.

| Needs | Version |
|---|---|
| Python | 3.10+ |
| Node | 22+ |
| Chrome | any recent version |
| ffmpeg (+ ffprobe) | any recent version |
| espeak-ng | Linux only, for the free voice |

## Use it

Ask in plain words. The skill asks for a style and colours, renders a draft,
shows you frames, and renders the final only after you say it is right. The
example film is included and renders out of the box:

```bash
cd ~/.claude/skills/motion-reel
node scripts/render.mjs example draft     # draft.mp4, 960x540
node scripts/render.mjs example final     # final.mp4, 1920x1080, + poster.png
```

The film's words live in `example/film.json` (`text`, `colors`, `score`,
`narration`); its scenes live in `example/film.html`. Copy `example/` to a new
folder to start your own film.

Tested: the example film renders as a draft and a final on the author's machine
(see `scripts/test_render.py`). The free-voice path was not rendered end to end
there — `espeak-ng` was not installable on that Linux machine — so narration is
code-verified rather than render-tested on that machine.

## What it makes

A 5–60 second animated explainer: titles, cards, charts and shapes that move,
with a synthesised score and an optional narrated voice. What it does not make:
photorealistic footage, or AI-generated people — there is no video generation
model in it, which is the same limit Claude Motion has. If you need footage,
this is the wrong tool.

## What changed from motion-skills

Adapted from [motion-skills](https://github.com/verbodh-pte-ltd/motion-skills)
by verbodh-pte-ltd, MIT licence, with attribution kept below. The changes:

- **One skill, not four.** `motion-video` (Manim), `training-guide` and
  `training-video` are gone. This is only the web-film skill, renamed
  `motion-reel`, because a 15-second explainer is the job most people ask for.
- **No paid voice.** The ElevenLabs path is removed. Narration is the free
  system voice only, so a film costs nothing and there is no API key to set —
  or to leak.
- **No real-app screenshots.** The walkthrough template is gone with it. Films
  are drawn cards and shapes, so nothing private can end up on screen.
- **A built-in look.** The example ships in the sine style — dark ink, cream
  text, one yellow wave, Josefin Sans (OFL, bundled in `runtime/`) — instead of
  asking you to pick a palette from scratch every time.
- **Self-contained score.** The score synth is vendored as `scripts/synth.py`,
  so this skill no longer depends on the motion-video folder sitting next to it.
- **Simpler install.** Copy the folder; no plugin marketplace, no installer script.

Kept verbatim: `scripts/render.mjs`, `runtime/motion.js` (Motion 12.23.24, MIT),
`runtime/player.js`, `runtime/film.css`, and the render test — with one change:
`render.mjs` passes `--no-sandbox` when run as root, since Chrome refuses to
start as root otherwise (containers, CI). The score format,
the film format and the render pipeline are unchanged, so a film written for the
original `motion-web-video` skill still renders here.

## Attribution and licence

- Original work: motion-skills, copyright (c) 2026 The motion-skills authors,
  MIT — see [LICENSE](LICENSE). This adaptation keeps that licence and adds
  nothing to it.
- Motion (the animation library in `runtime/motion.js`) is MIT — see
  [runtime/LICENSE-motion.md](runtime/LICENSE-motion.md).
- Josefin Sans (in `runtime/JosefinSans-VF.ttf`) is under the SIL Open Font License — see [runtime/OFL.txt](runtime/OFL.txt).
- Claude Motion is Anthropic's product; this skill is not affiliated with
  Anthropic, and films made with it must not use Claude Motion's name or branding.

## What it runs, sends and fetches

Everything runs on your machine. There is no telemetry and no account. The
renderer serves the film on `127.0.0.1` only. Nothing is sent anywhere: there is
no paid voice to call, and the film loads no web fonts — Josefin Sans is bundled.
