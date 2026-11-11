#!/usr/bin/env python3
"""Compare two nerf-watch runs and say whether the model got worse.

    python compare.py results/2026-11-04-....json results/2026-11-11-....json

Prints each task's pass/fail in both runs and exits 1 when the newer run
passes two or more fewer tasks than the older one — the threshold this
suite uses for "something changed, look into it". One task flipping is
noise on an 8-task panel; two is worth an hour of your time.

A drop does not prove a nerf. Before blaming the model, check the
three harness facts the SKILL.md lists: the CLI version, the effort
level, and whether any task file changed since the older run.
"""
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    if len(sys.argv) != 3:
        print("usage: compare.py <older-run.json> <newer-run.json>")
        return 2
    old, new = load(sys.argv[1]), load(sys.argv[2])
    old_tasks = {t["task"]: t["passed"] for t in old["tasks"]}
    print(f"older: {old['date']} {old['model']} {old['effort']} "
          f"({old['cli_version']}) -> {old['passed']}/{old['total']}")
    print(f"newer: {new['date']} {new['model']} {new['effort']} "
          f"({new['cli_version']}) -> {new['passed']}/{new['total']}")
    print()
    for t in new["tasks"]:
        was = old_tasks.get(t["task"])
        mark = "PASS" if t["passed"] else "FAIL"
        prev = "PASS" if was else ("FAIL" if was is False else "?")
        flag = "" if was == t["passed"] else "  <-- CHANGED"
        print(f"  {t['task']:<18} {prev} -> {mark}{flag}")
    drop = old["passed"] - new["passed"]
    print()
    if old["model"] != new["model"] or old["effort"] != new["effort"]:
        print("Note: model or effort differs between runs — this is not "
              "a like-for-like comparison.")
    if drop >= 2:
        print(f"Passes fell by {drop}. Something changed — work through "
              "the checklist in SKILL.md before concluding it is the model.")
        return 1
    if drop == 1:
        print("One task flipped. On an 8-task panel that is noise until "
              "it repeats — re-run before drawing a conclusion.")
        return 0
    print("No drop. Whatever changed this week, this suite cannot see it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
