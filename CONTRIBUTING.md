# Contributing

## The path a detection takes

1. Create a work item from the Detection request template in Azure Boards.
   This is the only front door. Requests that arrive by chat get pointed back
   here.
2. Triage applies the rubric in `docs/standards/triage-rubric.md` and assigns a
   band. Triage runs weekly.
3. Investigate: confirm the data source exists and carries the evidence. If it
   does not, this becomes a telemetry gap ticket for the platform team, which is
   a legitimate outcome.
4. Branch as `detection/<work-item-id>-<short-name>`.
5. Write the rule, the ADS and the runbook in one commit set. They review
   together or not at all.
6. Open a pull request and link the intake work item to it. Work through the
   definition of done checklist honestly. CI checks what it can; the reviewer
   checks the rest.
7. Two approvals for anything at `high` or `critical`, one otherwise. See
   `.azuredevops/reviewers.yml` for who must be among them.
8. Merge sets the rule at `in_test`. The nightly detonation pipeline runs it.
9. Once detonation passes and `last_validated` is stamped, a follow up PR
   promotes the rule to `stage: production`.
10. A tagged release deploys production stage rules through the approval
    gated environments.

## Rules for reviewers

- Reject "may generate noise" as a false positive entry. Name the source.
- Reject an empty Blind Spots section. Every behavioral detection has an evasion.
  If the author cannot name one, they do not understand the technique yet.
- Check the alert title against every Threatest scenario that asserts it. CI does
  not catch a renamed title breaking an assertion.
- Ask what the expected weekly volume is and where the number came from.
- Ask who gets paged and whether the runbook justifies it.

## Emergency changes

If a rule must be changed in the console to stop an incident or stop a flood,
do it, then open a PR the same day with the console change reflected. Console
state is overwritten by the next deployment, so an unreflected emergency change
silently reverts.
