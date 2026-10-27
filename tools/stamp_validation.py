#!/usr/bin/env python3
"""Stamp detection_engineering.validation.last_validated after a passing run.

Reads one or more Threatest --output JSON files, matches each passing scenario
back to the rule whose signal name it asserted, and writes today's date onto
that rule. flightsim results never reach this script: a standalone flightsim
run proves telemetry, not that the alert fired.

This is what makes "percentage of rules validated in the last 30 days" a
measurement rather than a claim. Intended to run in CI and commit the diff.
"""
import argparse
import json
import pathlib
import re
import sys
from datetime import date

import rulefile
import scenarios

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAST_VALIDATED = re.compile(r"^(\s+last_validated:[ \t]*).*$", re.MULTILINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=pathlib.Path, nargs="+")
    ap.add_argument("--scenarios", type=pathlib.Path, default=ROOT / "scenarios")
    args = ap.parse_args()

    expected = {}
    for sc in scenarios.files(args.scenarios):
        expected.update(scenarios.signal_names(sc))

    passed_signals = {
        expected[r["description"]]
        for results in args.results
        for r in json.loads(results.read_text())
        if r.get("isSuccess") and r.get("description") in expected
    }
    if not passed_signals:
        print("no passing scenarios mapped to a signal name, nothing stamped")
        return 0

    today = date.today().isoformat()
    stamped = 0
    for path in sorted((ROOT / "detections").rglob("*.y*ml")):
        text = path.read_text()
        rule = rulefile.load_rule(path)
        if rule.get("title") not in passed_signals:
            continue
        # Quoted, because the schema requires a string and YAML reads a bare
        # ISO date as a date object.
        text, n = LAST_VALIDATED.subn(rf'\g<1>"{today}"', text, count=1)
        if not n:
            print(f"no last_validated line in {path.relative_to(ROOT)}, not stamped")
            continue
        path.write_text(text)
        stamped += 1
        print(f"stamped {path.relative_to(ROOT)} last_validated={today}")

    print(f"{stamped} rules stamped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
