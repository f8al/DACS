## What this changes

Work item: #

## Definition of done

Every box must be checked or the reviewer will close this. See docs/standards/definition-of-done.md.

### Content
- [ ] Rule validates against `schema/detection.schema.json` (CI proves this)
- [ ] `detection_engineering.requirement.work_item` points at the intake work item, and that work item is linked to this pull request
- [ ] ATT&CK tags are correct at the subtechnique level where one applies
- [ ] `logsource.definition` states exactly what telemetry is required, including collection caveats
- [ ] False positives list is real and specific, not "may generate noise"

### Documentation
- [ ] ADS exists at `docs/ads/<name>.md` with all nine sections filled
- [ ] Blind Spots and Assumptions names at least one concrete way this detection can be evaded
- [ ] Runbook exists at `docs/runbooks/<name>.md` with a triage decision path and escalation criteria

### Validation
- [ ] Unit fixtures exist under `tests/data/` with both a positive and a negative case
- [ ] A detonation path exists: a Threatest scenario, a flightsim command, an Atomic test or a documented manual procedure
- [ ] For promotion to `stage: production`, the nightly detonation job has passed at least once and `last_validated` is set

### Operations
- [ ] `volume_budget_per_week` is a considered number, based on staging soak data where available
- [ ] `response_action` matches the severity. Nothing pages without a runbook that justifies waking someone.

## Expected alert volume

Observed in staging soak:

## Reviewer notes

What should the second reviewer look at hardest.
