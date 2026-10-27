#!/usr/bin/env python3
"""Run the flightsim detonation of every rule validated by flightsim alone.

Covers rules at lifecycle stage in_test or production whose validation method
is flightsim. Rules with a Threatest scenario are detonated by Threatest
instead, which also asserts that the alert fired.

This is tier 4 in docs/testing-strategy.md. It proves the traffic left and the
telemetry can arrive, not that the rule fired, so it never stamps
last_validated. An analyst who confirms the alert from this run stamps it by
hand, with the run as evidence, or the rule moves to a Threatest scenario.

Each command runs on DETONATION_HOST over SSH, one at a time, never on the
runner: assertions bind on source address and time window, and a detonation
from a second address muddies that. Run this after Threatest has finished so
the two do not overlap. Writes build/flightsim-results.json in the shape
Threatest uses, so the failure handling reads both. Exit code 1 if any
detonation failed.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone

import rulefile
from scenarios import flightsim_problem

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGES = {"in_test", "production"}


def select():
    for path in sorted((ROOT / "detections").rglob("*.y*ml")):
        rule = rulefile.load_rule(path)
        de = rule["detection_engineering"]
        if de["validation"]["method"] == "flightsim" and de["lifecycle"]["stage"] in STAGES:
            yield rule


def detonate(rule, target, keyfile, timeout):
    command = rule["detection_engineering"]["validation"]["detonation_command"]
    started = datetime.now(timezone.utc)
    result = {
        "description": f"flightsim: {rule['title']}",
        "timeDetonated": started.isoformat(timespec="seconds"),
        "durationSeconds": 0,
    }
    if problem := flightsim_problem(command):
        return {**result, "isSuccess": False, "errorMessage": f"not run, {command} {problem}"}

    # Rejoined from the parsed words so the remote shell sees exactly the
    # flightsim arguments the validator checked, and nothing it can interpret.
    ssh = ["ssh", "-o", "BatchMode=yes", *(["-i", keyfile] if keyfile else []), target,
           shlex.join(shlex.split(command))]
    clock = time.monotonic()
    try:
        proc = subprocess.run(ssh, capture_output=True, text=True, timeout=timeout)
        ok, error = proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    except subprocess.TimeoutExpired:
        ok, error = False, f"timed out after {timeout}s"
    return {
        **result,
        "isSuccess": ok,
        "errorMessage": "" if ok else error,
        "durationSeconds": round(time.monotonic() - clock),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("DETONATION_HOST"))
    ap.add_argument("--user", default=os.environ.get("DETONATION_USER"))
    ap.add_argument("--ssh-keyfile")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per detonation")
    ap.add_argument("--output", type=pathlib.Path, default=ROOT / "build" / "flightsim-results.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rules = list(select())
    if not rules:
        print("no rules at in_test or production use flightsim alone, nothing to detonate")
        return 0
    if args.dry_run:
        for rule in rules:
            print(f"would run {rule['detection_engineering']['validation']['detonation_command']} for {rule['title']}")
        return 0
    if not args.host:
        sys.exit("set DETONATION_HOST or pass --host")

    target = f"{args.user}@{args.host}" if args.user else args.host
    results = []
    for rule in rules:
        r = detonate(rule, target, args.ssh_keyfile, args.timeout)
        print(f"{'pass' if r['isSuccess'] else 'FAIL'} {r['description']}")
        results.append(r)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2))
    return 0 if all(r["isSuccess"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
