# Local versioned-storage and rollback prototype

Implemented and rehearsed October 19, 2026. This is a local filesystem/HTTP
prototype and deployment artifact dry-run, with an optional reader in the static UI. No regional configuration
uses it in production, no workflow uploads to it, and no service was provisioned.
The existing Pages data branches/publication remain in use.

## Contract

An enabled region may optionally carry this browser catalog field:

```json
{"storage":{"pointer_url":"https://objects.example/slaskie/current.json"}}
```

`scripts/update-summary.mjs` preserves that field in `data/regions.json`. The
listing and statistics readers resolve it independently when each page opens.
Absent configuration keeps the existing `data/<region>` path and legacy
manifest/index/full-archive behavior. A configured storage failure is a load
error; falling back to a different snapshot would defeat version consistency.
HTTPS is required except for loopback HTTP during local rehearsal. Credentials,
query strings and fragments are refused in pointer URLs.

The mutable pointer is only **89 bytes**:

```json
{"schema":1,"version":"<64 lowercase SHA-256 hex characters>"}
```

Its sibling directory `versions/<version>/` contains the existing regional
manifest, current/archive indexes, `d/` and (schema 3) `a/` details, metadata,
statistics and RCN benchmarks. All these requests use the resolved version;
changing the pointer cannot change an open tab's subsequent archive requests.
Dry-run catalogs additionally carry `storage.version`, sealing even new page
loads to the verified version until the next complete artifact is installed.
Such readers skip the mutable pointer; pointer-only configuration remains
supported for the original local prototype.
The existing payload manifest/hash remains unchanged. A second, full SHA-256
version covers a canonical `release.json` inventory, whose entries contain the
length and SHA-256 of **every** public file, including metadata/statistics.
Internal lifecycle history and caches are excluded.

Schema 1/2 payloads remain readable; the publisher also accepts their split
indexes/shards. A pre-split monolithic region can continue using the default
Pages reader but is not an input format for this publisher.

## Publish, interrupt and roll back

Run from the repository root with its Python environment. Use a frozen regional
input directory (for example, extracted from an immutable data-branch commit),
not files being rewritten concurrently by a scraper. Store the rehearsal
outside the checkout so generated listing data cannot enter a source commit.

```bash
python -m scripts.versioned_storage --store /tmp/rentgen-objects \
  publish slaskie /tmp/frozen/slaskie
python -m scripts.versioned_storage --store /tmp/rentgen-objects \
  publish slaskie /tmp/candidate/slaskie --interrupt-after 7
python -m scripts.versioned_storage --store /tmp/rentgen-objects \
  activate slaskie PREVIOUS_64_CHARACTER_VERSION
```

The publisher takes a per-region local lock, copies public files into a hidden
staging directory, creates the inventory, checks every file hash/length and runs
the existing payload/source/RCN validator. Only the private history requirement
is omitted for this public copy; scrape validation retains its strict default.
An incomplete shard set, incorrect payload hash/count/key, invalid source/RCN metadata or
invalid candidate stops publication. A source with explicitly degraded but valid
RCN evidence remains degraded; storage publication does not repair it.

After successful checks, the complete directory is renamed into its version
path. An existing version is verified and reused, never overwritten. The pointer
is written to a temporary file, flushed, atomically replaced and, on POSIX, its
parent directory flushed. Injected interruptions remove staging and leave the pointer
unchanged; the first interrupted upload creates no pointer. Rollback rechecks
the entire target before replacing the pointer. Corrupted targets are rejected.
Old and new versions remain available to existing tabs after either switch.
There is intentionally no automatic version deletion in this prototype.

## Two-origin browser and HTTP rehearsal

`serve` binds only to loopback and exposes public pointers/version objects:

```bash
python -m scripts.versioned_storage --store /tmp/rentgen-objects \
  serve --port 8001 --origin http://127.0.0.1:8000
```

