#!/usr/bin/env python3
"""Read Threatest scenario files and check flightsim commands.

A scenario asserts a rule through the alert name its expectation matches,
which is the rule title. The validator uses this to check that scenarios and
titles agree, stamp_validation.py to map a passing scenario back to its rule,
and the nightly job to find the scenario files that have anything to run.

  python tools/scenarios.py active    print scenario files with active scenarios
"""
import pathlib
import shlex
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
MATCHERS = ("datadogSecuritySignal", "elasticSecuritySignal")

# flightsim modules kept out of scheduled runs, see docs/testing-strategy.md.
UNSCHEDULED_MODULES = {"scan", "spambot", "ssh-exfil", "ssh-transfer"}


def files(root=ROOT / "scenarios"):
    return sorted(root.rglob("*.threatest.yaml"))


def load(path):
    """Active scenarios in a file. A file whose scenarios are all commented out has none."""
    return (yaml.safe_load(path.read_text()) or {}).get("scenarios") or []


def active_files(root=ROOT / "scenarios"):
    return [f for f in files(root) if load(f)]


def signal_names(path):
    """Map scenario name to the alert name it asserts."""
    out = {}
    for sc in load(path):
        for exp in sc.get("expectations", []):
            for matcher in MATCHERS:
                if matcher in exp:
                    out[sc["name"]] = exp[matcher]["name"]
    return out


def remote_commands(path):
    """(scenario name, command) for every remoteDetonator command in a file."""
    for sc in load(path):
        for cmd in ((sc.get("detonate") or {}).get("remoteDetonator") or {}).get("commands", []):
            yield sc["name"], cmd


def flightsim_problem(command):
    """Why a flightsim command must not run on a schedule, or None if it may."""
    argv = shlex.split(command)
    if argv[:2] != ["flightsim", "run"]:
        return "does not start with flightsim run"
    modules = set(argv[2].split(",")) if len(argv) > 2 and not argv[2].startswith("-") else set()
    if not modules:
        return "names no module, name the modules to run explicitly"
    if blocked := modules & UNSCHEDULED_MODULES:
        return f"runs {', '.join(sorted(blocked))}, which is excluded from scheduled runs"
    return None


def main():
    if sys.argv[1:] != ["active"]:
        sys.exit(__doc__)
    for path in active_files():
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
