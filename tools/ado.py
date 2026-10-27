#!/usr/bin/env python3
"""Azure DevOps glue for the pipelines: work items and the stamp pull request.

Talks to the Azure DevOps REST API with the standard library, so the self
hosted detonation agent needs nothing beyond what stamp_validation.py already
requires.

  stamp-pr               open the stamp pull request unless one is already active
  detonation-failures    one tuning work item per failed scenario, commented on repeat
  hygiene                one standing hygiene work item, closed on a clean run

In a pipeline the organisation, project, repository and build come from the
predefined variables, and the token from System.AccessToken, which a step must
map explicitly as SYSTEM_ACCESSTOKEN. Outside a pipeline set
SYSTEM_COLLECTIONURI and SYSTEM_TEAMPROJECT yourself and put a personal access
token in AZURE_DEVOPS_EXT_PAT.

Work item type and closed state depend on the process. The defaults suit Basic
(Issue, Done). Agile and CMMI use Issue and Closed. Scrum has no Issue type;
use Impediment and Closed. Set WORK_ITEM_TYPE and WORK_ITEM_CLOSED_STATE as
pipeline variables to change them, and AREA_PATH to file somewhere other than
the project root area.
"""
import argparse
import base64
import html
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

API = "7.1"
WORK_ITEM_TYPE = os.environ.get("WORK_ITEM_TYPE") or "Issue"
CLOSED_STATE = os.environ.get("WORK_ITEM_CLOSED_STATE") or "Done"


