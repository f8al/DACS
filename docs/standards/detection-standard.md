# Detection standard

## Source of truth

Rules are authored as Sigma with a required detection_engineering block carrying
the program metadata. The YAML file in this repository is authoritative. Rules
edited directly in the SIEM console are overwritten by the next deployment and
leave no audit trail. If you need an emergency change in the console, open a PR
the same day.

## Where Sigma stops

Author in Sigma where it fits. Author natively where it does not. Correlation
across events, statistical baselining and platform specific joins frequently do
not survive translation, and forcing them through the abstraction produces a rule
that compiles and does not work. A natively authored rule carries the same
detection_engineering block, the same ADS and the same tests. Only the logic
format differs.

## Naming

The rule title is the alert name the analyst sees. It becomes a foreign key in
dashboards, tickets and Threatest assertions, so it is expensive to change.

- Describe the behavior and the evidence, not the tool: "DNS Tunneling via High
  Volume Unique Subdomains", not "Suspicious DNS" and not "Iodine Detection".
- Title case, 10 to 120 characters, no vendor product names, no internal jargon.
- Changing a title requires updating every Threatest scenario that asserts it
  (the `title:` key of `theHiveAlert`) and the Splunk saved search, whose name
  TheHive uses as the alert title. The validator fails the build when a
  scenario asserts a title no rule has.

## File layout

```
detections/<platform>/<snake_case_behavior>.yml
docs/ads/<kebab-case-name>.md
docs/runbooks/<kebab-case-name>.md
tests/data/<snake_case_behavior>.true_positive.json
tests/data/<snake_case_behavior>.true_negative.json
```

Platform is one of network, windows, linux, cloud.

## Severity

| Level | Meaning | Default response action |
|---|---|---|
| critical | Confirmed compromise pattern, act now | page |
| high | Strong indicator, same day investigation | ticket |
| medium | Suspicious, investigate within the week | ticket |
| low | Weak signal, useful in aggregate | enrich_only |
| informational | Context for other detections or hunts | hunt_only |

## Lifecycle stages

proposed, in_development, in_test, production, deprecated. The stage field drives
deployment. Only production stage rules reach the production SIEM.

## Review intervals

| Severity | Interval |
|---|---|
| critical, high | 90 days |
| medium | 180 days |
| low, informational | 365 days |

Review means: confirm the data source still exists, confirm the detonation still
passes, check volume and precision, update blind spots against current tradecraft.

## Dates

Quote every date in YAML: `date: "2026-09-30"`. Unquoted, YAML parses it into a
native date object, which fails the schema string pattern and breaks staleness
math. CI catches this, but quoting saves you the round trip.
