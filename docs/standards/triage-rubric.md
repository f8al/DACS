# Triage rubric

Phase 2 of the lifecycle. Requests are scored the same way every time so that
prioritization is defensible and requesters can predict where their ask lands.

## Formula

```
priority = (threat_severity * 3) + (environmental_relevance * 3)
         + (coverage_gap * 2) + (active_exploitation * 2)
```

Each input is scored 1 to 4 from the intake form. Range is 10 to 40, normalized
to 0 to 100 for the rule metadata field.

| Input | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Threat severity | Nuisance | Moderate impact | Significant impact | Severe, material |
| Environmental relevance | Edge case platform | Some assets | Broad footprint | Crown jewel systems |
| Coverage gap | Solid coverage exists | Partial or brittle | Adjacent detection only | No coverage |
| Active exploitation | Theoretical | Reported in the wild | Active in our sector | Observed against us |

## Bands

| Normalized score | Band | Commitment |
|---|---|---|
| 80 to 100 | P1 | In development within 5 business days |
| 60 to 79 | P2 | In development within the current sprint |
| 40 to 59 | P3 | Backlog, reviewed monthly |
| below 40 | P4 | Backlog, reviewed quarterly, candidate to close |

## Override

A named leader may override the band, in a comment on the work item, with a reason.
Overrides are counted in the monthly report. An override rate above roughly one
in five means the rubric weights are wrong and should be revisited rather than
routed around.

## What triage is not

Triage does not decide whether the detection is feasible. That is phase 3,
Investigate, where the data source question is answered. A P1 with no viable
data source becomes a telemetry gap ticket for the platform team, which is a
legitimate and valuable output of this process.
