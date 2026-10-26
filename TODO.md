# Current queue — rentgen-ofert

Updated 2026-10-26. This file owns accepted work and the next-session handoff.
[Development history](docs/HISTORY.md) preserves the former diary and unselected
ideas. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns expansion and capacity gates;
its historical task lists do not authorize additional work.

## October 26 private Pi hosting verified

The owner resumed the private KW integration handoff on the Pi. Work stays on
`codex/kw-integration-2026-10-25` in a separate worktree; the existing main checkout
is preserved. The client now enables HTTPS catalogue access only when the private
server supplies a discovery marker matching the exact page origin. Public Pages
contains no marker or private catalogue data and performs no API discovery probes.
Requests remain same-origin, uncached and refuse redirects.

All 539 tests pass on ARM64 with Python 3.11.2 and Node 22.23.3. Both existing
regional snapshots build and pass Chromium listing/filter/timeline checks. The
companion backend and seven combined checks pass on loopback and a local TLS
fixture, including anonymous denial and identity revocation. The fixture is not
evidence of a deployed remote login. No scrape or workflow was dispatched.

The owner selected private Tailscale HTTPS. The companion service is installed,
enabled and restart-tested, with anonymous/unapproved app/data/API denial and
identity revocation/restoration checked locally. Consent is complete and the private
HTTPS route is active. Seven combined browser checks and both real regional listing/
filter/timeline checks pass through actual Tailscale Serve with certificate validation.
Removing the allowed identity denies every app/data/API route, even with a forged
allowlisted identity header; restoring it returns successful search. Test requests
originated on the Pi through its real tailnet listener; a separate laptop check and
full Pi reboot were not observed. The selected migration is complete. No new scraper,
acquisition, refresh or monitoring schedules were enabled.
The private repo owns runtime paths, catalogue and deployment configuration. See
[KW_INTEGRATION.md](docs/KW_INTEGRATION.md). Acquisition remains paused there.
This branch remains unmerged and has not been deployed to public Pages. Push
verification is pending on the [integration branch Actions view](https://github.com/110kc3/rentgen-ofert/actions?query=branch%3Acodex%2Fkw-integration-2026-10-25);
its current push filters do not trigger a branch run. No run existed for checkpoint
`9e1f015` at the single recovery check. The unrelated production queue below remains
unchanged by this migration.

## October 22 selected acceptance checks and storage plan

The owner selected fresh two-region RCN acceptance, the stability observation,
and **planning only** for expansion/storage, with push authorized. Infrastructure,
provider/account selection, a new region and manual workflow dispatch remain
outside this batch. The [cohort checkpoint](docs/audits/2026-10-22-cohort-checkpoint.md)
records the current evidence and the next verification procedure; the
[storage plan](docs/STORAGE.md#production-storage-and-expansion-plan--october-22)
defines item 3's deliverable and future acceptance criteria.

Latest Śląskie ref `e351e4e`, published October 22 13:00:42 UTC: 30,970 current
cards, 4,137 archives, 110 sale claims and 3,906 matched histories. Scheduled
scrape `39770778678` and deploy `39783221230` passed; 535 CI tests, all 268 live
JSON files across both regions and nine focused Śląskie Chromium checks pass.
Strict continuity against the previous publication passes without override.
Runtime is 91.3 minutes and critical photo deferrals/backlog remain zero.

Neither remaining acceptance gate is complete. Śląskie still uses its healthy
October 16 RCN cache; the seven-day refresh boundary is October 23. Opolskie
still publishes degraded September 28 RCN, with automatic eligibility October
23 01:36:15 UTC plus schedule/lock delays. Both retained archive checkpoints are
complete, but new maintenance cycles have **100 / 52 pending partitions** after
HTTP 429. Retaining the old checkpoint does not accept those unfinished cycles.
The repaired two-region stability clock remains unstarted, with zero accepted
cycles. Verify the next automatic publications rather than dispatching a run.

This documentation-only push matches neither push workflow. Push verification
is pending until the scoped commit is published; use the branch Actions view
at the next session. No runtime or production configuration changes are included.

## October 22 scheduled source recovery — verified

Pulled `main` with `--ff-only`; already at `385ea9a`. The next accepted task is
complete: [automatic Śląskie scrape 39678803197](https://github.com/110kc3/rentgen-ofert/actions/runs/39678803197)
passed 535 tests, strict source/type/RCN validation and regional staging with
`ALLOW_SOURCE_REGRESSION: false`; [deploy 39689522871](https://github.com/110kc3/rentgen-ofert/actions/runs/39689522871)
passed. This is a real publication, not a green hourly no-op.

New data ref `b0ce686`, published Oct 21 22:51:19 UTC: 31,000 cards, 4,091 archive
faces, 110 sale claims, 3,902 RCN matches; Gratka/Morizon recovered to 12,341 rows
each. Runtime 84.1 minutes, zero critical photo deferrals/backlog, persisted archive
checkpoint complete. All 134 public JSON files validate and nine live Chromium
checks pass. The two removed archive histories are preserved and active; one
carried the former sale claim, explaining the archive/sale-count changes.
See the [source-recovery audit](docs/audits/2026-10-22-source-recovery.md).

Śląskie still uses its healthy October 16 RCN cache. Opolskie remains on its
October 20 publication with degraded September 28 RCN and 52 archive checkpoints
pending. Next automatic eligibility is **October 23 01:36:15 UTC** plus schedule/
lock delays. Fresh two-region RCN acceptance and the stability observation remain
open; the clock has not started. No manual dispatch, override, new region or
hosting work was selected. Earlier dated sections retain their original evidence.

## Earlier October 21 selected address/source repairs

The owner selected both numbered audit findings. Implementation and live UI
verification are complete. The initial data refresh was correctly refused after
Gratka HTTP 503 responses; a healthy automatic replacement remains pending.

- [x] Repair manual address RCN lookup/copy clicks and verify success, re-render,
  clipboard fallback and accurate provider-failure handling in Chromium.
- [x] Investigate the 37-row collapse and reject abrupt source/type volume loss
  before publication, with an explicit logged override for intentional resets.

535 offline tests, 12 focused and 33 broad candidate Chromium checks pass. A real-provider candidate
check reaches UUG, ULDK and both WFS layers with HTTP 200, displays the parcel and
copies the command without opening a listing. The actual failed October 20
metadata is rejected at six source/type transitions; healthy publication drift
and the full frozen public dataset pass. Baselines of at least 100 offers must
retain at least half, independently per source/type. The conservative threshold
does not assert complete coverage or detect gradual long-term decline.
See the [repair audit](docs/audits/2026-10-21-controls-and-continuity.md).

Production follow-up: commit `3780e09` passed
[UI deploy 39627380687](https://github.com/110kc3/rentgen-ofert/actions/runs/39627380687),
and 33/33 live Chromium checks pass, including real GUGiK address lookup/copy.
All 268 public JSON files validate. Its
[scrape 39627380782](https://github.com/110kc3/rentgen-ofert/actions/runs/39627380782)
passed 535 tests but failed source continuity after Gratka returned zero offers.
Regional push and the dependent data deploy were skipped. Śląskie retains the
healthy 14:04 UTC publication (`8145ae2`, 30,876 cards / 4,093 archives / 111 sale
claims) and both regions' prior evidence is intact. This refused refresh cannot
count toward stability. The audit records complete production evidence.

Transport commit `eb7aeab` passed [scrape 39592569525](https://github.com/110kc3/rentgen-ofert/actions/runs/39592569525)
(524 tests and strict validation) and [Pages 39602509595](https://github.com/110kc3/rentgen-ofert/actions/runs/39602509595)
at the single recovery check. Production Opolskie fresh-RCN acceptance and the
seven-day/three-cycle observation remain open; next eligibility remains October
23 01:36:15 UTC plus scheduling delays. No manual dispatch or new region selected.

## Earlier October 21 recovery and feature audit

The owner selected Opolskie RCN transport recovery and a Śląskie feature audit.
Production logs show both GUGiK connections timed out before parsing, spending
26 minutes in the portal retry ladder. RCN now has its own session, 10-second
connect timeout, one adapter retry and up to three complete export-download
attempts. Interrupted streams restart bytes/hashes; invalid data and failed
second layers still preserve the previous atomic cache and retrieval date.

524 offline tests pass. A fresh local refresh of the actual Opolskie cache copy
validated 63,494 flat / 86,224 building deeds in 19.78 seconds. No cache was
uploaded. Commit `8733060` passed its 518-test scrape, strict validation and
Pages deployment. Its previously pending verification is resolved.

Both complete live public trees validate (134 JSON files each). Śląskie passes
32/33 live Chromium checks; manual address RCN check/copy controls are blocked
by event propagation. A transient 37-row Gratka/Morizon collapse also escaped
categorical continuity. These were unselected findings at that audit; both were
subsequently selected and repaired above. The
[earlier audit](docs/audits/2026-10-21-rcn-and-features.md) retains its original evidence.

Opolskie published October 20 01:36:15 UTC with degraded September 28 RCN and
a new archive cycle rate-limited at 52 pending checkpoints. Next automatic
eligibility is **October 23 01:36:15 UTC**, subject to scheduling/lock delays.
Śląskie remains healthy with 30,914 current cards, 4,092 archive cards and 111
sale claims; zero critical photo deferrals/backlog. The repaired two-region
stability clock has **not started**. This transport push requires its own
CI/Pages check; production Opolskie recovery remains pending.

Earlier dated sections below retain their original evidence; this section
supersedes their outstanding-status snapshots.

## Completed repair and selected stability/storage follow-up

The owner selected review items 1–3, then continued items 3 and 4: stability
verification and the measured P4 index/archive slice, with push authorized.
On October 19 the owner selected production acceptance and a local versioned-
storage/rollback prototype, with push authorized.
The owner then selected Opolskie recovery verification and the local deployment
dry-run, with push authorized. Retention/provider selection was not selected.
No additional region, concurrent matrix, new hosting infrastructure, automatic
KW acquisition, historical identity rewrite or manual workflow dispatch is selected.

1. **RCN ingestion repair:** support GML temporal deed dates and use GUGiK's
   official provincial GeoParquet exports when a complete WFS pull fails.
   Both export layers must pass schema, region, unique-ID, file completeness
   and existing snapshot-count checks before atomic replacement. Source URLs,
   file hashes, raw row counts and the WFS failure are retained in provenance.
   Nonpositive rounded prices and nonpositive flat areas are unusable deeds.
   Local verification passed: 476 tests, fresh validated snapshots for both
   regions and frozen-history replays reproducing the prior baseline before
   passing RCN continuity validation with the broader export evidence.
   See the [October 17 audit](docs/audits/2026-10-17-rcn-exports.md).
2. **Documentation reconciliation:** this compact queue replaces the historical
   diary as the current entrypoint. README, rollout status and KW verification
   now distinguish completed evidence from pending acceptance.
3. **Stability gate assessed, not accepted:** the last three automatic Opolskie
   cycles (October 10, 13 and 16) published successfully but all retained degraded
   RCN evidence. They cannot count as three healthy cycles or seven healthy days.
   Restart the observation only after the repaired code publishes a fresh,
   healthy snapshot in both regions. Time and successful CI alone are insufficient.

## Production acceptance — verified October 19

Storage commit `2c20374` passed [scrape 39019602305](https://github.com/110kc3/rentgen-ofert/actions/runs/39019602305)
and [deploy 39019602307](https://github.com/110kc3/rentgen-ofert/actions/runs/39019602307).
All gate/publication steps passed. The live regional copies pass every public
payload/source/RCN check, including schema-3 hashes and both detail namespaces.
Eleven live Chromium checks pass, including archive-detail 503/retry, correct
timelines, sold filtering, mobile layout and the real older Opolskie archive.
[The October 19 audit](docs/audits/2026-10-19-storage.md) records complete evidence.

Śląskie ref `d9613011be98fb8532c8d163ebfdb3a3b7a51771`, updated Oct 19
15:14:04 UTC: schema 3, 30,926 cards, 4,092 archive cards,
3,872 RCN matches and 111 archive sale claims. Healthy export-backed RCN retains
315,432 flat / 576,596 building deeds and the validated October 17 hashes.
Ordinary runtime is 82.3 minutes, with zero critical photo deferrals/backlog;
archive checkpoint remains complete (Oct 15 / 49,854 records).

Opolskie remains at `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b`:
schema 2, 3,665 cards, degraded September 28 RCN and complete October 13 archives.
Its next eligibility is **October 19 22:15:19 UTC**, subject to the hourly tick,
queue and schedule delays. The repaired two-region stability clock has **not
started**. Do not dispatch a workflow to accelerate it. Małopolskie remains
disabled and recoverable at `cba13c7`.

## Local versioned storage/rollback — completed October 19

`scripts/versioned_storage.py` stages and validates complete public trees,
seals immutable version directories, then atomically switches an 89-byte
regional pointer. File hashes/lengths cover metadata/statistics as well as the
payload. Interrupted/invalid uploads retain the prior pointer; rollback verifies
the complete target and retains newer versions for open tabs. The local server
rehearses CORS and mutable/immutable cache policy.

Optional per-region pointer URLs reach both listing/statistics readers. Each
page pins all requests to one version; absent configuration retains legacy Pages
behavior. No production region is configured for external storage. The generator
still includes local payloads in its normal Pages workflow; the separately
selected artifact dry-run below omits external payloads without uploading them.
[The storage guide](docs/STORAGE.md) records commands, contract, capacity and limits.

Verification: **504 offline tests**, **12 Chromium prototype checks**, and
successful local publication of both full live payloads (134 / 70 files).
The prior compact-index/lazy-archive slice is production-accepted; its frozen
byte and browser measurements remain in [docs/PAYLOAD.md](docs/PAYLOAD.md).
Nationwide hosting capacity, remote atomic publication and rollout acceptance
remain open. There are no owner-only blockers for the completed local slice.

Prototype/reader commit `f195e9b` passed [scrape 39252423912](https://github.com/110kc3/rentgen-ofert/actions/runs/39252423912)
(504 tests, strict pipeline/source/RCN validation and 140-path regional staging)
and [deployment 39263676649](https://github.com/110kc3/rentgen-ofert/actions/runs/39263676649).
All three shipped reader scripts match the source; 13 live Chromium checks pass,
including both statistics pages. The sale-archive drop from 112 to 111 is traced
to one preserved history returning to the active market under another portal URL;
it is not a count of new transactions. See the audit's production follow-up.

## Deployment artifact dry-run — completed locally October 19

`scripts/deployment_dry_run.py` builds a new isolated `site/` artifact and size
report from frozen Pages inputs plus verified local storage mirrors. Catalog
metadata, raw-data discovery and both readers pin the same immutable version.
External payloads never enter the candidate Pages artifact; legacy siblings stay
on Pages. Missing/corrupt versions or invalid local siblings abort the whole
candidate. Existing artifacts, source data and object pointers are unchanged.

Verification: **518 offline tests**, **12 complete-artifact Chromium checks**,
and **12 pointer-only prototype Chromium checks**. Frozen full-data rehearsal:
126.42 MB for both datasets on Pages versus 9.67 MB with Śląskie external and
Opolskie local. The [storage guide](docs/STORAGE.md) and
[dry-run audit](docs/audits/2026-10-19-deployment.md) record commands, source
versions, exact measurements and limitations. The normal deployment workflow
does not invoke this dry-run; no remote host/provider was configured.

**Historical selected item 1 check:** at Oct 19 20:15:17 UTC Opolskie still
serves its Oct 16 publication and degraded Sep 28 RCN, before its next eligibility
at 22:15:19 UTC. The repaired two-region observation has not started. Continue
after the scheduled publication; do not accelerate it with a dispatch or wait
for the seven-day/three-cycle gate in this session.

## Next accepted checks — after this push

- [x] Verify repair commit `6fbb266` and healthy Silesian RCN production recovery.
- [x] Verify compact storage commit `2c20374`, complete live payloads, archive retry
  and the older regional format; reconcile production documentation.
- [x] Rehearse local immutable publication/rollback and mixed storage backends.
- [x] Verify prototype/reader commit `f195e9b`: scrape/deploy, strict pipeline
  validation and default Pages listing/statistics readers all pass.
- [x] Verify handoff commit `6a5894d`: [scrape 39279297132](https://github.com/110kc3/rentgen-ofert/actions/runs/39279297132)
  and [deploy 39282872502](https://github.com/110kc3/rentgen-ofert/actions/runs/39282872502)
  passed at the one recorded status check.
- [x] Build and verify a local artifact/catalog dry-run; see the completed slice above.
- [x] Verify RCN transport commit `eb7aeab`: scrape/strict validation and Pages pass.
- [x] Check address/continuity commit `3780e09` once: UI deployed, 535 CI tests
  pass, live controls/readers/payloads pass; source guard correctly refuses a
  Gratka outage and preserves the previous publication. See the audit.
- [x] Confirm a healthy automatic Śląskie publication after Gratka HTTP 503
  recovery: scrape 39678803197/deploy 39689522871 passed; full live payload,
  continuity without override and archive reconciliation verified October 22.
- [ ] Confirm both regions publish fresh healthy RCN snapshots under the repair.
  Reconcile changed matches, benchmarks and derived sale claims against broader
  export evidence. A rise in source records is not a sales-growth claim.
  Preserve the last good cache if either layer fails validation.
- [ ] From the first healthy repaired two-region baseline, record at least seven
  healthy days and three successful automatic Opolskie cycles. Require source
  continuity, no critical photo deferrals/backlog, persisted archive completion,
  normal no-op behavior, regional isolation, and ordinary plus fresh-RCN runs
  ≤180 minutes (preferred ≤150). The known unresolved two-ad Opolskie group
  must stay separate. Investigate failures/missed cycles and restart after recovery.

Expansion/storage planning is selected and recorded in the storage guide.
Expansion implementation, provider selection, remote migration and the remaining
P4 hosting work require separate selection. Local rollback checks do not accept nationwide
capacity or the seven-day cohort. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns those gates.

Both address/continuity push verification and healthy Śląskie source recovery
are recorded; do not repeatedly poll those terminal runs. The next TODO is the
fresh healthy two-region RCN check, led by Opolskie's next eligible October 23
publication. Leave guards active and preserve prior data on failure; no manual
dispatch selected. This documentation-only handoff matches neither push workflow.
Two-region fresh-RCN acceptance and the stability cohort remain open. The newest
checkpoint above supersedes earlier same-day publication/maintenance counts.