class Client:
    def __init__(self, org=None, project=None):
        self.org = (org or os.environ.get("SYSTEM_COLLECTIONURI") or "").rstrip("/") + "/"
        self.project = project or os.environ.get("SYSTEM_TEAMPROJECT")
        if self.org == "/" or not self.project:
            sys.exit("set SYSTEM_COLLECTIONURI and SYSTEM_TEAMPROJECT, or pass --org and --project")
        if token := os.environ.get("SYSTEM_ACCESSTOKEN"):
            self.auth = f"Bearer {token}"
        elif token := os.environ.get("AZURE_DEVOPS_EXT_PAT"):
            self.auth = "Basic " + base64.b64encode(f":{token}".encode()).decode()
        else:
            sys.exit("map System.AccessToken to SYSTEM_ACCESSTOKEN, or set AZURE_DEVOPS_EXT_PAT")

    def url(self, path, base=None, **params):
        params.setdefault("api-version", API)
        base = base or f"{self.org}{urllib.parse.quote(self.project)}/"
        return f"{base}{path}?{urllib.parse.urlencode(params)}"

    def call(self, method, url, body=None, content_type="application/json"):
        req = urllib.request.Request(
            url,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": self.auth, "Content-Type": content_type, "Accept": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            sys.exit(f"{method} {url} failed, HTTP {exc.code}: {exc.read().decode(errors='replace')[:2000]}")
        return json.loads(raw) if raw else None

    def run_url(self):
        build = os.environ.get("BUILD_BUILDID")
        if not build:
            return "local run"
        return f"{self.org}{urllib.parse.quote(self.project)}/_build/results?buildId={build}"

    # Work items

    def find_open(self, title):
        """Id of an open work item of our type with exactly this title, or None."""
        q = lambda s: s.replace("'", "''")
        wiql = (
            "SELECT [System.Id] FROM WorkItems"
            " WHERE [System.TeamProject] = @project"
            f" AND [System.WorkItemType] = '{q(WORK_ITEM_TYPE)}'"
            f" AND [System.Title] = '{q(title)}'"
            f" AND [System.State] NOT IN ('{q(CLOSED_STATE)}', 'Removed')"
        )
        items = self.call("POST", self.url("_apis/wit/wiql"), {"query": wiql})["workItems"]
        return items[0]["id"] if items else None

    def patch(self, method, path, fields):
        ops = [{"op": "add", "path": f"/fields/{k}", "value": v} for k, v in fields.items()]
        return self.call(method, self.url(path), ops, "application/json-patch+json")

    def create(self, title, description, tags):
        fields = {"System.Title": title, "System.Description": description, "System.Tags": tags}
        if area := os.environ.get("AREA_PATH"):
            fields["System.AreaPath"] = area
        item = self.patch("POST", f"_apis/wit/workitems/${urllib.parse.quote(WORK_ITEM_TYPE)}", fields)
        print(f"opened work item #{item['id']}: {title}")
        return item["id"]

    def update(self, item_id, **fields):
        """Fields by reference name with dots as underscores, System_History adds a comment."""
        self.patch("PATCH", f"_apis/wit/workitems/{item_id}", {k.replace("_", "."): v for k, v in fields.items()})


def pre(text):
    return f"<pre>{html.escape(text)}</pre>"


def link(url):
    return f'<a href="{html.escape(url)}">{html.escape(url)}</a>'


def stamp_pr(args, client):
    repo_id = os.environ.get("BUILD_REPOSITORY_ID") or sys.exit("BUILD_REPOSITORY_ID is not set")
    repo = client.call("GET", client.url(f"_apis/git/repositories/{repo_id}"))
    source = f"refs/heads/{args.branch}"
    active = client.call("GET", client.url(
        f"_apis/git/repositories/{repo_id}/pullrequests",
        **{"searchCriteria.sourceRefName": source, "searchCriteria.status": "active"},
    ))["value"]
    if active:
        print(f"stamp pull request already open: {repo['webUrl']}/pullrequest/{active[0]['pullRequestId']}")
        return 0
    pr = client.call("POST", client.url(f"_apis/git/repositories/{repo_id}/pullrequests"), {
        "sourceRefName": source,
        "targetRefName": repo["defaultBranch"],
        "title": "Stamp last_validated from nightly detonation",
        "description": "\n".join([
            "Rules whose Threatest scenario passed in the nightly detonation run.",
            "",
            f"Run: {client.run_url()}",
            "",
            "This branch is rebuilt from the default branch on every run with changes.",
            "Merge it to record validation; the coverage metrics read last_validated from main.",
        ]),
    })
    print(f"opened {repo['webUrl']}/pullrequest/{pr['pullRequestId']}")
    return 0


def detonation_failures(args, client):
    # Threatest writes one file per scenario file and flightsim one more. A
    # missing or unreadable file means that detonation did not get as far as
    # writing results, which the run's own failure already reports.
    results = []
    for path in args.results:
        try:
            results += json.loads(path.read_text())
        except (OSError, ValueError):
            pass
    failed = [r for r in results if not r.get("isSuccess")]
    run = client.run_url()

    for r in failed:
        title = f"[tuning] detonation failed: {r.get('description')}"
        detail = [
            pre((r.get("errorMessage") or "no error message")[:4000]),
            f"<p>Detonated at {html.escape(str(r.get('timeDetonated')))}, ran for {html.escape(str(r.get('durationSeconds')))}s.</p>",
            f"<p>Run: {link(run)}</p>",
        ]
        if existing := client.find_open(title):
            client.update(existing, System_History="<p>Failed again.</p>" + "".join(detail))
            print(f"commented on work item #{existing}: {title}")
            continue
        name = html.escape(str(r.get("description")))
        if str(r.get("description")).startswith("flightsim: "):
            body = [
                f"<p><b>{name}</b> did not complete on the detonation host.</p>",
                *detail,
                "<p>flightsim alone does not check the alert, so this is a detonation problem:"
                " the host is unreachable, flightsim failed, or the command was refused as unsafe.</p>",
            ]
        else:
            body = [
                f"<p>Scenario <b>{name}</b> did not produce the expected signal.</p>",
                *detail,
                "<p>A failure here means one of: the rule broke, the data source stopped flowing,"
                " the detonation was blocked by a control, or the timeout is too short."
                " Distinguish blocked from undetected before tuning the rule.</p>",
            ]
        client.create(title, "".join(body), "tuning; detonation-failure")
    return 0


def hygiene(args, client):
    title = "Weekly detection hygiene findings"
    findings = [l for l in args.report.read_text().splitlines() if l.startswith(("WARN ", "ERROR "))]
    existing = client.find_open(title)
    run = client.run_url()

    if not findings:
        if existing:
            client.update(existing, System_History=f"<p>Clean run, closing. {link(run)}</p>", System_State=CLOSED_STATE)
            print(f"closed work item #{existing}")
        return 0

    body = "".join([
        f"<p>{len(findings)} findings from the hygiene run on {date.today().isoformat()}.</p>",
        "<p>Stale review: re-review the rule and bump <code>last_reviewed</code>, or start deprecation.<br>",
        "Decaying validation: find out why the nightly detonation stopped passing.<br>",
        "Errors: the rule no longer meets the schema or program standards.</p>",
        pre("\n".join(findings)[:60000]),
        f"<p>Run: {link(run)}</p>",
    ])
    if existing:
        client.update(existing, System_Description=body)
        print(f"updated work item #{existing}")
    else:
        client.create(title, body, "hygiene")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--org", help="organisation URL, defaults to SYSTEM_COLLECTIONURI")
    ap.add_argument("--project", help="project name, defaults to SYSTEM_TEAMPROJECT")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("stamp-pr")
    p.add_argument("--branch", required=True)
    p.set_defaults(func=stamp_pr)

    p = sub.add_parser("detonation-failures")
    p.add_argument("results", type=pathlib.Path, nargs="+")
    p.set_defaults(func=detonation_failures)

    p = sub.add_parser("hygiene")
    p.add_argument("report", type=pathlib.Path)
    p.set_defaults(func=hygiene)

    args = ap.parse_args()
    return args.func(args, Client(args.org, args.project))


if __name__ == "__main__":
    sys.exit(main())