Pointers and errors use `Cache-Control: no-store`; version files use
`public, max-age=31536000, immutable`. The configured UI origin gets
`Access-Control-Allow-Origin` and `Vary: Origin`. Reads are credential-free;
the server has no upload endpoint. Hidden uploads, lock files, directories and
private history return 404. This prototype uses same-filesystem rename; it is not
an object-store adapter or a production web server.

Local Windows runs use a real one-byte `msvcrt` file lock; POSIX retains `fcntl`.
A second process cannot acquire the same publication lock. Windows lock
contention retries for up to ten seconds and fails before publication if still
locked. Both paths release the lock after errors. Windows retains file flushing
and atomic pointer replacement, but Python's directory-fsync operation is not
available there, so the extra POSIX directory-entry crash durability is not
claimed. SHA-256 streaming also supports local Python 3.10 environments.

Offline tests run with the normal `python -m pytest -q`. The optional Chromium
rehearsal creates a temporary UI, storage server, two-region fixtures and two
versions; it needs audit-only Playwright and a locally installed browser:

```bash
PYTHONPATH=. python tests/check_storage_browser.py --executable /path/to/chrome
```

It exercises the actual listing/statistics scripts across different origins,
interrupted upload, a tab reading its old archive after publication, a newer
tab retaining its archive after rollback, reload onto the previous version,
legacy Pages data beside the new backend and browser rejection of incorrect
CORS without snapshot fallback. It makes no external requests or writes.

## October 19 evidence and capacity

The existing live release first passed [production acceptance](audits/2026-10-19-storage.md).
Frozen copies of its public files then passed local publication:

| Region | Public files | Version directory bytes, including inventory | Inventory overhead |
|---|---:|---:|---:|
| Śląskie | 134 | 116,763,038 | 14,185 |
| Opolskie, legacy schema 2 | 70 | 9,203,706 | 7,346 |

All **504 offline tests**, **11 production Chromium checks** and **12 local
prototype Chromium checks** passed. Live/source hashes and counts are recorded
in the audit; no production data branch was modified by this rehearsal.

Sixteen versions equal to this measured Śląskie version would consume
1,868,208,608 bytes. Retaining two full versions would consume 3,736,417,216
bytes, requiring at least **5,337,738,880 bytes of capacity** to stay at or below
70% utilization. This is a sensitivity calculation, not a regional inventory
forecast, service quota, transfer estimate or cost estimate. Without pruning,
storage grows with every distinct publication; rollback retention must be
budgeted before selecting a host.

## Deployment artifact dry-run

The selected next slice builds a complete candidate artifact from frozen Pages
inputs and a local mirror of immutable storage. It performs no network requests,
upload, pointer activation or workflow dispatch. The normal Pages workflow does
not invoke it. Create a separate mapping file, leaving the canonical catalog
and production configuration unchanged:

```json
{"schema":1,"regions":{"slaskie":{"pointer_url":"https://objects.example/slaskie/current.json"}}}
```

```bash
python -m scripts.deployment_dry_run \
  --data-root /tmp/frozen \
  --store /tmp/rentgen-objects \
  --storage-map /tmp/storage-map.json \
  --output /tmp/pages-candidate
```

`--data-root` contains directories named for each frozen local region;
`--store` is the local object mirror from the publisher above. Mapped regions
must be enabled and known to the canonical catalog. The builder reads each
mirror pointer once, or takes an explicit `version` in that region's mapping,
then verifies the inventory, all file bytes and full served-data contract.
Pointer URLs must be absolute HTTPS (loopback HTTP is allowed for rehearsal).

Remote summaries/counts/freshness come directly from the verified version's
metadata. The generated browser catalog pins that version. Listing/statistics
summaries, JSON-LD downloads, alternate JSON and `llms.txt` use its immutable
URLs. A later pointer change cannot mismatch those summaries and the reader.
Remaining Pages regions receive their validated public files and keep their
older formats. Disabled regions, pipeline history and caches are excluded.

