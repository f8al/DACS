#!/usr/bin/env python3
"""Gate 1 and gate 2 of the pipeline.

Validates every detection file against schema/detection.schema.json and applies
the program rules that a JSON schema cannot express on its own:

  * rule IDs are globally unique
  * ATT&CK tags resolve to a known technique format
  * a rule at lifecycle stage production must have a validation method other
    than none, a non null last_validated date, an ADS file that exists and a
    runbook file that exists
  * a rule is stale when last_reviewed is older than review_interval_days
  * a scenario_file or detonation_command referenced by a rule exists
  * a rule validated by threatest is asserted by its scenario_file under its
    exact title, and every active scenario asserts the title of a real rule
  * no flightsim command, in a rule or a scenario, names no module or runs a
    module excluded from scheduled runs
  * base rules of a correlation are well formed and every correlation
    reference resolves to a base rule in the same file
  * no condition uses the deprecated Sigma pipe aggregation syntax

Exit code 1 on any error. Warnings do not fail the build.
"""
import json
import pathlib
import re
import sys
from datetime import date, datetime

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit("missing dependencies: pip install -r tools/requirements.txt")

import rulefile
import scenarios

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "detection.schema.json").read_text())
ATTACK_TAG = re.compile(r"^attack\.(t\d{4}(\.\d{3})?|[a-z_]+)$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

errors, warnings, seen_ids = [], [], {}


def parse_date(value):
    """YAML parses an unquoted ISO date into a date object. Accept both."""
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def check(rule, path):
    rid = rule.get("id", "<no id>")
    prefix = f"{path}: "

    for err in sorted(Draft202012Validator(SCHEMA).iter_errors(rule), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{prefix}{loc}: {err.message}")

    check_id(rid, path)

    for tag in rule.get("tags", []):
        if tag.startswith("attack.") and not ATTACK_TAG.match(tag):
            errors.append(f"{prefix}malformed ATT&CK tag {tag}")

    de = rule.get("detection_engineering") or {}
    life, val, ops = de.get("lifecycle", {}), de.get("validation", {}), de.get("operations", {})

    if life.get("stage") == "production":
        if val.get("method") in (None, "none"):
            errors.append(f"{prefix}production rule has no validation method")
        if not val.get("last_validated"):
            errors.append(f"{prefix}production rule has never been validated")
        if rule.get("status") == "draft":
            errors.append(f"{prefix}production lifecycle stage with draft Sigma status")

    for key in ("ads", "runbook"):
        ref = ops.get(key)
        if ref and not (ROOT / ref).exists():
            errors.append(f"{prefix}{key} points at missing file {ref}")

    scenario = val.get("scenario_file")
    if scenario and not (ROOT / scenario).exists():
        errors.append(f"{prefix}scenario_file points at missing file {scenario}")
    if val.get("method") == "threatest" and not scenario:
        errors.append(f"{prefix}validation method threatest requires a scenario_file")
    if val.get("method") == "threatest" and scenario and (ROOT / scenario).exists():
        if rule.get("title") not in scenarios.signal_names(ROOT / scenario).values():
            errors.append(f"{prefix}no active scenario in {scenario} asserts the title {rule.get('title')!r}")
    if val.get("method") == "flightsim":
        command = val.get("detonation_command")
        if not command:
            errors.append(f"{prefix}validation method flightsim requires a detonation_command")
        elif problem := scenarios.flightsim_problem(command):
            errors.append(f"{prefix}detonation_command {command} {problem}")

    reviewed, interval = life.get("last_reviewed"), life.get("review_interval_days")
    if reviewed and interval:
        age = (date.today() - parse_date(reviewed)).days
        if age > interval:
            warnings.append(f"{prefix}stale, last reviewed {age} days ago, interval is {interval}")

    validated = val.get("last_validated")
    if life.get("stage") == "production" and validated:
        age = (date.today() - parse_date(validated)).days
        if age > 30:
            warnings.append(f"{prefix}last validated {age} days ago, detonation coverage is decaying")


def check_id(rid, path):
    if rid in seen_ids:
        errors.append(f"{path}: duplicate rule id {rid}, also in {seen_ids[rid]}")
    seen_ids[rid] = path


def check_file(docs, path):
    """Checks that span the documents of one file."""
    prefix = f"{path}: "
    for doc in docs:
        condition = (doc.get("detection") or {}).get("condition")
        for c in condition if isinstance(condition, list) else [condition]:
            if isinstance(c, str) and "|" in c:
                errors.append(f"{prefix}condition uses deprecated pipe aggregation, write a Sigma correlation instead: {c}")

    bases = [d for d in docs if "detection_engineering" not in d]
    for base in bases:
        missing = [k for k in ("title", "id", "name", "logsource", "detection") if k not in base]
        if missing:
            errors.append(f"{prefix}base rule {base.get('title', '<untitled>')} is missing {', '.join(missing)}")
        if "correlation" in base:
            errors.append(f"{prefix}correlation {base.get('title', '<untitled>')} has no detection_engineering block")
        if base.get("id") is not None:
            if not UUID.match(str(base["id"])):
                errors.append(f"{prefix}base rule id {base['id']} is not a UUID")
            check_id(base["id"], path)

    refs = {str(d[k]) for d in bases for k in ("name", "id") if d.get(k)}
    for doc in docs:
        for ref in (doc.get("correlation") or {}).get("rules", []):
            if ref not in refs:
                errors.append(f"{prefix}correlation references {ref}, which is not a base rule in this file")


def check_scenarios(titles):
    """Checks that start from the scenario files rather than the rules."""
    for path in scenarios.files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            asserted = scenarios.signal_names(path)
            commands = list(scenarios.remote_commands(path))
        except (yaml.YAMLError, AttributeError, KeyError, TypeError) as exc:
            errors.append(f"{rel}: unreadable scenario file: {exc}")
            continue
        for name, title in asserted.items():
            if title not in titles:
                errors.append(f"{rel}: scenario {name!r} asserts {title!r}, which is no rule's title")
        for name, command in commands:
            if command.lstrip().startswith("flightsim") and (problem := scenarios.flightsim_problem(command)):
                errors.append(f"{rel}: scenario {name!r} command {command} {problem}")


def main():
    files = sorted((ROOT / "detections").rglob("*.yml")) + sorted((ROOT / "detections").rglob("*.yaml"))
    if not files:
        sys.exit("no detection files found under detections/")
    titles = set()
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            docs = rulefile.load_documents(path)
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: unparsable YAML: {exc}")
            continue
        if not docs or not all(isinstance(d, dict) for d in docs):
            errors.append(f"{rel}: every document must be a mapping")
            continue
        rule = rulefile.primary(docs)
        if rule is None:
            errors.append(f"{rel}: expected exactly one document with a detection_engineering block")
            continue
        titles.add(rule.get("title"))
        check(rule, rel)
        check_file(docs, rel)
    check_scenarios(titles)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(files)} rules checked, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
