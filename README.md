# Detection as Code Scaffold

A reusable, platform neutral scaffold for running a detection engineering
program on Azure DevOps. It implements the six phase detection engineering
lifecycle (Requirements Discovery, Triage, Investigate, Develop, Test, Deploy),
uses the Palantir ADS framework as the documentation artifact, and closes the
loop with automated detonation testing via AlphaSOC flightsim and Datadog
Threatest.

The design goal is repeatability: every phase produces an artifact, every
artifact is checked by CI, and nothing reaches production on trust.

## Lifecycle to artifact mapping

| Phase | Azure DevOps mechanism | Artifact |
|---|---|---|
| 1. Requirements Discovery | Boards work item template, `.azuredevops/work-item-templates/detection-request.yml` | Intake work item with every section answered |
| 2. Triage | Rubric applied on the work item, tags and iteration | `priority_score` in rule metadata |
| 3. Investigate | Work item discussion, data source check | `logsource.definition`, ADS sections 3 and 4 |
| 4. Develop | Branch and pull request | Rule YAML plus ADS plus runbook |
| 5. Test | `validate` and `detonate-nightly` pipelines | Fixtures, Threatest scenario, `last_validated` stamp |
| 6. Deploy | `deploy` pipeline, tagged release, environments with approvals | Release notes, SOC notification |
| Ongoing | `hygiene` pipeline | Staleness report, metrics, Navigator layer |

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
tools/                          Validation, coverage metrics, validation stamping, flightsim detonation,
                                deployment,
                                Azure DevOps setup (ado_setup.py) and pipeline glue (ado.py)
.azuredevops/pipelines/         validate, detonate-nightly, deploy, hygiene
.azuredevops/reviewers.yml      Path based required reviewers, the CODEOWNERS equivalent
.azuredevops/work-item-templates/  Detection request and tuning intake templates
.azuredevops/pull_request_template.md  Definition of done checklist
```

## Quick start

```
pip install -r tools/requirements.txt
python tools/validate_rules.py      # gate 1 and 2
pytest tests/unit -q                # gate 3
python tools/coverage_report.py     # metrics plus ATT&CK Navigator layer
```

## What you must change to adopt this

1. `.azuredevops/reviewers.yml`: replace the placeholder project and groups.
2. `.azuredevops/pipelines/validate.yml`: set the `backend` matrix to your platform.
3. `tools/deploy.py`: implement `push()` for your SIEM. This is the only file
   that cannot be platform neutral and it is deliberately isolated.
4. `scenarios/*.threatest.yaml`: the alert matcher keys shown are for Datadog.
   Threatest ships matchers for Datadog and Elastic. For any other platform,
   implement a matcher against the Go interface: authenticate, poll the alert
   API, filter on name plus time window plus correlation id, return a boolean.
   Each rule validates through a Threatest scenario or through flightsim alone;
   `docs/testing-strategy.md` explains the choice and what each one proves.
5. Run the setup once, with a personal access token in `AZURE_DEVOPS_EXT_PAT`
   (scopes listed in the script):
   `python tools/ado_setup.py --org https://dev.azure.com/your-org --project your-project --repo your-repo`.
   It registers the `validate`, `deploy` and `hygiene` pipelines, puts a two
   approval minimum (votes reset on push, the last pusher cannot approve), a
   blocking `validate` build, a work item linking reminder
   and the reviewers from step 1 on the default branch, and uploads the work
   item templates to the project's default team (`--team` for another).
   Azure Boards templates cannot make a field required, so "incomplete
   requests are not triaged" is enforced by the triager, not the form.
6. Work item type: the pipelines file tuning and hygiene work items as `Issue`
   and close them as `Done`, which suits the Basic process. For Agile or CMMI
   set the pipeline variable `WORK_ITEM_CLOSED_STATE` to `Closed`; for Scrum
   also set `WORK_ITEM_TYPE` to `Impediment`. Set `AREA_PATH` to file them
   somewhere other than the project root. Set the same `WORK_ITEM_TYPE` when
   running the setup so the templates match.
7. Build service permissions: the pipelines act as
   `<project> Build Service (<org>)`. On the area path grant it Edit work items
   in this node. On the repository grant it Contribute, Create branch,
   Contribute to pull requests, and Force push on the
   `automation/stamp-last-validated` branch.
8. Environments: in Pipelines, Environments, create `siem-staging`,
   `siem-production` and `detonation-lab` and add an Approvals check to each.
   Azure DevOps creates a missing environment on first use with no checks, so
   do this before the first tag. Create the variable groups `siem-staging`
   (`SIEM_URL`, secret `SIEM_TOKEN`) and `siem-production` (the same plus
   secret `SOC_WEBHOOK`), and authorize the `deploy` pipeline to use them.
   The `deploy` pipeline runs the YAML from the tagged commit, so anyone who
   can push a `v*` tag can rewrite it to skip the environments. Two settings
   close that, because the YAML cannot remove them. In Repos, Security, deny
   Create tag to Contributors on this repository and allow it only to the
   release owners. In Library, add an Approvals check to both variable groups,
   and have the approver confirm the run's commit is on `main`. A Branch
   control check allowing only `refs/tags/v*` on the groups is worth adding
   too, but it cannot tell whether the tag points at a commit on `main`.
9. A self hosted agent pool named `detonation-lab`, with an agent sitting
   inside the network whose telemetry you are testing. A Microsoft hosted agent
   is not inside your monitored network, so detonation from one proves nothing.
   The agent needs git, curl, and Python 3 with PyYAML on PATH and SSH
   access to `DETONATION_HOST`. The job installs the pinned
   [f8al/threatest](https://github.com/f8al/threatest) fork build itself and
   checks its hash; upstream Threatest cannot parse the Splunk and TheHive
   matcher keys. Network scenarios also need `DETONATION_HOST_ADDRESSES` in the
   `detonation-lab` variable group: every address the detonation host's
   traffic can appear as in an alert, comma-separated. The detonation host needs flightsim, plus
   PowerShell 7 and Invoke-AtomicRedTeam for Atomic scenarios. Stratus
   scenarios use the agent's own cloud credentials, so scope them to a sandbox
   account. Detonation is off by default, twice over. The setup does not register
   `detonate-nightly` unless you pass `--with-detonation`, and the pipeline
   skips its stage unless the pipeline variable `DETONATION_ENABLED` is `true`.
   Do both only once the agent is in place and `detonation-lab` has its
   approval check. Put `DETONATION_HOST`, `DETONATION_USER` and the secrets
   `DD_API_KEY`, `DD_APP_KEY` in a variable group named `detonation-lab`, not
   in pipeline variables: pipeline variables reach a run of any branch, so
   anyone who can queue the pipeline with their own YAML would get the keys
   and a job inside the monitored network. Add a Branch control check allowing
   only `refs/heads/main` to both the `detonation-lab` variable group and the
   `detonation-lab` agent pool, which the YAML cannot remove. Then switch it on:
   `az pipelines variable create --pipeline-name detonate-nightly --name DETONATION_ENABLED --value true`.
10. Validation stamping: the nightly pipeline records passing detonations by
    opening a pull request that updates `last_validated`. A pull request
    opened by the build service triggers the `validate` build policy like any
    other, so no separate token is needed beyond the permissions in step 7.

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
