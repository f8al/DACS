# Runbook: DNS Tunneling via High Volume Unique Subdomains

Alert name as it appears in the console: DNS Tunneling via High Volume Unique Subdomains
Rule id: 6f1c2a4e-9b07-4d2f-8a31-5c7e0d3b1f88
Severity: high    Response action: ticket
Owner: detection-engineering    Last reviewed: 2026-09-30

## What fired and why it matters

One internal host resolved more than 50 unique subdomains under a single
registered domain within five minutes. That pattern carries data inside query
names, which is how DNS tunneling both exfiltrates and receives commands.

## Triage in order

1. Note the source address and the registered domain from the alert.
2. Check the registered domain against the vendor allow list and against
   reputation sources. A known security vendor domain is the most common benign
   cause.
3. Pull the query names. Random or base32 looking leftmost labels of consistent
   length indicate encoding. Human readable labels indicate a vendor lookup.
4. Check the record types. Sustained TXT or NULL queries to one domain is
   strongly indicative.
5. From EDR, attribute the queries to a process on the host. A browser or a
   security agent is expected. An unsigned binary, a scripting host or a service
   you do not recognize is not.
6. Check whether the same domain is queried by other hosts. One host is likely
   compromise. Many hosts is likely a vendor product you have not allow listed.

## Close as benign when

- The registered domain belongs to a deployed security or email product and the
  querying process matches that product.
- The source is the authorized vulnerability scanner performing enumeration.
- The activity traces to a detonation run from the detonation host. Confirm the
  querying process has a parent whose name contains the Threatest detonation
  UUID before assuming this.

## Escalate when

- The querying process is not attributable to installed software.
- The registered domain has no reputation or was registered recently.
- Query volume continues after the initial window.

Escalate to: incident response. Include: host name, source address, registered
domain, sample query names, record types, querying process and its parent, and
the time window.

## Containment options

1. Block the registered domain at the resolver. Authorized by the SOC lead.
2. Isolate the host in EDR. Authorized by the IR on call.
3. Disable the user account if credential use is suspected. Authorized by IR
   together with identity operations.

## Known false positives

See docs/ads/dns-tunneling.md section 6.

## If this alert is noisy

Open a tuning work item with seven days of alert counts grouped by registered domain.
The fix is almost always an allow list addition, not a threshold change. Do not
disable the rule in the console.
