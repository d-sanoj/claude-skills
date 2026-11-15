# Conventions evidence — the pain point and the related work

## The pain point

The complaint is consistent across teams that adopt a coding agent:
the first week is impressive; by the third week, review comments
start repeating. One write-up (dev.to, October 22, 2026) puts the
pattern plainly: "we don't use that logger here", "this should
follow the orders service", "don't call the payments API directly".
"The agent writes good code. It just keeps writing it the way most
projects do, not the way yours does."

Why it happens, in the same piece: a model learns its defaults from
an enormous amount of public code, and a team's conventions are, by
definition, the places where it decided to do something different
from the default. Those decisions live in "review comments from two
years ago, a wiki page nobody opens, the head of the engineer who
set up the service". "When a coding agent starts a session, it sees
the files it reads and the instructions it loads. If a convention
isn't in either, the agent falls back to the average choice. Which
is exactly the choice your team decided against."

The same piece's fix #4 is the one this skill is built on:
"Anything a linter, formatter, type checker, or architecture test
can catch should be caught there, not in review." And fix #5 is the
drift ledger: "If you correct the agent on the same thing twice,
the problem is not the prompt. It is a missing rule. Add the line
to `CLAUDE.md` in the same PR as the fix." This skill keeps the
ledger but stores the rule as a check, not a line of prose.

- "Why your AI coding agent ignores your team's conventions (and
  how to fix it)", dev.to, published 2026-10-22, updated
  2026-10-27.
  https://dev.to/aiworkspacebuilder/why-your-ai-coding-agent-ignores-your-teams-conventions-and-how-to-fix-it-2p8n

## The enforcement hierarchy

A second write-up (swarmz.net, published 2026-08-15, updated
2026-09-08) ranks enforcement mechanisms by how hard they are to
ignore: (1) a formatter that rewrites the file, (2) a linter with
a non-zero exit code in the agent's build command, (3) a type
system or a test that asserts structure, (4) committed example
code the agent reads before editing, (5) a rule written in prose
in your instructions file — which the agent ignores frequently.
"Most teams start at tier 5 and stay there, then conclude the
agent is bad at following instructions. The agent is fine. Tier 5
is a weak channel." And: "Prose in a config file is a suggestion.
A failing exit code is a fact."

This skill's severity tiers map directly onto that ladder: hard
rules are tier 2, advisory rules are the ones a regex cannot
enforce honestly, and formatter rules are tier 1 and left to the
formatter. It also adopts the piece's warning that drift is a bug
report about the configuration, not about the agent — and its
observation that the cost of drift is reviewability: "four naming
conventions, three error-handling patterns, two ways of importing
the same module, and no way to tell which was deliberate."

- "Make an AI Coding Agent Follow Your Code Style", swarmz.net.
  https://swarmz.net/blog/make-an-ai-coding-agent-follow-your-code-style

## Related work — what already exists, and what is different

- **Claude Code `/init`** generates a starter `CLAUDE.md` from a
  codebase. That is the prose route: useful as a starting point,
  and the weakest enforcement tier. This skill starts where `/init`
  stops — it turns the detected patterns into checks.
- **AI Dev OS** (dev.to, 2026) is an open-source framework that
  converts implicit developer knowledge into explicit rules for AI
  coding assistants, in four layers by lifespan. Same diagnosis —
  "Yesterday: `getUsers()`. Today: `fetchUserList()`. Tomorrow:
  `loadAllUsers()`" — but a framework of hand-written rules per
  stack, not a measurement of one repo's actual code.
  https://dev.to/yun_bow/i-built-an-oss-to-stop-ai-from-writing-inconsistent-code-every-time-claude-code-cursor-kiro-1oe1
- **ywc-onboard-repo** (mcpmarket) is a skill that extracts
  "true ground-truth conventions" from a repo — package manifests,
  file-naming and error-handling patterns, test layouts — and
  generates an onboarding guide and a `CLAUDE.md`. Closest
  relative: same measurement instinct, but the output is a prose
  document the agent reads, not a checker the agent runs.
  https://mcpmarket.com/tools/skills/repository-onboarding-documentation
- **Aider's repo map** (aider.chat/docs/repomap.html) is the prior
  art for giving an agent a compact view of a repo: it parses the
  code with tree-sitter, extracts the important classes and
  functions with their signatures, ranks them with a graph
  algorithm, and sends the top-ranked symbols inside a ~1,024
  token budget. This skill is not a repo map — it does not map
  symbols or rank files. It answers a different question: not
  *where* things are, but *how* things are written here, and
  whether the new code matches.
- **Repo-map skills and tools** (repomap-cli on PyPI, PinkyAI's
  repo-map skill, context-tools, context-crafter-mcp) all build
  the same map in different packaging. None of them extracts
  conventions or checks a diff against them.

## What this skill adds

A dominance threshold (80%), per-directory scoping, severity
tiers, and an outlier ledger — the four things that make the
difference between "here are your conventions" and "here is a
check that fails when the new code breaks one". The measurement
is the argument: the sine-portfolio run found that error handling,
the convention most style guides lead with, is mixed in every
directory and earns no rule, while the enforceable conventions
are the boring mechanical ones — naming, `const`, no logging in
shipped code, commit prefixes.
