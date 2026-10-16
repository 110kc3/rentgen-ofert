# Current queue — rentgen-ofert

Updated 2026-10-17. This file owns accepted work and the next-session handoff.
[Development history](docs/HISTORY.md) preserves the former diary and unselected
ideas. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns expansion and capacity gates;
its historical task lists do not authorize additional work.

## Selected batch — RCN repair, documentation and stability assessment

The owner selected review items 1, 2 and 3 on October 17 and authorized push.
No additional region, concurrent matrix, P4 hosting migration, automatic KW
acquisition, historical identity rewrite or manual workflow dispatch is selected.

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

## Verified production baseline — before this push

Main: `f5b7830df9d7f1cc7e79561608e0e6caf567d660`. Both regional publications
are dated October 16; no production data branch was changed during this audit.

| Evidence | Śląskie | Opolskie |
|---|---|---|
| Frozen data ref | `7e2afd37c64336b1bf1d397ff300aebb2773affa` | `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b` |
| Cards / raw offers | 31,042 / 52,187 | 3,665 / 5,441 |
| Scraper runtime | 78.1 min | 11.0 min |
| RCN status / retained snapshot | degraded / Oct 3 | degraded / Sep 28 |
| Archive checkpoint | complete, Oct 15, 49,854 records | complete, Oct 13, 7,822 records |
| Critical photo deferrals / backlog | 0 / 0 | 0 / 0 |

Both complete archive checkpoints have no failed/capped partitions or unfinished
cursor queue. Each frozen branch has exactly 76 files, all passing its regional
allowlist. Małopolskie remains disabled and recoverable at `cba13c7`.
The KW filter's [scrape](https://github.com/110kc3/rentgen-ofert/actions/runs/37736507948)
and [deployment](https://github.com/110kc3/rentgen-ofert/actions/runs/37736507945)
succeeded; the live regional controls and standalone viewer return HTTP 200.
KW acquisition/current-register verification remains in the private project.

## Next accepted checks — after this push

- [ ] Check this push's completed scrape and deployment once next session in
  [Actions](https://github.com/110kc3/rentgen-ofert/actions?query=branch%3Amain).
  Require the offline suite, payload/source/RCN validators and regional staging
  to pass. Confirm the live RCN date, health and source provenance agree with
  the new cache. The push-triggered refresh is Śląskie; Opolskie stays on its
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

**Push verification is pending.** Do not wait/poll after push. There are no
owner-only blockers. Expansion and P4 remain deferred until their gates and
separate selection; completion of this batch does not authorize them.
