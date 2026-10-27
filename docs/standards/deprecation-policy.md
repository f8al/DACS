# Deprecation policy

A detection program without a deletion path only accumulates. Removal is a
normal, expected outcome, not a failure.

## Deprecation triggers

A rule enters the deprecation review queue when any of these is true:

- Precision has stayed below 10 percent true positives for two consecutive
  monthly reviews, after a genuine tuning attempt.
- The rule has not fired in 12 months and its detonation test also does not fire,
  meaning it is broken rather than quiet.
- The data source it depends on has been decommissioned or has changed schema in
  a way the rule cannot follow.
- The technique is no longer relevant: the software is retired, the platform is
  gone, or the vulnerability is remediated fleet wide.
- It has been superseded by a better detection that covers the same behavior with
  higher fidelity.

## Quiet is not the same as broken

A rule that has never fired and whose detonation test passes is working
correctly. Silence plus a passing detonation is evidence of a working control,
not evidence of a useless rule. Never deprecate on alert count alone.

## Process

1. Open a tuning work item with the deprecation proposal and the supporting numbers.
2. The rule owner and one SOC lead review. Disagreement escalates to the DE lead.
3. On approval, set lifecycle stage to deprecated with a deprecation_reason, and
   set the Sigma status field to deprecated. The next deployment removes it from
   the SIEM.
4. The file stays in the repository. Git history is the record of what was tried
   and why it was retired. Do not delete the file, do not delete the ADS.

## Resurrection

A deprecated rule can be brought back by reversing the stage field, but it must
pass the full definition of done again, including a fresh detonation.
