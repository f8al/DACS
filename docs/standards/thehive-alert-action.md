# TheHive alert action

Threatest's `theHiveAlert` matcher can only find what TA-thehive-cortex 3.2.1
puts into TheHive. Configure the Splunk alert action of every saved search a
scenario asserts as follows, or the nightly assertions fail for reasons that
have nothing to do with the rule.

## Observables

Every field a scenario matches on must be mapped in `thehive_datatypes.csv`,
or it never becomes an observable and the assertion cannot match.

- Network rules, `correlation: host`: the source address field, for example
  `src_ip,observable,ip,`. The scenario's `observableField` names the same
  field.
- Endpoint rules detonated with Atomic tests, `correlation: host`: the host
  name field, for example `host,observable,hostname,`. The detonation UUID
  does not reach the technique's process, see docs/testing-strategy.md,
  Correlation.
- UUID scenarios: the field that carries the detonation UUID, for example
  `userAgent,observable,user-agent,` for Stratus. For an endpoint rule, only
  when the detected process is a direct child of the detonation (its
  `ParentCommandLine` holds `/tmp/<uuid>`) or the telemetry carries process
  ancestry.

Map each field by name. The "All fields" scope is broken in 3.2.

## Unique ID field

Leave it empty. TheHive treats an alert with the same type, source and
sourceRef as a duplicate, so a stable value makes it reject the next night's
alert and the assertion fails.

## Title

Set the title to `<inheritance>`, so the alert title is the saved search name,
which is the rule title. Renaming a rule means renaming its saved search and
the `title:` of every `theHiveAlert` that asserts it.

## Test runs

After each scenario, Threatest sets status Other and adds the tag Control
Validation to every open alert it binds to the run:

- `correlation: uuid`: every alert from the past hour whose observables or
  description contain the run's UUID, whatever its title.
- `correlation: host`: only alerts with the scenario's title and an
  observable equal to a detonation host address.

It changes nothing if Other is missing or not a Closed-stage alert status,
and discovery expectations never clean up. Exclude the tag from TheHive
notifications, Functions and Cortex responders, so a detonation never pages
anyone or triggers an automated response.
