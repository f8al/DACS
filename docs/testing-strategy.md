# Testing strategy

Five tiers, each with a different cost and a different question it answers.
A rule must pass every tier below the one it claims.

| Tier | Question it answers | Tool | Runs | Cost |
|---|---|---|---|---|
| 1. Schema and lint | Is the rule well formed and documented | tools/validate_rules.py | Every PR | Seconds |
| 2. Compile | Does it translate to our query language | sigma convert | Every PR | Seconds |
| 3. Fixture replay | Does the logic match known bad and ignore known good | pytest, tests/data | Every PR | Seconds |
| 4. Detonation | Does the real technique produce the real telemetry | flightsim, Atomic Red Team, Stratus Red Team | Nightly | Minutes |
| 5. End to end assertion | Did the alert actually appear in TheHive | Threatest | Nightly | Minutes to hours |
| 6. Adversarial | Does it survive an operator who is trying to evade it | Purple team exercise | Quarterly | Days |

## What each tier does not prove

- Tier 1 to 3 prove form and logic. They prove nothing about telemetry. A rule
  can pass all three while the log source has been dark for a month.
- Tier 4 proves telemetry arrives. It does not prove the rule fired.
- Tier 5 proves the alert fired for the canonical procedure. It says nothing
  about precision and nothing about the variants the rule misses.
- Only tier 6 tests the rule against an adversary who knows it exists. Record the
  results in the Blind Spots section of the ADS, which is the artifact that
  carries this knowledge forward.

## Choosing a validation method

The nightly job runs two kinds of detonation. A rule picks one with
`validation.method`.

| Method | What runs | Tier reached | Stamps last_validated |
|---|---|---|---|
| `threatest` | Every active scenario in the rule's `scenario_file`, detonated and then asserted against TheHive | 5 | Yes, automatically on a pass |
| `flightsim` | The rule's `detonation_command` on the detonation host, with no assertion | 4 | No |

Threatest is the default and the only path to an automatic stamp. Its
detonator is chosen per scenario:

- `remoteDetonator` runs commands on the detonation host over SSH: flightsim
  modules (`scenarios/network.threatest.yaml`) and Atomic Red Team tests
  through PowerShell (`scenarios/endpoint.threatest.yaml`).
- `stratusRedTeamDetonator` runs a Stratus Red Team technique against a cloud
  sandbox account from the runner (`scenarios/cloud.threatest.yaml`).

A scenario asserts with `theHiveAlert`: the TheHive alert whose `title` is the
rule title, bound to the detonation by one of the two correlation modes below.
It can add a `splunkLog` expectation, which proves the telemetry reached
Splunk and so separates a missing log source from a broken rule; it names no
rule and never stamps one. On cleanup Threatest sets each matched alert to
status Other with the tag Control Validation.

Use `flightsim` alone for a rule whose alert cannot be queried by a Threatest
matcher yet, or while a scenario is being written. It proves the traffic leaves
the host and that a failure is not a broken detonation path, and nothing more.
Its rule reaches `last_validated` only when an analyst confirms the alert from
that night's run and stamps it by hand in a pull request, citing the run as
evidence. Move it to a Threatest scenario as soon as one is possible.

`atomic_red_team`, `stratus_red_team` and `manual` mean the detonation is run
by hand outside the nightly job. A rule whose Atomic or Stratus detonation runs
through a Threatest scenario uses `threatest`.

The validator enforces the wiring: a `threatest` rule must be asserted by name
in its scenario file, every active scenario must assert a real rule title, and
a flightsim command, in a rule or a scenario, must name its modules and none of
the modules excluded below.

## Detonation safety rules

1. Detonation runs from a dedicated host with a dedicated egress address. Never
   from a shared workstation and never from a clinical, OT or production segment
   without written approval and a change window.
2. flightsim contacts live command and control infrastructure to build its
   destination list. Your egress address will appear in third party telemetry
   reaching out to known bad destinations. Get that acknowledged in advance by
   whoever owns the address space.
3. The scan and spambot modules are excluded from scheduled runs. scan can trip
   IPS blocking and lock out the detonation host, spambot can get the egress
   range listed. ssh-exfil and ssh-transfer are excluded too, because they move
   enough data to trip bandwidth and DLP controls. The validator rejects all
   four in rules and scenarios.
4. tunnel-icmp requires superuser privileges on the detonation host.
5. Every scheduled run is announced to the SOC with the detonation host and
   its time window, so a detonation is never mistaken for an incident. Where
   Threatest runs the detonation, the UUID is also in the parent process name
   on the detonation host. TheHive alerts a run matched are closed as Other
   with the tag Control Validation. Unannounced detonation is a
   purple team exercise, which is a different activity with a different approval.

## Blocked is not the same as undetected

If a detonation produces no alert, determine which of these happened before
touching the rule:

1. A control blocked the traffic and logged it. That is a pass for the control
   and a pass for visibility.
2. A control blocked the traffic and did not log it. That is a visibility gap.
   Open a telemetry ticket, not a tuning ticket.
3. The traffic went out, was logged, and no rule matched. That is a detection
   gap. Tune the rule.
4. The traffic went out and was not logged. That is a collection gap. Escalate to
   the platform team.

Reporting all four cases as "detection failed" is the fastest way to lose
credibility with the platform and network teams.

## Correlation

`theHiveAlert` binds an alert to the detonation in one of two ways, set per
expectation with `correlation`. Without one, an assertion could pass on an
unrelated alert of the same name.

**`uuid`, the default.** Threatest assigns a UUID to each detonation, and the
matcher accepts only an alert whose observables or description contain it.
The UUID has to reach the alert through the telemetry:

- Stratus Red Team puts it in the user agent of every API call, so it lands in
  the CloudTrail event.
- The remote detonator runs its commands under a parent process named after it
  (/tmp/<uuid>), so an endpoint rule that returns the parent process carries it.

**`host`, for network rules.** Resolver, proxy and flow logs never see a
process name, so flightsim traffic cannot carry the UUID. These scenarios bind
instead on the alert title, the alert being created after the run started,
and an observable exactly equal to one of the detonation host's addresses
(`DETONATION_HOST_ADDRESSES`, passed to Threatest as
`THEHIVE_DETONATION_HOSTS`).

Host correlation is weaker. Anything else that trips the same rule from the
same address while the scenario waits passes the assertion: another test, a
scheduled job, or real malware on the host. Three things keep it honest:

1. The detonation host is dedicated, and none of its addresses is shared with
   anything that could trip the same rule. A NAT address shared with other
   hosts defeats it.
2. The nightly pipeline runs flightsim-only rules over SSH only after
   Threatest has finished, so a flightsim-only detonation never falls inside a
   Threatest scenario's window.
3. Every observable the scenario names, `src_ip` for network rules, is mapped
   in TA-thehive-cortex, so the address is an exact observable rather than text
   that happens to match. See `docs/standards/thehive-alert-action.md`.

Endpoint telemetry on the detonation host still carries the UUID, so an
analyst can tie a network alert back to its run through the querying process.
