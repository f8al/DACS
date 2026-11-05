"""CODEOWNERS rewriting in github_setup."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import github_setup  # noqa: E402

TEXT = """# Replace your-org with your organisation, @your-org/example stays put here.
*              @your-org/detection-engineering
/detections/   @your-org/detection-engineering @your-org/soc-leads
/vendor/       @other/vendor-team @someone
"""


def test_placeholder_org_is_replaced_and_comments_kept():
    out = github_setup.rewrite_codeowners(TEXT, "acme", {})
    assert out.splitlines() == [
        "# Replace your-org with your organisation, @your-org/example stays put here.",
        "*              @acme/detection-engineering",
        "/detections/   @acme/detection-engineering @acme/soc-leads",
        "/vendor/       @other/vendor-team @someone",
    ]


def test_renames_take_the_org_unless_given_one():
    out = github_setup.rewrite_codeowners(TEXT, "acme", {
        "detection-engineering": "csirt",
        "soc-leads": "shared/soc",
    })
    assert out.splitlines()[2] == "/detections/   @acme/csirt @shared/soc"


def test_rerun_with_the_same_flags_changes_nothing():
    renames = {"detection-engineering": "csirt"}
    once = github_setup.rewrite_codeowners(TEXT, "acme", renames)
    assert github_setup.rewrite_codeowners(once, "acme", renames) == once


def test_unknown_team_is_refused():
    with pytest.raises(SystemExit, match="typo"):
        github_setup.rewrite_codeowners(TEXT, "acme", {"typo": "x"})


def test_bad_team_flag_is_refused():
    with pytest.raises(SystemExit, match="OLD=NEW"):
        github_setup.parse_renames(["detection-engineering"])
