---
name: motion-reel
description: Make a short animated explainer (about 5–60 seconds) as a web page animated with Motion (the motion.dev library, MIT), then render it to MP4 with headless Chrome and ffmpeg. One skill, one template, free system voice only. Use when the user asks for a "Claude Motion"-style video, an animated explainer, a product teaser or an animated chart, and wants it on any Claude Code plan — including Pro, where Claude Motion itself is not available.
---

# A film as a web page

This skill is the Motion idea without the plan gate: a prompt becomes a film you
can preview, edit and download as MP4. The film is code. Every frame comes from
one paused Motion timeline, so a re-render gives the same film, frame for frame.
No footage. Narration is optional, comes last, and uses the free system voice —
there is no paid voice in this skill.

```bash
R="${CLAUDE_SKILL_DIR}/scripts/render.mjs"
```

Tools: Node 22 or later, Google Chrome, `ffmpeg`, Python 3.10 or later. No npm packages.
Motion 12.23.24 is saved in `runtime/motion.js` with its MIT licence. The score
is synthesised by `scripts/synth.py` (no samples, no downloads). The typeface is
Josefin Sans (SIL Open Font License), saved in `runtime/JosefinSans-VF.ttf` so a
film renders the same on any machine. Before the first film, run
`python ${CLAUDE_SKILL_DIR}/scripts/check.py`.

## 1. Read the product first
- Read the product's own source of truth: its site, its docs or the plan.
  Write down the one idea the film shows, in one sentence.
- Every claim on screen must be true today. Use real prices and names, or say they are samples.

## 2. Ask two questions only
Ask with AskUserQuestion, both in one call. Skip a question that the request already answers.
- **Visual style:** 3 film ideas named after the picture, each with one line on the scenes.
- **Colours:** the product's own palette first, then 2 others, with hex values.

Default: 16:9, about 10 seconds, 3 scenes, in the built-in sine style — dark ink,
cream text, one yellow wave, Josefin Sans. That is the look of `example/`.

## 3. Make the folder
Copy `example/` to `<scratchpad>/reel-<slug>/`. It holds two files:
- `film.html`: one `<section data-scene="<Name>">` per scene inside `#stage`, and a module that
  calls `film({ scenes })` from `/runtime/player.js`.
- `film.json`: `shape` (`16:9`, `1:1`, `9:16`), `text`, `colors`, `score` and `narration`.

A scene is `{ name, duration, play }`. `play()` returns Motion sequence segments
`[target, keyframes, options]`, and `options.at` is seconds from the scene start:

```js
{ name: "Plans", duration: 3.5, play: () => [
  ["#c1", { opacity: [0, 1], y: [80, 0] }, { type: "spring", bounce: 0.25, visualDuration: 0.6, at: 0.2 }],
] }
```

Rules for the page:
- Design for the full frame: 1920×1080 for 16:9. Use px sizes; the preview scales the frame.
- Give every keyframe a `[from, to]` pair. The runtime shows the `from` value until the
  segment starts, so nothing flashes before it animates in.
- Put words that may change in `film.json` `text`, and mark the element `data-text="<key>"`.
- Put colours in `film.json` `colors` as custom properties (`--bg`, `--accent`), and use
  `var(--bg)` in the CSS. The editor shows a colour picker for each one.
- Only one scene shows at a time. A scene that continues the last picture re-creates it.
- Keep the film's own words and pictures in the film. Do not put a real app's screens in
  it: captures can leak customer data, and that is a different skill.

## 4. Score
Same format as the film's `score` in `example/film.json` (`note`, `pad`, `hit`;
`at` is seconds from the scene start; `"len": "scene"` lasts to the scene end).
Put a `hit` or a `note` on each thing that lands. A film with no `score.events`
renders silent. The synth is `scripts/synth.py`: notes are sine, triangle, square
or saw waves, hits are short shaped sounds (`thud`, `pop`, `tick`, `whoosh`).

## 5. Narration: script first, free voice only
- Write the words first, in `film.json`: `"narration": {"Wake": "Meet Acme Board.", ...}`. One short
  spoken line per scene, in plain short sentences. A scene with no line has no voice.
