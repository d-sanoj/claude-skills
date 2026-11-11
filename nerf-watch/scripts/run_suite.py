#!/usr/bin/env python3
"""Run the nerf-watch frozen suite and score it.

Each task runs in a fresh temp directory: fixtures are copied in, the
agent is invoked once with the task prompt, then the task's checks run
against whatever the agent left behind. Results are appended as one JSON
object per run to the output file (default: results/<date>-<model>-<effort>.json).

The agent is Claude Code in headless mode:

    claude --bare -p "<prompt>" --model <model> --effort <level>
        --output-format json --max-turns 10 --max-budget-usd 2
        --allowedTools "Read Write Edit Bash Glob Grep"
        --permission-mode acceptEdits

--bare skips hooks, skills, MCP servers and CLAUDE.md so the run is the
same on every machine. The model and effort are pinned on the command
line, because the whole point is comparability: a run at a different
effort is a different measurement, not a repeat.

Set NERF_WATCH_AGENT_CMD to replace `claude` — e.g. a test stub — and
NERF_WATCH_TASK_ID is passed through to that command so a stub knows
which task it is faking. The real `claude` ignores both.

Usage:
    python run_suite.py [--model claude-opus-5-5] [--effort medium]
                        [--out results/] [--task median] [--dry-run]
"""
import argparse
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TASKS = os.path.join(SKILL, "tasks", "tasks.json")
FIXTURES = os.path.join(SKILL, "tasks", "fixtures")

AGENT_CMD = os.environ.get("NERF_WATCH_AGENT_CMD", "claude")
MAX_TURNS = "10"
MAX_BUDGET_USD = "2"


def load_tasks():
    with open(TASKS) as f:
        return json.load(f)["tasks"]


def run_check(check, workdir, output):
    """One check. Returns (passed, detail)."""
    kind = check["type"]
    if kind == "shell":
        proc = subprocess.run(check["cmd"], shell=True, cwd=workdir,
                              capture_output=True, text=True, timeout=120)
        ok = proc.returncode == 0
        if ok and "stdout_equals" in check:
            ok = proc.stdout.strip() == check["stdout_equals"]
        if ok and "stdout_contains" in check:
            ok = check["stdout_contains"] in proc.stdout
        detail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        if not ok and proc.stderr.strip():
            detail = proc.stderr.strip().splitlines()[-1]
        return ok, detail
    if kind == "output_contains":
        return check["text"] in output, ""
    if kind == "output_not_contains":
        return check["text"] not in output, ""
    if kind == "file_contains":
        path = os.path.join(workdir, check["file"])
        try:
            with open(path) as f:
                return check["text"] in f.read(), ""
        except FileNotFoundError:
            return False, f"{check['file']} was not created"
    raise ValueError(f"unknown check type: {kind}")


def run_agent(prompt, task_id, model, effort, workdir):
    """One headless agent run, inside the task's temp directory.
    Returns (result_text, cost_usd, raw)."""
    env = dict(os.environ)
    env["NERF_WATCH_TASK_ID"] = task_id
    cmd = shlex.split(AGENT_CMD) + ["--bare", "-p", prompt,
           "--model", model, "--effort", effort,
           "--output-format", "json",
           "--max-turns", MAX_TURNS, "--max-budget-usd", MAX_BUDGET_USD,
           "--allowedTools", "Read Write Edit Bash Glob Grep",
           "--permission-mode", "acceptEdits"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=600, env=env, cwd=workdir)
    if proc.returncode != 0:
        return "", None, proc.stderr.strip()[-500:]
    try:
        data = json.loads(proc.stdout)
        return data.get("result", ""), data.get("total_cost_usd"), ""
    except json.JSONDecodeError:
        return proc.stdout, None, ""


def run_task(task, model, effort):
    workdir = tempfile.mkdtemp(prefix=f"nerf-watch-{task['id']}-")
    fixture = os.path.join(FIXTURES, task["fixture"])
    for name in os.listdir(fixture):
        src = os.path.join(fixture, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(workdir, name))
        else:
            shutil.copy2(src, os.path.join(workdir, name))
    started = datetime.datetime.now(datetime.timezone.utc)
    output, cost, error = run_agent(task["prompt"], task["id"], model,
                                    effort, workdir)
    results = []
    for check in task["checks"]:
        try:
            passed, detail = run_check(check, workdir, output)
        except subprocess.TimeoutExpired:
            passed, detail = False, "check timed out"
        results.append({"desc": check["desc"], "passed": passed,
                        "detail": detail})
    shutil.rmtree(workdir, ignore_errors=True)
    return {
        "task": task["id"],
        "title": task["title"],
        "passed": all(r["passed"] for r in results),
        "checks": results,
        "cost_usd": cost,
        "error": error,
        "seconds": round(
            (datetime.datetime.now(datetime.timezone.utc) - started)
            .total_seconds(), 1),
    }


def claude_version():
    try:
        proc = subprocess.run(shlex.split(AGENT_CMD) + ["--version"], capture_output=True,
                              text=True, timeout=30)
        return proc.stdout.strip() or proc.stderr.strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--out", default=os.path.join(SKILL, "results"))
    parser.add_argument("--task", default=None,
                        help="run one task by id")
    parser.add_argument("--dry-run", action="store_true",
                        help="list tasks without running them")
    args = parser.parse_args()

    tasks = load_tasks()
    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        if not tasks:
            print(f"unknown task: {args.task}")
            return 1
    if args.dry_run:
        for t in tasks:
            print(f"{t['id']}: {t['title']} ({len(t['checks'])} checks)")
        return 0

    today = datetime.date.today().isoformat()
    run = {
        "date": today,
        "model": args.model,
        "effort": args.effort,
        "agent_cmd": AGENT_CMD,
        "cli_version": claude_version(),
        "tasks": [run_task(t, args.model, args.effort) for t in tasks],
    }
    run["passed"] = sum(1 for t in run["tasks"] if t["passed"])
    run["total"] = len(run["tasks"])
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{today}-{args.model}-{args.effort}.json")
    with open(path, "w") as f:
        json.dump(run, f, indent=2)
    for t in run["tasks"]:
        mark = "PASS" if t["passed"] else "FAIL"
        print(f"[{mark}] {t['task']}: {t['title']}")
        for c in t["checks"]:
            if not c["passed"]:
                print(f"       failed: {c['desc']} {c['detail']}")
    print(f"{run['passed']}/{run['total']} passed -> {path}")
    return 0 if run["passed"] == run["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
