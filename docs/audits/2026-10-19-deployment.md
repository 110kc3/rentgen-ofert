# Deployment artifact dry-run and Opolskie recovery check — October 19

The owner selected (1) scheduled Opolskie recovery verification and (2) a local
deployment dry-run, with push authorized. Starting source commit:
`6a5894deb8a1ae71c947a25070617165febcd80e`. Retention/provider selection, remote
provisioning, workflow dispatch and region expansion were not selected.

## Recovery check: pending the scheduled publication

At **2026-10-19 20:15:17 UTC**, live Opolskie still reports its Oct 16 22:15:19
publication with degraded Sep 28 RCN, 3,665 cards and 573 archive cards. The next
72-hour eligibility is **Oct 19 22:15:19 UTC**, plus hourly scheduling/queue delay.
No workflow was dispatched. This check cannot accept recovery or start the
seven-healthy-day/three-automatic-Opolskie-cycle observation.

Śląskie is healthy, updated Oct 19 15:14:04 UTC, data ref
`d9613011be98fb8532c8d163ebfdb3a3b7a51771`: 30,926 cards, 3,872 matched properties,
111 archive sale claims and 4,937.5 seconds (82.3 minutes) runtime. Both validated
RCN export counts/hashes remain unchanged. Source continuity and ordinary
runtime do not substitute for a healthy repaired publication in the other region.

The starting documentation handoff passed [scrape 39279297132](https://github.com/110kc3/rentgen-ofert/actions/runs/39279297132)
and [deploy 39282872502](https://github.com/110kc3/rentgen-ofert/actions/runs/39282872502)
at the one recorded status check. The new dry-run push remains pending CI/Pages.

## Artifact/catalog handoff

`python -m scripts.deployment_dry_run` consumes frozen local regions and an
explicit mapping to local immutable-store mirrors. It verifies every mapped
version's inventory, bytes and full public-data contract before generating any
candidate. Remaining local regions undergo the same served-data validation.
Unknown/disabled mappings, bad pointers, missing/corrupt shards and invalid
legacy siblings fail the build. Mirrors are rechecked after rendering.

The generated browser catalog, summaries, alternate JSON, JSON-LD downloads and
`llms.txt` all use the verified immutable version. Readers skip the mutable
pointer when the catalog contains a version. New visitors cannot drift onto a
different version before the next complete artifact is installed. Old tabs keep
their version after either a pointer update or artifact installation.

External payloads are absent from the candidate `site/data/<region>` tree.
Disabled datasets, private history and caches are excluded. The complete result
is built in a temporary directory and renamed to a new output path only after
checks succeed. Existing artifacts, inputs and pointers are not overwritten.
The normal deployment workflow still uses its current local data overlay; it
does not run this builder or upload to storage.

## Frozen full-data measurements

The rehearsal uses the earlier frozen Śląskie ref
`8849971a3a3030eb8e6034183459913fc2de061f` and Opolskie ref
`a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b`, whose complete public files were
validated in [the storage audit](2026-10-19-storage.md). They are measured inputs,
not a claim that the candidate contains the latest live counts.

Śląskie's verified external version is
`81bf3a56b0c0c3cac95334458b7696e4a962d0d9c53d2e5fa8d97cf0c875cd4c`:
134 public files, 116,763,038 bytes including its immutable inventory.
Opolskie stays on Pages with schema 2 and 70 public files / 9,196,360 bytes.

| Candidate Pages artifact | Bytes |
|---|---:|
| Both regional datasets on Pages | 126,419,100 |
| Śląskie external, Opolskie on Pages | 9,671,566 |
| Pages bytes saved | 116,747,534 |

Generated URL/catalog differences account for the small difference between
excluded payload bytes and artifact bytes saved. The mirror uses an example
HTTPS origin for this offline size rehearsal; that origin is not a deployed
service. These measurements demonstrate artifact exclusion, not provider quota,
cost, transfer policy or nationwide capacity acceptance. Retained versions still
consume storage and remain part of the separate hosting gate.

## Verification and handoff

All **518 offline tests** pass. Twelve new real Chromium checks exercise complete
artifacts on two loopback origins: both backends and statistics pages, all six
advertised dataset downloads, catalog pinning across pointer advancement,
rejected incomplete candidates, a complete second artifact and old archive
timelines across installation. The original pointer-only prototype's twelve
Chromium checks also pass. Both harnesses have no uncaught browser errors and
block outside network access. [STORAGE.md](../STORAGE.md) gives CLI/config and
browser reproduction commands.

Full frozen CLI output, exact measurements, browser checks and the bounded
production metadata check are under `/tmp/rentgen-deployment-20261019/`.
Scraped data, generated artifacts and audit-only browser dependencies are not
committed. No production configuration, object pointer, data branch or Pages
deployment was changed manually. Next session: check this implementation push
once, then verify Opolskie's scheduled result if complete. Item 1 remains pending.