The generator reads external metadata through an internal temporary
`RENTGEN_PUBLICATION_PLAN`; only the builder supplies it after full verification.
It does not copy external payloads into `site/data/<region>`. Both local and
external inputs must pass; broken legacy siblings abort the complete candidate.
Mirror bytes are checked again after rendering. Missing/corrupted shards,
incomplete pointers, bad counts or invalid mappings leave no candidate output.

Builds happen in a sibling temporary directory and install by rename only after
all checks pass. Output must be a new directory outside the repo and all input
trees; existing artifacts are never overwritten. The result contains `site/`
(the candidate Pages artifact) and `report.json` with per-region versions/bytes
and the final artifact size. A dry-run failure does not change any previous
artifact, source tree or object pointer. This is not remote publication or a
power-loss durability guarantee.

518 offline tests pass. The optional complete-artifact Chromium rehearsal is:

```bash
PYTHONPATH=. python tests/check_deployment_browser.py --executable /path/to/chrome
```

Its 12 checks cover both listing/statistics backends, advertised downloads,
pointer advancement while the catalog stays sealed, an incomplete candidate,
installation of a complete second artifact and old archive timelines across
that installation. The original pointer-only prototype's 12 Chromium checks
also pass. Both harnesses use two loopback origins and no external network.

Using the same frozen regional files as the table above, the full local artifact
is about **126.42 MB**; leaving Opolskie on Pages and moving Śląskie to the mirrored
version yields about **9.67 MB**. The excluded version is 116,763,038 bytes including
its inventory. This demonstrates removal of the Pages payload ceiling in the
candidate build; it does not accept any provider quota, transfer budget, cost
or nationwide inventory projection. [The dry-run audit](audits/2026-10-19-deployment.md)
records source versions, exact sizes and the still-pending Opolskie recovery.

## Remaining rollout gates

The local partial-upload/rollback and mixed-backend behavior is demonstrated.
Nationwide storage acceptance remains open. A future selected service needs
real quota/cost/transfer measurements, public HTTPS/CORS/cache checks, immutable
write permissions, complete upload verification, conditional pointer updates
for multiple writers and remote rollback rehearsal. Its retention/garbage
collection policy must protect versions used by open tabs. This prototype does
not assert crash durability of object writes during host power loss.

The normal workflow still derives publication metadata from local regional
trees and includes those trees in its Pages artifact. Only the explicit dry-run
uses the verified catalog handoff and excludes remote payloads. Real workflow
upload, public URL verification and promotion of that candidate require a
separately selected deployment slice. No hosting account/provider or migration
is selected here.
[TODO.md](../TODO.md) owns the current handoff; [the rollout plan](../POLAND_ROLLOUT.md)
owns overall capacity and cohort acceptance.

## Production storage and expansion plan — October 22

The owner selected **planning only** for this item, alongside the RCN and
stability checks in [TODO.md](../TODO.md). This plan is complete as a design
handoff; every remote implementation step below remains deferred. No provider,
account, retention period, budget, migration or additional region is selected.

### Order and evidence required

| Step | Planned outcome | Acceptance before advancing |
|---|---|---|
| 1. Accept the current cohort | Fresh repaired RCN publications for both regions, then seven healthy days and three automatic Opolskie cycles. | Immutable refs/runs, both RCN layers and provenance, explained match/benchmark/sale changes, resumed archive cycles complete, zero critical photo backlog, normal no-ops, regional isolation and ordinary/fresh-RCN runtimes ≤180 minutes, preferred ≤150. |
| 2. Select service and retention | A dated comparison of candidate services against measured storage, requests, transfer and a monthly budget. | Verify current official quotas/pricing, public HTTPS, CORS/cache support, immutable object protection and conditional activation. Choose account ownership, retention/open-tab policy and budget before provisioning. No provider recommendation is implied by this plan. |
| 3. Rehearse one remote region | Upload a frozen Śląskie version while Opolskie continues on Pages. | Complete hash/length inventory verified through public URLs; no credentials exposed; interrupted/invalid upload preserves the prior release; conflicting activation is refused; remote rollback works. Both readers and discovery/download metadata pin the same version. |
| 4. Integrate publication | Upload/verify first, then generate and promote the sealed Pages catalog/artifact. | Existing local dry-run becomes the tested build input; external payloads stay out of the artifact. A failed upload, validation or build keeps the previous catalog/artifact. The mixed backend passes listing/statistics, lazy archive, error/retry and old-tab checks. |
| 5. Measure and select the next pilot | Decide whether one additional serial region fits storage, transfer and runner budgets. | Healthy current cohort; measured retained versions and projected full inventory below 70% quota; cold/warm pilot meets the existing rollout gates. Region choice and activation require separate selection. No concurrent matrix or nationwide enablement. |

