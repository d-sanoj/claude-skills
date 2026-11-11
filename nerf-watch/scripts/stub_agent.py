#!/usr/bin/env python3
"""Test stub for nerf-watch: pretends to be `claude` so the runner,
scoring, and comparer can be tested end to end without a live model.

The stub reads NERF_WATCH_TASK_ID, copies that task's canned solution
from tests/stub-solutions/<task-id>/ into the working directory, and
prints the canned answer (tests/stub-solutions/<id>/canned-output.txt)
as JSON in the shape `claude -p --output-format json` returns.

Set NERF_WATCH_STUB_WRONG=1 to use tests/wrong-solutions/ instead —
one deliberately wrong answer (read-then-answer names the old figure),
which proves the checks can actually fail.

Usage (from the skill folder):
    NERF_WATCH_AGENT_CMD="python scripts/stub_agent.py" \\
        python scripts/run_suite.py --model stub --effort medium
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

task_id = os.environ.get("NERF_WATCH_TASK_ID", "")
if "--version" in sys.argv:
    print("stub-agent 0.1 (test double for claude)")
    sys.exit(0)
wrong = os.environ.get("NERF_WATCH_STUB_WRONG") == "1"
base = os.path.join(SKILL, "tests",
                    "wrong-solutions" if wrong else "stub-solutions",
                    task_id)
if wrong and not os.path.isdir(base):
    # A wrong variant exists only for the tasks it is meant to break;
    # the rest answer correctly.
    base = os.path.join(SKILL, "tests", "stub-solutions", task_id)
if not task_id or not os.path.isdir(base):
    print(json.dumps({"result": "", "total_cost_usd": 0.0,
                      "error": f"stub has no solution for task {task_id!r}"}))
    sys.exit(0)

result = ""
for name in sorted(os.listdir(base)):
    src = os.path.join(base, name)
    if name == "canned-output.txt":
        with open(src) as f:
            result = f.read().strip()
    elif os.path.isdir(src):
        shutil.copytree(src, name, dirs_exist_ok=True)
    else:
        shutil.copy2(src, name)

print(json.dumps({"result": result, "total_cost_usd": 0.0,
                  "session_id": f"stub-{task_id}"}))