- Make the clips: `python ${CLAUDE_SKILL_DIR}/scripts/voice.py <dir>`. It uses the
  system voice (`say` on macOS, Windows speech, `espeak-ng` on Linux) and writes
  `voice.json`. Each scene stretches to fit its narration.
- Clips are kept under names made from their words. A re-run re-records only changed lines.
  Playing or re-rendering the film costs nothing, and there is no key to set.
- The score plays at 35% under the voice. The narration code is `scripts/narrate.py`.
- The system voice sounds like a system voice. If the reader wants a human voice,
  say so plainly and let them record it; do not pretend the free voice is a performance.

## 6. Preview and edit
```bash
node $R <dir> edit      # prints http://127.0.0.1:<port>/film.html?edit ; Ctrl+C to stop
```
- The editor shows Play, a time bar and one button per scene. A scene button shows the end of
  that scene, where everything is in place.
- The side panel changes the words and the colours live. **Save to film.json** writes them back.
  Render again to put them in the MP4.
- `node $R <dir> preview` serves the same page without the panel and without saving.
- The server listens on 127.0.0.1 only, and saves only `film.json` in that folder.

## 7. Draft, then final
- Draft (960×540, 15 fps, about 20 s for a 10 s film): `node $R <dir> draft` → `draft.mp4`.
  It prints each scene's start and end time.
- **Look before you report.** Take frames from the middle of each scene and view them:
  `ffmpeg -loglevel error -y -ss <sec> -i <dir>/draft.mp4 -frames:v 1 <dir>/f<sec>.png`.
  One full-size frame without a video: `node $R <dir> still <sec> <out.png>`.
- Check the sound: `ffmpeg -i <dir>/draft.mp4 -af volumedetect -f null -` must show
  `Audio: aac` and a mean volume above about −40 dB.
- Final, after the user says the draft is right: `node $R <dir> final` → `final.mp4`
  (1920×1080, 30 fps, about 1 minute for a 10 s film) and `poster.png` (1 s before the end).

## 8. Deliver
- Give the path to `final.mp4` and `poster.png`, the scene plan and the render command.
- List any on-screen claim you are not sure is true.
- To keep it, copy `film.html` and `film.json` next to the post or page that uses the film.

## Safety
- **Nothing private on screen or in a file.** No keys, tokens, passwords, customer names,
  emails or security findings in a screenshot, a film or a commit. Read keys from the
  environment only; never print them or write them to a file. This matters more than it
  looks: Claude Code has repeatedly put the signed-in user's email into outgoing request
  headers, so check what actually left the machine before you share a film or a log.
- **Use made-up names in shared examples:** the product *Acme Board* at `board.example.com`.
- **Never embed a narrated video as muted autoplay.** Browsers autoplay only muted video,
  so the voice is never heard. Embed it with `controls` and a poster.

## Licences
- Motion and the Motion AI Kit are MIT. Keep `runtime/LICENSE-motion.md` with `motion.js`.
- This skill is adapted from motion-skills by verbodh-pte-ltd (MIT); see the README for
  what changed. Keep `LICENSE` with the skill.
- Josefin Sans is under the SIL Open Font License.
- Do not copy Motion+ source code (paid) into a film or into this skill.
- Claude Motion is Anthropic's product. Do not use its name or branding in films you publish.

## Known traps
- **A scene shows during the wrong scene:** a film rule such as `display: grid` on a section
  beat the `hidden` attribute. `runtime/film.css` forces `display: none` on hidden sections;
  keep it loaded.
- **Chrome not found:** set `CHROME_PATH` to the Chrome executable.
- **`ffmpeg` not found on Windows after `winget install`:** open a new shell.
- **No voice on Linux:** install `espeak-ng` (`sudo apt install espeak-ng`).

## Check the script
`python ${CLAUDE_SKILL_DIR}/scripts/test_render.py` renders the example and checks
the length, the sound, that the picture moves, and that one time gives the same frame twice.
