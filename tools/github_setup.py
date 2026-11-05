#!/usr/bin/env python3
"""One time CODEOWNERS setup for a repository created from this scaffold.

Rewrites .github/CODEOWNERS with the real organisation in place of your-org,
and renames the teams given with --team. Commit the file afterwards. Branch
protection and environments are still set by hand, see README step 5.

  python tools/github_setup.py --org acme \\
      --team detection-engineering=csirt --team soc-leads=soc

--team renames a team by its slug, the part after the slash. A new name
without an org/ prefix gets the --org one. Safe to rerun with the same flags.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
PLACEHOLDER = "your-org"
TEAM = re.compile(r"@([\w.-]+)/([\w.-]+)")


def slug(team):
    """The part after the slash in [@]org/team."""
    return team.lstrip("@").partition("/")[2] or team


def team_name(owner, team, org, renames):
    """@your-org/team with the real org, or the --team replacement."""
    team = renames.get(team, team)
    if "/" in team:
        return "@" + team.lstrip("@")
    return f"@{org if owner == PLACEHOLDER else owner}/{team}"


def rewrite_codeowners(text, org, renames):
    """CODEOWNERS text with every team owner passed through team_name. Comment
    lines are left alone."""
    lines = text.splitlines(keepends=True)
    owners = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    present = {m.group(2) for line in owners for m in TEAM.finditer(line)}
    # A rename whose target is already there was applied by an earlier run.
    done = {old for old, new in renames.items() if slug(new) in present}
    if unknown := sorted(set(renames) - present - done):
        sys.exit(f"--team names not in CODEOWNERS: {', '.join(unknown)}")

    def sub(m):
        return team_name(m.group(1), m.group(2), org, renames)

    return "".join(
        line if line.lstrip().startswith("#") else TEAM.sub(sub, line)
        for line in lines
    )


def parse_renames(values):
    renames = {}
    for value in values:
        old, sep, new = value.partition("=")
        if not (sep and old and new):
            sys.exit(f"--team wants OLD=NEW, got {value}")
        renames[old] = new
    return renames


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--org", required=True, help="GitHub organisation that owns the teams")
    ap.add_argument("--team", action="append", default=[], metavar="OLD=NEW",
                    help="rename a CODEOWNERS team, for example detection-engineering=csirt; repeatable")
    args = ap.parse_args()

    text = CODEOWNERS.read_text()
    new = rewrite_codeowners(text, args.org, parse_renames(args.team))
    if new == text:
        print("CODEOWNERS unchanged")
    else:
        CODEOWNERS.write_text(new)
        print("CODEOWNERS updated, commit it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
