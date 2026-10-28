# Detonation lab setup

How to stand up the lab the `detonate-nightly` pipeline runs against: a
detonation host, a pipeline agent, Splunk and TheHive configuration, and the
Azure DevOps pieces. README step 9 is the summary; this is the procedure.

Nothing detonates until the last section. The pipeline is not registered
without `--with-detonation`, its stage is skipped until `DETONATION_ENABLED`
is `true`, and its first step stops the run and names any variable missing
from the `detonation-lab` variable group.

## 1. Detonation host

- A dedicated Linux box. None of its addresses, including any NAT address, is
  shared with anything else that could trip a rule: for network rules the
  address is the only thing that binds an alert to a run (see
  `docs/testing-strategy.md`, Correlation).
- It resolves DNS through the resolver whose query logs Splunk collects, with
  the client source address. DNS over HTTPS is off, or the DNS tunneling rule
  has nothing to fire on.
- Outbound DNS to the internet is allowed: flightsim queries real domains.
- flightsim on PATH for the detonation user. PowerShell 7 and
  Invoke-AtomicRedTeam only once an endpoint rule lands.
- A non-root detonation user that can log in over SSH with the agent's key.
  flightsim's tunnel-icmp module needs root and stays out of scheduled runs.
- Write down its hostname and every IP its traffic can appear as in
  `src_ip`. Those become `DETONATION_HOST_ADDRESSES`. The surest way to find
  them is to resolve a unique name from the host
  (`dig dacs-check-<date>.example.com`) and look up that query's `src_ip` in
  Splunk.

## 2. Pipeline agent

- A separate box from the detonation host, inside the monitored network,
  Linux x86_64 (`uname -sm` prints `Linux x86_64`). The pipeline installs the
  x86_64 build of Threatest; another architecture needs the archive name and
  hash changed in `detonate-nightly.yml`.
- The Azure Pipelines agent, registered in a self hosted pool named
  `detonation-lab`.
- On PATH: git, curl, ssh, and python3 with
  `pip install -r tools/requirements.txt`.
- Outbound to the Splunk management port (usually 8089), TheHive, Azure
  DevOps, and `github.com` plus `objects.githubusercontent.com` for the pinned
  Threatest release.
- If Splunk or TheHive uses a private CA, its PEM bundle on the agent.

SSH, as the user the agent runs as. Threatest only reads the key named by the
SSH config's `IdentityFile`, the key must be unencrypted, and it does not use
ssh-agent. Both Threatest and the flightsim step refuse a host whose key is
not in `~/.ssh/known_hosts`.

```
ssh-keygen -t ed25519 -N "" -f ~/.ssh/dacs_detonation
ssh-copy-id -i ~/.ssh/dacs_detonation.pub <user>@<detonation-host>

cat >> ~/.ssh/config <<'EOF'
Host <detonation-host>
  User <user>
  IdentityFile ~/.ssh/dacs_detonation
EOF

# Records the host key. Before answering yes, compare the fingerprint shown
# with the output of this, run on the detonation host itself:
#   ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
ssh <detonation-host> 'command -v flightsim'
```

The `Host` name is exactly the value `DETONATION_HOST` will hold. The last
command must print flightsim's path without prompting a second time. If the
detonation host is ever rebuilt, its key changes and detonation stops with a
host key error until the new key is checked and `known_hosts` updated.

## 3. Splunk

- A service user whose role can search the DNS (and later endpoint) indexes,
  token authentication enabled, and a token for that user: `SPLUNK_TOKEN`.
- The DNS tunneling saved search with the TheHive alert action configured as
  in `docs/standards/thehive-alert-action.md`: title `<inheritance>`, Unique ID
  field empty, scope limited to listed fields, source `splunk`.
- `src_ip` mapped as an observable. Check the lookup exists first, because the
  add-on fills it with TheHive's default types only when it is missing, and
  writing it first would leave only your row:

  ```
  | inputlookup thehive_datatypes | stats count
  ```

  If that returns 0, fire the alert action once so the add-on creates the
  file. Then, in the TA-thehive-cortex app:

  ```
  | inputlookup thehive_datatypes
  | append [| makeresults | eval field_name="src_ip", field_type="observable", datatype="ip", description="DACS host correlation for network rules" | fields - _time]
  | dedup field_name
  | outputlookup thehive_datatypes
  ```

## 4. TheHive

- A service account in the organisation the alerts land in, allowed to read
  alerts and update them (`manageAlert/update`). Its API key is
  `THEHIVE_API_KEY`.
- Confirm `Other` is an alert status in the Closed stage. Cleanup refuses to
  close anything otherwise:

  ```
  curl -s -H "Authorization: Bearer $THEHIVE_API_KEY" -H 'Content-Type: application/json' \
    -d '{"query":[{"_name":"listAlertStatus"}]}' https://<thehive>/api/v1/query
  ```

- Exclude the tag `Control Validation` from notifications, Functions and
  Cortex responders.

## 5. Azure DevOps

- The `detonation-lab` environment with an Approvals check (README step 8),
  before anything runs.
- The `detonation-lab` variable group:

  | Variable | Value | Secret |
  |---|---|---|
  | `DETONATION_HOST` | the `Host` name from the agent's SSH config | no |
  | `DETONATION_USER` | the detonation user | no |
  | `DETONATION_HOST_ADDRESSES` | the host's addresses, comma-separated | no |
  | `SPLUNK_URL` | `https://<splunk>:8089` | no |
  | `SPLUNK_TOKEN` | Splunk token | yes |
  | `THEHIVE_URL` | `https://<thehive>` | no |
  | `THEHIVE_API_KEY` | TheHive API key | yes |
  | `SPLUNK_CA_CERT`, `THEHIVE_CA_CERT` | CA bundle paths on the agent, private CA only; also uncomment them in the pipeline | no |

- A Branch control check allowing only `refs/heads/main` on both the variable
  group and the agent pool, and an Approvals check on the variable group.
- Register the pipeline:
  `python tools/ado_setup.py --org ... --project ... --repo ... --with-detonation`.
  Then authorize `detonate-nightly` to use the variable group, the pool and
  the environment.

## 6. First run

1. Announce the window and the detonation host to the SOC.
2. Set `DETONATION_ENABLED` to `true`. Manual runs skip the stage without it
   too:
   `az pipelines variable create --pipeline-name detonate-nightly --name DETONATION_ENABLED --value true`
3. Queue `detonate-nightly` by hand from `main` with scenario
   `scenarios/network.threatest.yaml`.
4. Expect: the variable check passes, the `detonation-results` artifact shows
   the scenario passed, and TheHive shows the DNS tunneling alert closed as
   Other with the tag Control Validation. This run is the end to end proof
   the matchers have not had yet.
5. If it fails:
   - "... is not set in the detonation-lab variable group": fix the group.
   - "host ... is not in known_hosts" or "key mismatch": redo the SSH step in
     section 2 as the agent's user.
   - "did not find TheHive alert": walk the chain. The resolver logs for the
     run are in Splunk; the saved search fired; the add-on's log shows the
     alert sent; the TheHive alert has a `src_ip` observable equal to an
     address in `DETONATION_HOST_ADDRESSES`.
6. Leave the variable set. The weekday 07:00 UTC schedule takes over from
   `main`.
