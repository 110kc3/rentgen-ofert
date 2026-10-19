# Local versioned-storage and rollback prototype

Implemented and rehearsed October 19, 2026. This is a local filesystem/HTTP
prototype, with an optional reader in the static UI. No regional configuration
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
is written to a temporary file, flushed, atomically replaced and its parent
directory flushed. Injected interruptions remove staging and leave the pointer
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
private history return 404. This Linux prototype uses `fcntl` and same-filesystem
rename; it is not an object-store adapter or a production web server.

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

## Remaining rollout gates

The local partial-upload/rollback and mixed-backend behavior is demonstrated.
Nationwide storage acceptance remains open. A future selected service needs
real quota/cost/transfer measurements, public HTTPS/CORS/cache checks, immutable
write permissions, complete upload verification, conditional pointer updates
for multiple writers and remote rollback rehearsal. Its retention/garbage
collection policy must protect versions used by open tabs. This prototype does
not assert crash durability of object writes during host power loss.

The current generator still derives publication metadata from local regional
trees and includes those trees in the Pages artifact. Reader configurability
alone does not remove that artifact's storage ceiling. Workflow upload, catalog
handoff and exclusion of remote payloads from Pages need a separately selected
deployment slice. No hosting account/provider or migration is selected here.
[TODO.md](../TODO.md) owns the current handoff; [the rollout plan](../POLAND_ROLLOUT.md)
owns overall capacity and cohort acceptance.
