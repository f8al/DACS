# Runbook: <alert name>

Alert name as it appears in the console: <exact string>
Rule id: <uuid>
Severity: <level>    Response action: <page | ticket | hunt_only | enrich_only>
Owner: <team>        Last reviewed: <YYYY-MM-DD>

## What fired and why it matters

Two sentences. What the detection saw and what it would mean if true.

## Triage in order

1. <first thing to check, with the exact query or console path>
2. <second>
3. <third>

Stop as soon as one of the close conditions below is met.

## Close as benign when

- <specific, checkable condition>
- <specific, checkable condition>

If you close this alert as benign for a reason not listed here, open a tuning work
item so the allow list and this runbook both get updated.

## Escalate when

- <specific condition>

Escalate to: <team or rotation>. Include: <the minimum evidence package>.

## Containment options

Listed in order of increasing disruption, with who authorizes each.

## Known false positives

Point at the ADS section rather than duplicating it.

## If this alert is noisy

Open a tuning work item with the alert count for the last seven days. Do not
disable the rule in the console. Console changes are overwritten by the next
deployment and leave no audit trail.
