#!/usr/bin/env python3
"""One time Azure DevOps setup for a repository created from this scaffold.

Does what CODEOWNERS and repository settings did on GitHub:

  * registers the validate, deploy and hygiene pipelines, and detonate-nightly
    only when --with-detonation is passed
  * on the default branch, a two approval minimum, a blocking validate build,
    a work item linking reminder, and one Required reviewers policy per entry
    in .azuredevops/reviewers.yml
  * creates or updates the work item templates in .azuredevops/work-item-templates/
    for one team

Safe to rerun: pipelines are matched by name, policies by type and path or
build, templates by name. It never deletes or edits an existing policy, so
change a policy that already exists in Project settings, Repositories,
Policies, or delete it there and rerun.

Run it from a workstation with a personal access token in AZURE_DEVOPS_EXT_PAT
that has Code (read, write and manage), Build (read and execute), Work Items
(read and write), Identity (read) and Project and Team (read):

  python tools/ado_setup.py --org https://dev.azure.com/your-org \\
      --project your-project --repo detections
"""
import argparse
import pathlib
import sys
import urllib.parse

import yaml

from ado import WORK_ITEM_TYPE, Client

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADO = ROOT / ".azuredevops"
PIPELINES = ["validate", "deploy", "hygiene"]


def ensure_pipelines(client, repo, names):
    existing = {p["name"]: p["id"] for p in client.call("GET", client.url("_apis/pipelines"))["value"]}
    for name in names:
        if name in existing:
            print(f"pipeline {name} exists, id {existing[name]}")
            continue
        created = client.call("POST", client.url("_apis/pipelines"), {
            "name": name,
            "folder": "\\",
            "configuration": {
                "type": "yaml",
                "path": f"/.azuredevops/pipelines/{name}.yml",
                "repository": {"id": repo["id"], "name": repo["name"], "type": "azureReposGit"},
            },
        })
        existing[name] = created["id"]
        print(f"pipeline {name} created, id {created['id']}")
    return existing


def identity(client, name):
    """Descriptor id of a group such as [project]\\team, via the identity service."""
    parts = urllib.parse.urlsplit(client.org)
    if parts.netloc == "dev.azure.com":
        base = f"https://vssps.dev.azure.com{parts.path}"
    else:
        base = f"{parts.scheme}://{parts.netloc.replace('.visualstudio.com', '.vssps.visualstudio.com')}/"
    found = client.call("GET", client.url(
        "_apis/identities", base=base, searchFilter="General", filterValue=name, queryMembership="None",
    ))["value"]
    if not found:
        sys.exit(f"no identity named {name}, check .azuredevops/reviewers.yml")
    return found[0]["id"]


def reviewer_policies(client):
    """CODEOWNERS semantics: the last matching entry wins, so each entry excludes
    the paths of every entry after it. Azure DevOps would otherwise apply every
    matching policy at once."""
    entries = yaml.safe_load((ADO / "reviewers.yml").read_text())
    for i, entry in enumerate(entries):
        patterns = [entry["path"]] + [f"!{later['path']}" for later in entries[i + 1:]]
        yield "Required reviewers", {
            "requiredReviewerIds": [identity(client, g) for g in entry["groups"]],
            "minimumApproverCount": 1,
            "creatorVoteCounts": False,
            "filenamePatterns": patterns,
            "message": f"Owners of {entry['path']}",
        }, True


def ensure_policies(client, repo, validate_id):
    branch = repo["defaultBranch"]
    scope = [{"repositoryId": repo["id"], "refName": branch, "matchKind": "exact"}]
    types = {t["displayName"]: t["id"] for t in client.call("GET", client.url("_apis/policy/types"))["value"]}
    existing = client.call("GET", client.url(
        "_apis/git/policy/configurations", repositoryId=repo["id"], refName=branch,
    ))["value"]

    def key(type_id, settings):
        return type_id, settings.get("buildDefinitionId"), tuple(settings.get("filenamePatterns") or ())

    have = {key(p["type"]["id"], p["settings"]) for p in existing}

    wanted = [
        # Approvals reset on every push, and the last pusher cannot approve, so
        # nobody can collect two approvals and then push different code.
        ("Minimum number of reviewers", {
            "minimumApproverCount": 2,
            "creatorVoteCounts": False,
            "allowDownvotes": False,
            "resetOnSourcePush": True,
            "blockLastPusherVote": True,
        }, True),
        # No path filter: the validator checks ADS and runbook files under docs/
        # as well as the rules, so every pull request needs it.
        ("Build", {
            "buildDefinitionId": validate_id,
            "displayName": "validate",
            "queueOnSourceUpdateOnly": False,
            "manualQueueOnly": False,
            "validDuration": 0,
        }, True),
        # A reminder rather than a gate, because the automated stamp pull
        # request has no work item to link.
        ("Work item linking", {}, False),
        *reviewer_policies(client),
    ]
    for type_name, settings, blocking in wanted:
        type_id = types[type_name]
        label = f"{type_name} {settings.get('filenamePatterns', [''])[0]}".strip()
        if key(type_id, settings) in have:
            print(f"policy {label} exists on {branch}")
            continue
        client.call("POST", client.url("_apis/policy/configurations"), {
            "isEnabled": True,
            "isBlocking": blocking,
            "type": {"id": type_id},
            "settings": {**settings, "scope": scope},
        })
        print(f"policy {label} created on {branch}")


def ensure_templates(client, team):
    path = f"{urllib.parse.quote(team)}/_apis/wit/templates"
    existing = {
        t["name"]: t["id"]
        for t in client.call("GET", client.url(path, workitemtypename=WORK_ITEM_TYPE))["value"]
    }
    for src in sorted((ADO / "work-item-templates").glob("*.yml")):
        tpl = yaml.safe_load(src.read_text())
        body = {**tpl, "workItemTypeName": WORK_ITEM_TYPE}
        if tpl["name"] in existing:
            client.call("PUT", client.url(f"{path}/{existing[tpl['name']]}"), body)
            print(f"template {tpl['name']} updated for {team}")
        else:
            client.call("POST", client.url(path), body)
            print(f"template {tpl['name']} created for {team}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--org", required=True, help="organisation URL, https://dev.azure.com/your-org")
    ap.add_argument("--project", required=True)
    ap.add_argument("--repo", required=True, help="repository name")
    ap.add_argument("--team", help="team that owns the work item templates, defaults to '<project> Team'")
    ap.add_argument("--with-detonation", action="store_true",
                    help="also register detonate-nightly, see README before passing this")
    args = ap.parse_args()

    client = Client(args.org, args.project)
    repo = client.call("GET", client.url(f"_apis/git/repositories/{urllib.parse.quote(args.repo)}"))
    names = PIPELINES + (["detonate-nightly"] if args.with_detonation else [])
    pipelines = ensure_pipelines(client, repo, names)
    ensure_policies(client, repo, pipelines["validate"])
    ensure_templates(client, args.team or f"{args.project} Team")
    return 0


if __name__ == "__main__":
    sys.exit(main())
