# ADS: DNS Tunneling via High Volume Unique Subdomains

Rule id: 6f1c2a4e-9b07-4d2f-8a31-5c7e0d3b1f88
Rule file: detections/network/dns_tunneling_high_volume_subdomains.yml
Status: in_test
Author: Skip Cruse (f8al)
Last reviewed: 2026-09-30

## 1. Goal

Detect data being encoded into DNS query labels by identifying internal hosts
that resolve an anomalous number of unique subdomains under a single registered
domain in a short window.

## 2. Categorization

Command and Control / Application Layer Protocol: DNS (T1071.004).
Secondary: Exfiltration / Exfiltration Over Alternative Protocol: DNS (T1048.003).

## 3. Strategy Abstract

Resolver query logs are aggregated over fixed five minute windows. For each
source address and registered domain pair, distinct fully qualified query names
are counted. When the count exceeds 50, an alert is raised. Registered domain is
derived by public suffix list lookup so that per customer subdomains of a shared
provider do not collapse into one key. Domains on the vendor allow list,
lookups/dns_allowlist.csv, are excluded before counting. Sigma has no lookup
construct, so the exclusion is applied on the platform when the rule is
deployed.

## 4. Technical Context

DNS tunneling encodes payload bytes into the leftmost labels of a query name and
receives responses in TXT, NULL or CNAME records. Because each carried byte
requires a fresh query, the signature is volume of unique labels rather than
volume of queries. Tools in this class include iodine, dnscat2 and the AlphaSOC
flightsim tunnel-dns module.

Normal in this environment: endpoint security agents and email gateways perform
reputation lookups that also produce many unique subdomains. Those are enumerated
on the allow list and are the dominant false positive class.

The required data source is the internal resolver, not the egress boundary.
Passive DNS collected at the perimeter shows the resolver as the client for every
query and loses the attribution this detection depends on.

## 5. Blind Spots and Assumptions

- Assumes all clients use the internal resolver. A host configured with an
  external resolver, or one using DNS over HTTPS, is invisible to this log source
  entirely. This is the largest gap and it is not mitigated by tuning.
- An adversary staying under 50 unique labels per five minutes per domain evades
  this outright. Low and slow tunneling is a known miss.
- Spreading labels across several registered domains splits the count across keys
  and evades the grouping.
- Windows are fixed, not sliding: the Splunk conversion bins on five minute
  boundaries. A burst that straddles a boundary is split across two windows, so
  up to twice the threshold can pass unseen. A platform that supports sliding
  windows closes this gap.
- Assumes public suffix list resolution is current. A newly delegated suffix can
  cause undercounting.
- No coverage for tunneling over protocols other than DNS.

## 6. False Positives

| Source | Handling |
|---|---|
| Endpoint security reputation lookups | Allow list, lookups/dns_allowlist.csv |
| Email security gateway per message subdomains | Allow list |
| CDN and telemetry service discovery | Allow list |
| Internal vulnerability scanner performing DNS enumeration | Suppress by scanner source address |

## 7. Validation

```
flightsim run tunnel-dns -fast
```

Automated: scenarios/network.threatest.yaml, scenario name
"DNS tunneling detected from egress host", asserted in TheHive with a thirty
minute timeout and host correlation: an alert with this rule's title, created
after the run started, with a `src_ip` observable equal to a detonation host
address. Resolver logs never carry the Threatest UUID, so the binding is the
dedicated detonation host, see docs/testing-strategy.md, Correlation. Runs in
the nightly detonation job. Requires egress access from the detonation
host and prior approval, because flightsim tunnel-dns queries an AlphaSOC
operated sandbox domain.

## 8. Priority

High. Expected volume after allow listing is under five alerts per week. A true
positive is either active exfiltration or established command and control, both
of which warrant same day investigation.

## 9. Response

See docs/runbooks/dns-tunneling.md. Summary: identify the host, confirm the
registered domain is not a known vendor, pull process to network attribution from
EDR for the querying process, and escalate to IR if the process is not a known
resolver client.

## Additional resources

- https://attack.mitre.org/techniques/T1071/004/
- https://github.com/alphasoc/flightsim
- Related: detections/network/dga_resolution_pattern.yml (not yet written)