The completed local publisher, rollback tests and artifact dry-run are inputs
to steps 3–4, not work to repeat or evidence that remote behavior already passes.
Allow roughly one focused session for the provider/cost decision and separate
implementation and verification slices for remote rehearsal and workflow
integration. Pilot acceptance depends on actual cold/warm runs; it has no fixed
completion date before those measurements exist.

### Capacity model includes retained publications

The [October 22 checkpoint](audits/2026-10-22-cohort-checkpoint.md) measures
116,550,340 public JSON bytes for Śląskie and 8,586,501 for Opolskie, each
134 files. These exclude the additional version inventory and service overhead.
Use actual regional release inventories when selecting a service. Two retained
versions alone do not model a retention window with repeated publications.

For a sensitivity calculation, let every one of 16 regions have Śląskie's
measured size `B`; retain an active and rollback version per region, plus every
publication in a `D`-day window, plus one serial staging version. With Śląskie
twice daily and 15 other regions every 72 hours, reserve:

`objects_bytes(D) = B × (32 + 2D + 15 × ceil(D / 3) + 1)`

This deliberately overcounts overlapping active/rollback versions. It assumes
every publication changes all objects, no cross-version deduplication and no
compression savings; it excludes growth, inventories and provider overhead.
The per-region ceiling handles cadence boundaries rather than rounding the
whole fleet down to an average seven publications/day.

| Illustrative window | Full-version equivalents | Public JSON GB | Quota floor at 70% usage, GB |
|---|---:|---:|---:|
| 7 days | 92 | 10.72 | 15.32 |
| 30 days | 243 | 28.32 | 40.46 |
| 90 days | 663 | 77.27 | 110.39 |

GB is decimal. These are scenario floors, not a nationwide forecast or selected
retention periods. Add measured regional sizes/growth, inventory overhead,
orphaned-upload allowance and rollback reserves before accepting capacity.
Budget uploads, object operations and download transfer separately: a session
usually fetches an index and selected lazy shards, not the whole release.
Measure those requests and distinguish bots from human sessions before
estimating transfer; existing traffic evidence does not establish a budget.

### Publication, retention and rollback decisions

Keep the existing data branches as the source of pipeline history/caches. Upload
only the validated public release to a new immutable version path; verify every
object before activation. Serialize publication and use conditional pointer
updates so another writer cannot silently replace a newer release. Readers
must pin the verified version; never fall back to a different snapshot on error.
Rehearse rollback of both the public catalog and any active pointer, with the
previous and newer versions still readable by already-open tabs.

The prototype has no garbage collector. A fixed deletion window cannot protect
arbitrarily old open tabs. Before implementing deletion, explicitly choose
either indefinite retention with a sustainable budget, or a bounded supported
tab lifetime plus a user-visible refresh/recovery path for expired versions.
Until that decision is implemented and tested, do not enable automatic deletion
or claim that one of the illustrative windows preserves every open tab.
Protect active, rollback and deployed-catalog versions even when older than a
chosen window; rehearsal must cover deletion races, interrupted uploads and
rollback after a newer publication.

The next implementation choice, after cohort acceptance, is step 2's dated
service/retention proposal. This plan does not create a second task queue;
[TODO.md](../TODO.md) remains the accepted-work entrypoint.
