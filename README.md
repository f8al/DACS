# Detection as Code Scaffold

A reusable, platform neutral scaffold for running a detection engineering
program on GitHub. It implements the six phase detection engineering lifecycle
(Requirements Discovery, Triage, Investigate, Develop, Test, Deploy), uses the
Palantir ADS framework as the documentation artifact, and closes the loop with
automated detonation testing via AlphaSOC flightsim and Datadog Threatest.

The design goal is repeatability: every phase produces an artifact, every
artifact is checked by CI, and nothing reaches production on trust.

## Lifecycle to artifact mapping

| Phase | GitHub mechanism | Artifact |
|---|---|---|
| 1. Requirements Discovery | Issue form, `.github/ISSUE_TEMPLATE/detection-request.yml` | Intake issue with required fields |
| 2. Triage | Rubric applied on the issue, label and milestone | `priority_score` in rule metadata |
| 3. Investigate | Issue discussion, data source check | `logsource.definition`, ADS sections 3 and 4 |
| 4. Develop | Branch and pull request | Rule YAML plus ADS plus runbook |
| 5. Test | `validate` and `detonate-nightly` workflows | Fixtures, Threatest scenario, `last_validated` stamp |
| 6. Deploy | `deploy` workflow, tagged release, protected environment | Release notes, SOC notification |
| Ongoing | `hygiene` workflow | Staleness report, metrics, Navigator layer |

## Repository layout

```
detections/<platform>/          Sigma rules plus the detection_engineering block
schema/detection.schema.json    The contract. Everything is enforced here.
docs/ads/                       One ADS per detection, nine sections, all required
docs/runbooks/                  What the analyst does when it fires
docs/standards/                 Detection standard, triage rubric, definition of done, deprecation policy
docs/testing-strategy.md        The six testing tiers and detonation safety rules
scenarios/*.threatest.yaml      End to end assertions: flightsim and Atomic on the detonation host, Stratus in the cloud
tests/unit, tests/data          Fixture replay, one positive and one negative per rule
lookups/                        Allow lists and other reference data the platform applies at deploy time
tools/                          Validation, coverage metrics, validation stamping, flightsim detonation, deployment
.github/workflows/              validate, detonate-nightly, deploy, hygiene
```

## Quick start

```
pip install -r tools/requirements.txt
python tools/validate_rules.py      # gate 1 and 2
pytest tests/unit -q                # gate 3
python tools/coverage_report.py     # metrics plus ATT&CK Navigator layer
```

## What you must change to adopt this

1. `.github/CODEOWNERS`: replace the placeholder teams.
2. `.github/workflows/validate.yml`: set the `backend` matrix to your platform.
3. `tools/deploy.py`: implement `push()` for your SIEM. This is the only file
   that cannot be platform neutral and it is deliberately isolated.
4. `scenarios/*.threatest.yaml`: the alert matcher keys shown are for Datadog.
   Threatest ships matchers for Datadog and Elastic. For any other platform,
   implement a matcher against the Go interface: authenticate, poll the alert
   API, filter on name plus time window plus correlation id, return a boolean.
   Each rule validates through a Threatest scenario or through flightsim alone;
   `docs/testing-strategy.md` explains the choice and what each one proves.
5. Repository settings: branch protection on `main` requiring the `validate`
   checks and two approving reviews, plus protected environments
   `detonation-lab`, `siem-staging` and `siem-production` with required
   reviewers.
6. A self hosted runner labelled `detonation-lab`, sitting inside the network
   whose telemetry you are testing. A hosted GitHub runner is not inside your
   monitored network, so detonation from one proves nothing. The runner needs
   `threatest` and Python 3 with PyYAML on PATH and SSH access to
   `DETONATION_HOST`; the detonation host needs flightsim, plus PowerShell 7 and
   Invoke-AtomicRedTeam for Atomic scenarios. Stratus scenarios use the
   runner's own cloud credentials, so scope them to a sandbox account.
   Detonation is off by default. Once the runner is in place and the
   `detonation-lab` environment has required reviewers, opt in with
   `gh variable set DETONATION_ENABLED --body true`. Until then the nightly
   workflow is skipped on schedule and on manual dispatch.
7. Validation stamping: the nightly job records passing detonations by opening a
   pull request that updates `last_validated`. Enable Settings, Actions,
   "Allow GitHub Actions to create and approve pull requests", and add a
   `STAMP_PR_TOKEN` secret (a GitHub App token or a fine grained token with
   contents and pull requests write). Without the token the pull request still
   opens, but GitHub does not run `validate` on it, so its required checks never
   report.

## Design decisions worth defending

**Metadata lives on the rule, not in a wiki.** A separate documentation system
drifts because nothing forces it to change when the logic does. The ADS path is
a required field and CI fails if the file is missing.

**Lifecycle stage drives deployment, not branch state.** Merging to `main` is
not shipping. A rule at `in_test` can sit in `main` indefinitely without ever
reaching the production SIEM.

**Coverage is scored by validation freshness, not by rule existence.** The
Navigator layer gives 100 only to production rules with a detonation test that
passed in the last 30 days. A green cell backed by an unvalidated rule is a
hypothesis wearing a measurement costume.

**Deprecation is a first class path.** See `docs/standards/deprecation-policy.md`.
Quiet plus a passing detonation means the control works, not that the rule is
useless.

## References

- Practical Threat Detection Engineering, Roddie, Deyalsingh, Katz (Packt, 2023), chapter 2
- Palantir Alerting and Detection Strategy framework: github.com/palantir/alerting-detection-strategy-framework
- Elastic Detection Engineering Behavior Maturity Model: elastic.co/security-labs/elastic-releases-debmm
- Elastic detection-rules: github.com/elastic/detection-rules
- AlphaSOC flightsim: github.com/alphasoc/flightsim
- Datadog Threatest: github.com/DataDog/threatest
