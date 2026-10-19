# Current queue — rentgen-ofert

Updated 2026-10-19. This file owns accepted work and the next-session handoff.
[Development history](docs/HISTORY.md) preserves the former diary and unselected
ideas. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns expansion and capacity gates;
its historical task lists do not authorize additional work.

## Completed repair and selected stability/storage follow-up

The owner selected review items 1–3, then continued items 3 and 4: stability
verification and the measured P4 index/archive slice, with push authorized.
On October 19 the owner selected production acceptance and a local versioned-
storage/rollback prototype, with push authorized.
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

Śląskie ref `f4051cffa4c9266b57db74b5472d2867fc347a97`, updated Oct 19
13:50:28 UTC: schema 3, 30,879 cards, 4,092 archive cards,
3,869 RCN matches and 111 archive sale claims. Healthy export-backed RCN retains
315,432 flat / 576,596 building deeds and the validated October 17 hashes.
Ordinary runtime is 80.5 minutes, with zero critical photo deferrals/backlog;
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
still includes local payloads in Pages; no remote upload/deployment is implemented.
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

## Next accepted checks — after this push

- [x] Verify repair commit `6fbb266` and healthy Silesian RCN production recovery.
- [x] Verify compact storage commit `2c20374`, complete live payloads, archive retry
  and the older regional format; reconcile production documentation.
- [x] Rehearse local immutable publication/rollback and mixed storage backends.
- [x] Verify prototype/reader commit `f195e9b`: scrape/deploy, strict pipeline
  validation and default Pages listing/statistics readers all pass.
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

Expansion, provider selection, remote migration and the remaining P4 hosting
work require separate selection. Local rollback checks do not accept nationwide
capacity or the seven-day cohort. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns those gates.

The incoming documentation-only handoff push is pending CI/Pages verification;
check its commit once next session. No implementation remains selected before
the scheduled Opolskie recovery; do not wait/poll or dispatch a workflow.
