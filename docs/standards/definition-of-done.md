# Definition of done

A detection is done when all of the following are true. This list is mirrored in
the pull request template and enforced by CI wherever enforcement is possible.

## Machine enforced (CI fails without these)

1. The rule validates against schema/detection.schema.json.
2. The rule id is a UUID and is unique across the repository.
3. ATT&CK tags are well formed and include the subtechnique where one applies.
4. The ADS file referenced in operations.ads exists.
5. The runbook file referenced in operations.runbook exists.
6. The scenario file or detonation command referenced in validation exists.
7. The rule compiles for every configured backend.
8. Positive and negative fixtures exist and the thresholds agree with them.
9. A rule at lifecycle stage production has a validation method other than none
   and a non null last_validated date.

## Human enforced (reviewer fails the PR without these)

10. Blind Spots and Assumptions names at least one concrete evasion. "None
    known" is not acceptable for a behavioral detection.
11. The false positives list describes real observed sources, not hypotheticals.
12. logsource.definition states the collection requirements and their caveats.
13. The runbook has a close as benign path and an escalate path with named
    owners.
14. The volume budget is grounded in staging soak data or an explicit estimate
    with its reasoning.
15. The response action matches the severity. Nothing is set to page without a
    runbook that justifies waking a human.

## Promotion gate

A rule may only move to lifecycle stage production after the nightly detonation
job has passed for it at least once and last_validated is stamped. Merging to
main is not deployment. Deployment is a tagged release through an environment
with an approval check.
