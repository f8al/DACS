#!/usr/bin/env python3
"""Tell the SOC what a release put into production.

Posts a plain {"text": ...} JSON body to SOC_WEBHOOK, which Slack, Teams
workflow and most chat or ticketing webhooks accept as is. Reshape payload()
for anything that expects a different body.

Runs after the rules are already deployed, so a notification failure warns and
exits 0 rather than failing the release. Unset SOC_WEBHOOK skips notification.
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.request

import rulefile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def production_rules():
    for path in sorted((ROOT / "detections").rglob("*.y*ml")):
        rule = rulefile.load_rule(path)
        if rule["detection_engineering"]["lifecycle"]["stage"] == "production":
            yield rule


def payload(release, rules):
    lines = [f"Detection release {release} deployed to production, {len(rules)} rules live."]
    lines += [f"- {r['title']} ({r['level']}, {r['detection_engineering']['operations']['response_action']})" for r in rules]
    return {"text": "\n".join(lines)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    body = payload(args.release, list(production_rules()))
    webhook = os.environ.get("SOC_WEBHOOK")
    if args.dry_run or not webhook:
        if not webhook:
            print("SOC_WEBHOOK not set, not notifying")
        print(json.dumps(body, indent=2))
        return 0

    req = urllib.request.Request(
        webhook,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"notified SOC, HTTP {resp.status}")
    except OSError as exc:
        print(f"##vso[task.logissue type=warning]SOC notification failed, rules are deployed: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
