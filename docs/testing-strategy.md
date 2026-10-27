# Testing strategy

Five tiers, each with a different cost and a different question it answers.
A rule must pass every tier below the one it claims.

| Tier | Question it answers | Tool | Runs | Cost |
|---|---|---|---|---|
| 1. Schema and lint | Is the rule well formed and documented | tools/validate_rules.py | Every PR | Seconds |
| 2. Compile | Does it translate to our query language | sigma convert | Every PR | Seconds |
| 3. Fixture replay | Does the logic match known bad and ignore known good | pytest, tests/data | Every PR | Seconds |
| 4. Detonation | Does the real technique produce the real telemetry | flightsim, Atomic Red Team, Stratus Red Team | Nightly | Minutes |
| 5. End to end assertion | Did the alert actually appear in the SIEM | Threatest | Nightly | Minutes to hours |
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
| `threatest` | Every active scenario in the rule's `scenario_file`, detonated and then asserted against the SIEM | 5 | Yes, automatically on a pass |
| `flightsim` | The rule's `detonation_command` on the detonation host, with no assertion | 4 | No |

Threatest is the default and the only path to an automatic stamp. Its
detonator is chosen per scenario:

- `remoteDetonator` runs commands on the detonation host over SSH: flightsim
  modules (`scenarios/network.threatest.yaml`) and Atomic Red Team tests
  through PowerShell (`scenarios/endpoint.threatest.yaml`).
- `stratusRedTeamDetonator` runs a Stratus Red Team technique against a cloud
  sandbox account from the runner (`scenarios/cloud.threatest.yaml`).

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
5. Every scheduled run is announced to the SOC with the detonation host and the
   Threatest detonation UUID in the parent process, so a
   detonation is never mistaken for an incident. Unannounced detonation is a
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

Threatest assigns a UUID to each detonation and binds the matched alert to it,
which is what keeps assertions from passing on unrelated alerts of the same name.
flightsim does not do this. When flightsim is used as the detonator, the
assertion binds on signal name plus time window plus source address, so the
detonation host must not share its address with anything else that could trip
the same rule. The nightly pipeline runs flightsim on the detonation host only, either
through the Threatest remote detonator, which executes it under a parent
process containing the detonation UUID, or for flightsim-only rules over SSH
after Threatest has finished, so the two never share a window. Endpoint telemetry on that host can
correlate against the UUID; resolver and network logs cannot, which is why the
address rule above still applies.
