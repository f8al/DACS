# Contributing

## The path a detection takes

1. Open a detection request issue. This is the only front door. Requests that
   arrive by chat get pointed back here.
2. Triage applies the rubric in `docs/standards/triage-rubric.md` and assigns a
   band. Triage runs weekly.
3. Investigate: confirm the data source exists and carries the evidence. If it
   does not, this becomes a telemetry gap ticket for the platform team, which is
   a legitimate outcome.
4. Branch as `detection/<issue-number>-<short-name>`.
5. Write the rule, the ADS and the runbook in one commit set. They review
   together or not at all.
6. Open a pull request. Work through the definition of done checklist honestly.
   CI checks what it can; the reviewer checks the rest.
7. Two approvals for anything at `high` or `critical`, one otherwise. See
   `.github/CODEOWNERS`.
8. Merge sets the rule at `in_test`. The nightly detonation job runs it.
9. Once detonation passes and `last_validated` is stamped, a follow up PR
   promotes the rule to `stage: production`.
10. A tagged release deploys production stage rules through the protected
    environment.

## Rules for reviewers

- Reject "may generate noise" as a false positive entry. Name the source.
- Reject an empty Blind Spots section. Every behavioral detection has an evasion.
  If the author cannot name one, they do not understand the technique yet.
- Check that a renamed title was renamed in every Threatest scenario too. CI
  fails when a scenario asserts a title no rule has, but not when a scenario
  still asserts the right title for the wrong reason.
- Ask what the expected weekly volume is and where the number came from.
- Ask who gets paged and whether the runbook justifies it.

## Emergency changes

If a rule must be changed in the console to stop an incident or stop a flood,
do it, then open a PR the same day with the console change reflected. Console
state is overwritten by the next deployment, so an unreflected emergency change
silently reverts.
