# Claude Skills

A collection of Claude skills I build and improve. Each folder is one skill, with its own README and everything needed to install it.

## Skills

- **Claude Motion for Pro** — [motion-reel](motion-reel): animated explainers on any Claude Code plan, even though Claude Motion itself is Team/Enterprise only. First skill in this repo.
- **Claude Code secret-leak guard** — [claude-guard](claude-guard): audit a repo for secrets Claude Code's "Don't Ask Again" saved into settings files, and fix them. Second skill in this repo.
- **Model regression watcher** — [nerf-watch](nerf-watch): a frozen 8-task suite that scores your coding agent week to week, so when a model "feels nerfed" you have a number instead of a vibe. Third skill in this repo.
- **Test prover** — [prove-the-tests](prove-the-tests): make your coding agent prove its tests can fail — expected values from the requirement, red first, then a mutation check that deliberately breaks the code. Fourth skill in this repo.

## Install

Each skill folder has its own README with install steps. In general: copy the skill folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project).

## License

Each skill folder carries its own license and attribution. Skills adapted from someone else's work say so in their README.
