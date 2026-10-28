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
- UUID scenarios: the field that carries the detonation UUID, for example
  `userAgent,observable,user-agent,` for Stratus and
  `ParentCommandLine,observable,other,` for endpoint rules.

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

Threatest closes every alert it matched with status Other and the tag Control
Validation. Exclude that tag from TheHive notifications, Functions and Cortex
responders, so a detonation never pages anyone or triggers an automated
response.
