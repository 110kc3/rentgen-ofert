# Archive throttling and maintenance verification — 2026-10-03

The owner selected the archive rate-limit fix and completion of maintenance
verification. The working tree was clean at `2aaa2dd1f43e590bace0cc22883a4659d3544d2e`,
matching remote `main`. No additional region, manual workflow dispatch or direct
data-branch change is included.

## Production findings

The latest actual Silesian scrape
[37070054949](https://github.com/110kc3/rentgen-ofert/actions/runs/37070054949)
and [deployment 37078946403](https://github.com/110kc3/rentgen-ofert/actions/runs/37078946403)
succeeded. The deployed data ref is
`a8984a674aeaf7fe96912d343854609676e41e50`, updated October 2 at 23:43:23 UTC:
30,392 cards / 51,999 raw offers, **102.7-minute runtime**, healthy RCN,
3,315 matched properties, 59 benchmark towns, 62 gap pairs and 71 confirmed sales.
All 442 then-current tests and the generated-data publication gate passed.
Critical photo deferrals, unresolved size groups and photo backlog are zero.
Four portals still contribute; OLX remains blocked. The October 3 06:33 UTC
[latest update](https://github.com/110kc3/rentgen-ofert/actions/runs/37103463469)
was an expected Opolskie no-op, not a fresh Silesian scrape.

Archive progress is genuinely persisted and resumed across successful runs:

| Run | Date (UTC) | Maintenance seconds | Pending partitions | Unique cycle records |
|---|---|---:|---:|---:|
| [36864185548](https://github.com/110kc3/rentgen-ofert/actions/runs/36864185548) | Oct 1 afternoon | 257.4 | 108 | 4,383 |
| [36935453050](https://github.com/110kc3/rentgen-ofert/actions/runs/36935453050) | Oct 1 evening | 414.5 | 57 | 10,646 |
| [37005237181](https://github.com/110kc3/rentgen-ofert/actions/runs/37005237181) | Oct 2 afternoon | 627.1 | 56 | 18,010 |
| [37070054949](https://github.com/110kc3/rentgen-ofert/actions/runs/37070054949) | Oct 2 evening | 529.5 | 53 | 25,326 |

The last slice collected 7,316 new archived rows in 285 requests. All 53 remaining
flat partitions then returned **HTTP 429**, stopping the slice before its
900-second budget expired. House traversal has finished. The complete-refresh
date correctly remains September 24; the current cycle began October 1. Before
this fix, any failed partition rotated to the end and every other pending town
was attempted once, even after rate limiting had started. Per-type metadata
contained the errors, but the Actions summary did not surface archive progress
or the stop reason.

Opolskie's first P1 scheduled refresh
[36822082863](https://github.com/110kc3/rentgen-ofert/actions/runs/36822082863)
passed and deployed on October 1. Its data ref
`fe43d8f592b599317dc1527f900adb1f3107e92c` has 3,613 cards / 5,378 raw offers,
**13.7-minute runtime**, healthy September 28 RCN evidence, 189 matches and
6 confirmed sales. Critical photo deferrals are zero; one unresolved size group
remains separate. The next eligible refresh is October 4 at 06:09:26 UTC,
subject to schedule/queue delay. Both frozen data trees contain 76 files, all
within their respective regional storage allowlists.

## Fix

The first archive HTTP 429 now stops the **entire maintenance slice** without
advancing or rotating the refused town/type/page cursor. No remaining town or
property type is probed afterward. Already collected rows and seen IDs are
retained and saved through the existing history-first checkpoint publication.
The next scheduled attempt resumes the refused page. The full current-offer
pass still runs before maintenance; its coverage health remains independent.
There is no new retry loop, long sleep or forced refresh.

Non-throttling behavior is preserved: HTTP 404 finishes that partition; other
request errors rotate and allow other towns to proceed once. Metadata and logs
now identify `rate_limited`, `errors`, `budget` or `complete`. Source-level
archive metadata aggregates the stop reason and failed-request count without
duplicating shared timing/request totals. The Actions summary reports archive
mode, recorded refresh, pending partitions, cycle records, elapsed/budget time
and the stop reason, separately from current-source health. Older cached
archive metadata remains readable.

## Verification and limits

- `.venv/bin/python -m pytest -q`: **451 tests passed**. New cases cover 429
  before and after progress, stopping across towns and both property types,
  current collection preservation, JSON checkpoint round-trip, retrying the
  exact refused page and clearing the throttle reason on completion. HTTP
  404/503 behavior and summary rendering for every stop reason/legacy caches
  are covered. `git diff --check` passes.
- Downloaded only `cache/nol_archive_slaskie.json` from the immutable Silesian
  ref above. Its schema-2 state has 53 pending partitions, 25,326 seen IDs and
  first cursor `flat/sosnowiec/page 75`. Replaying that state with a synthetic
  429 makes **one archive request** and preserves every cursor and seen ID.
  After a real JSON checkpoint save/reload, synthetic successful pages add one
  archived row per partition and then end each partition: 106 requests,
  53 new archived rows, 25,379 total cycle IDs, completed date October 3.
  The original checkpoint is unchanged. This is an offline mechanism test,
  **not evidence that the live archive has completed**.
- No newer completed production scrape was available at the continuation's
  single Actions check. The live Silesian RCN snapshot is still September 26,
  so a fresh weekly WFS pull and its total-run runtime remain unobserved.
  Runtime with partial archive maintenance is verified below the preferred
  150-minute threshold; completion and a fresh RCN pull are separate gates.

## Remaining accepted verification

Item 1 is implemented locally; its push/publication is **pending production
verification**. Item 2 is **partially verified**: archive resumption and P1
Opolskie publication passed, but live archive completion and the next fresh
weekly RCN refresh remain open. Inspect the next completed automatic run once:
first 429 should halt further archive requests; progress must persist; later
successful slices must drain the queue before advancing the refresh date.
Confirm both RCN layers refresh successfully and total runtime remains ≤180
minutes, preferably ≤150. Then assess the existing seven-healthy-day cohort
gate before any expansion. Do not wait/poll after pushing or dispatch a manual
workflow to manufacture acceptance. [TODO.md](../../TODO.md) owns the handoff.
