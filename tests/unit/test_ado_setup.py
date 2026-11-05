"""reviewers.yml rewriting in ado_setup."""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import ado_setup  # noqa: E402

TEXT = """# Owners, later entries win.
- path: /*
  groups: ["[your-project]\\\\detection-engineering"]
- path: /detections/*
  groups: ["[your-project]\\\\detection-engineering", "[your-project]\\\\soc-leads"]
- path: /vendor/*
  groups: ["[Other]\\\\vendor-team"]
"""


def groups(text):
    return [entry["groups"] for entry in yaml.safe_load(text)]


def test_placeholder_project_is_replaced_and_comments_kept():
    out = ado_setup.rewrite_reviewers(TEXT, "Sec", {})
    assert out.startswith("# Owners, later entries win.\n")
    assert groups(out) == [
        ["[Sec]\\detection-engineering"],
        ["[Sec]\\detection-engineering", "[Sec]\\soc-leads"],
        ["[Other]\\vendor-team"],
    ]


def test_renames_take_the_project_unless_given_one():
    out = ado_setup.rewrite_reviewers(TEXT, "Sec", {
        "detection-engineering": "CSIRT",
        "soc-leads": "[Shared]\\SOC Leads",
    })
    assert groups(out)[1] == ["[Sec]\\CSIRT", "[Shared]\\SOC Leads"]


def test_rerun_with_the_same_flags_changes_nothing():
    renames = {"detection-engineering": "CSIRT"}
    once = ado_setup.rewrite_reviewers(TEXT, "Sec", renames)
    assert ado_setup.rewrite_reviewers(once, "Sec", renames) == once


def test_unknown_group_is_refused():
    with pytest.raises(SystemExit, match="typo"):
        ado_setup.rewrite_reviewers(TEXT, "Sec", {"typo": "X"})


def test_bad_group_flag_is_refused():
    with pytest.raises(SystemExit, match="OLD=NEW"):
        ado_setup.parse_renames(["detection-engineering"])
