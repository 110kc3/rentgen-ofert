# Current queue — rentgen-ofert

Updated 2026-10-17. This file owns accepted work and the next-session handoff.
[Development history](docs/HISTORY.md) preserves the former diary and unselected
ideas. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns expansion and capacity gates;
its historical task lists do not authorize additional work.

## Completed repair and selected stability/storage follow-up

The owner selected review items 1–3, then continued items 3 and 4: stability
verification and the measured P4 index/archive slice, with push authorized.
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

## Verified RCN production recovery — October 17

Repair commit `6fbb266` passed [scrape 38982350853](https://github.com/110kc3/rentgen-ofert/actions/runs/38982350853)
and [deploy 38988650534](https://github.com/110kc3/rentgen-ofert/actions/runs/38988650534).
All 476 tests, payload/source/RCN validation and isolated branch publication
passed. Śląskie ref `09aa75c472428a8a9378a34b1f8d686284118b08` is served live:
31,063 cards / 52,198 raw offers, healthy export-backed RCN with 315,432 flat /
576,596 building deeds, 3,850 matches, 112 confirmed archive sales and
**78.2-minute total runtime**. Snapshot date is October 16, the job's start date;
retrieval completed after midnight. Source hashes agree with the local audit.
Archive checkpoint remains complete (Oct 15 / 49,854 records), with zero critical
photo deferrals/backlog and no unresolved groups. Its 76-file branch is isolated.

Opolskie remains unchanged at `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b`:
3,665 cards, degraded September 28 RCN and complete October 13 archives.
Its next eligibility is **October 19 22:15:19 UTC**, subject to the hourly tick,
queue and schedule delays. The repaired two-region stability clock has **not
started**. Do not dispatch a workflow to accelerate it. Małopolskie remains
disabled and recoverable at `cba13c7`.

## P4 index/archive slice — implemented locally, publication pending

The next automatic publications use schema 3: column-table current/archive
faces, existing lazy current detail shards and new lazy archive detail shards.
All filters, sold banners and per-record timelines are retained. Distinct archive
histories sharing a portal URL get distinct detail keys. The reader supports
old regional schemas during serial migration. Version/hash, file/count/key and
deployment-completeness guards cover both detail namespaces; errors remain
retryable. No hosting migration is included.

On the frozen Silesian payload: raw current index 24.30 → 18.61 MB, archive entry
17.85 → 1.30 MB, full payload 124.69 → 116.17 MB (6.84% smaller). Browser cold
fetch/parse/decode improved slightly in the measured 8 Mbps/80 ms case, while
warm decode costs about 27 ms more. This does not meet nationwide hosting
capacity/rollback acceptance. [Payload contract and measurements](docs/PAYLOAD.md)
record the protocol, browser checks and remaining P4 gates.
Local verification: **492 tests**, 11 real Chromium checks, exact current-face
and archive-detail roundtrips, and full frozen-payload/source/RCN validation
(with the audit-only streaming history syntax check documented in the guide).

## Next accepted checks — after this push

- [x] Check repair commit `6fbb266` scrape/deploy and live Silesian RCN recovery.
- [ ] Check this storage push's completed scrape and deployment once next session in
  [Actions](https://github.com/110kc3/rentgen-ofert/actions?query=branch%3Amain).
  Require the offline suite, payload/source/RCN validators and regional staging
  to pass. Confirm schema 3 and both index/detail namespaces agree with the manifest,
  including an archive-detail retry and an older regional payload. Retain healthy
  RCN provenance and continuity. The push-triggered refresh is Śląskie; Opolskie stays on its
  existing automatic 72-hour cadence. Do not dispatch a run to accelerate it.
- [ ] Confirm both regions publish fresh healthy RCN snapshots under the repair.
  Reconcile changed matches, benchmarks and derived sale claims against the
  broader export evidence; a rise in source records is not a sales-growth claim.
  Preserve the last good cache if either layer fails validation.
- [ ] From the first healthy repaired two-region baseline, record at least seven
  healthy days and three successful automatic Opolskie cycles. Require source
  continuity, no critical photo deferrals/backlog, persisted archive completion,
  normal no-op behavior, regional isolation, and ordinary plus fresh-RCN runs
  ≤180 minutes (preferred ≤150). The known unresolved two-ad Opolskie group
  must stay separate; it is not permission to merge without evidence. Investigate
  failures/missed cycles and restart the observation after recovery.

**Storage push verification is pending; RCN repair is production-verified for Śląskie.**
Do not wait/poll after push. There are no owner-only blockers. Expansion and P4
hosting/rollback work remain gated and require separate selection; the measured
index/archive slice does not accept nationwide capacity.
