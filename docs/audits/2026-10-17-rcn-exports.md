# RCN recovery, archive closeout and cohort assessment — 2026-10-17

Codex inspected clean main `f5b7830df9d7f1cc7e79561608e0e6caf567d660`,
then implemented the owner-selected review items 1–3. Scope: RCN ingestion,
affected documentation and the existing stability gate. No new region, manual
workflow dispatch, direct data-branch write or storage deployment was performed.
[TODO.md](../../TODO.md) owns the current queue; older handoffs are historical.

## Frozen production evidence

| Evidence | Śląskie | Opolskie |
|---|---|---|
| Data ref | `7e2afd37c64336b1bf1d397ff300aebb2773affa` | `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b` |
| Publication UTC, October 16 | 22:03:31 | 22:15:19 |
| Cards / raw offers | 31,042 / 52,187 | 3,665 / 5,441 |
| Runtime | 4,687.2 s / 78.1 min | 659.5 s / 11.0 min |
| RCN retained date | October 3 | September 28 |
| Flat / building transactions | 201,022 / 468,317 | 13,426 / 34,356 |
| Matched properties / confirmed archive sales | 3,492 / 82 | 210 / 6 |
| Archive complete date / records | October 15 / 49,854 | October 13 / 7,822 |

The [Silesian scrape](https://github.com/110kc3/rentgen-ofert/actions/runs/38964446875)
and [Opolskie scrape](https://github.com/110kc3/rentgen-ofert/actions/runs/38967378733)
passed 453 tests and published successfully, but their logs explicitly show
failed fresh RCN pulls and fallback to old evidence. Their
[deployments](https://github.com/110kc3/rentgen-ofert/actions/runs/38973456664)
[succeeded](https://github.com/110kc3/rentgen-ofert/actions/runs/38974646550).
Each source retains positive contributions except the already-blocked OLX;
Otodom remains partial. Critical photo deferrals and backlog are zero. The
known two-ad unresolved Opolskie group remains separate.

Both saved schema-2 archive checkpoints are `complete: true`, have no unfinished
cursor queue and have empty failed/capped arrays for both types. Śląskie has
40,234 flat plus 9,620 house records; Opolskie has 5,841 plus 1,981. Each frozen
tree contains exactly 76 files and all pass `region_storage._allowed` for its
own region. This closes the previously pending saved-checkpoint completion and
branch-scope checks, rather than inferring them from green CI. Małopolskie
remains disabled and its retained ref is still `cba13c76081dae29b6c56aeaab26cba5adcbd68a`.

The KW filter commit passed
[scrape 37736507948](https://github.com/110kc3/rentgen-ofert/actions/runs/37736507948)
and [deploy 37736507945](https://github.com/110kc3/rentgen-ofert/actions/runs/37736507945).
Live regional HTML contains the import, explicit-link and KW-only controls;
the standalone viewer returns HTTP 200. This is an HTTP/content check, not a
new interactive browser audit.

## RCN failure and repair

Live WFS requests reproduce both production errors: Śląskie reports 434,641
hits but returns 1,996 members on its first 2,000-row request; Opolskie reports
89,176 but returns 351. Advancing by those 351 returned rows repeats 298 IDs
from the first page. Sorted/alternative request probes also fail to establish
a complete traversal. The underlying server cause is not established; ignoring
its count mismatch or simply accepting a short page would be unsafe.

The service also changed deed dates from scalar text to a temporal property:
`DOK_DATA` contains `gml:timePosition`. Reading only `child.text` discards the
date. The parser now accepts the old scalar encoding and one GML time position;
ambiguous/unsupported nested encodings fail.

The repair retains strict WFS pagination and falls back, on failure, to both
official provincial GeoParquet exports from the same publisher. GUGiK's
[own QGIS client](https://github.com/GlownyUrzadGeodezjiIKartografii/pobierz_dane_GUGiK/blob/main/pobierz_dane_GUGiK_dockwidget.py)
selects this export family for voivodeships. The
[publisher's RCN description](https://www.geoportal.gov.pl/pl/dane/rejestr-cen-nieruchomosci-rcn/)
documents both the WFS and provincial vector downloads.

Each export downloads to a temporary directory, with a 512-MiB limit and
Content-Length verification when supplied. PyArrow validates the Parquet
footer and reads only the transaction matching fields in batches. Required
fields, full footer row count, unique nonnegative feature IDs and the requested
TERYT prefix are checked; only residential buildings enter matching. Distinct
source IDs remain distinct, even when compact deed values coincide. Invalid
nonpositive rounded prices and nonpositive flat areas are excluded as unusable
transactions. Raw exports, geometry and unrelated source fields are not published.

Both candidate layers still pass the existing snapshot validation and 20%
previous-count floor before atomic replacement. A failure in either layer,
download, parsing or save retains the previous complete cache and its date.
An incomplete WFS layer is never combined with an export. Cache/health provenance
retains source URLs, file hashes, bytes, raw row counts and the WFS error.
`fetched` remains the retrieval date; it does not assert that every county
updated its underlying register that day or that the publisher exports are atomic
across both files.

## Local real-source verification

The actual refresh path was run against copies of both frozen caches, with
fresh downloads, snapshot validation and atomic save/reload outside the repo:

| Region | Export rows: flats / all buildings | Usable flat / residential-building deeds | Refresh time |
|---|---|---|---|
| Śląskie | 434,641 / 1,151,982 | 315,432 / 576,596 | 103.8 s |
| Opolskie | 89,176 / 273,649 | 63,494 / 86,224 | 23.7 s |

Both return healthy snapshots dated October 17. Flat export footer row counts
agree with the independently observed provincial WFS hits. The broader source
population changes evidence coverage; its count increase is not an increase in
observed listing sales. These local RCN-only timings do not establish the total
production scraper/runtime gate.

Downloaded export identities (SHA-256; also retained in the candidate cache):

| Region / layer | Bytes | SHA-256 |
|---|---:|---|
| Śląskie flats | 35,129,889 | `7b0b08b2daf5732e059ba3c800a53208b2fbc5ec6851ca68c90de7456358805d` |
| Śląskie buildings | 87,046,617 | `e37bd144dd70f6de68e60b900e962f3b55023697dd789522e7e1e31181b4f4b9` |
| Opolskie flats | 7,273,504 | `f1efbf4cfcd74a2baf438d018ee27de063e3405d26aeaaf4766a2739d2bb5a66` |
| Opolskie buildings | 16,906,829 | `7540e9837bcbaabadb442f88290454cc432936b39c4aeccfd05428463b0b3b68` |

`.venv/bin/python -m pytest -q` passed **476 tests**. Regression coverage
includes old/temporal GML dates, ambiguous dates, nonpositive prices/areas,
valid export reads, residential scope, duplicate IDs, wrong/missing regions,
missing fields, malformed/truncated Parquet, interrupted/oversized downloads,
source provenance on cache reuse, failed second-layer retention and the
unchanged 20% shrinkage gate. Markdown file targets resolve and
`git diff --check` passes.

Frozen-history replay reproduces the published baseline before applying the
fresh snapshot. Only matching/statistics fields were retained in the temporary
replay: observations were reduced to the last positive-price observation used
by gap statistics; gallery hashes/photo URLs were omitted. Decimal JSON numbers
were converted for matching without changing integer IDs. The source histories
and production branches were not written. `ijson` was an audit-only dependency,
not added to runtime requirements.

| Replay | Śląskie | Opolskie |
|---|---|---|
| Frozen history records | 63,943 | 5,110 |
| Matched records, retained cache → fresh export | 3,492 → 3,850 | 210 → 296 |
| Histories with a derived sold claim | 82 → 112 | 6 → 10 |
| Benchmark towns | 66 → 64 | 50 → 56 |
| Ask/deed gap pairs | 70 → 97 | 6 → 10 |
| Local replay time | 319.7 s | 14.6 s |

Both replay outputs pass `validate_rcn` against the retained-cache baseline:
healthy fresh snapshot dates/counts, nonempty benchmarks and preservation of
previously positive matching/sale/gap evidence. These are comparisons on frozen
histories, not forecasts of the next live scrape or independent confirmation of
individual sales. Benchmark counts are not forced to rise; the Silesian result
has two fewer benchmark towns despite broader transaction coverage. Full live
payload validation and total production runtime remain pending.

## Cohort assessment and handoff

The last three automatic Opolskie attempts have successful publication status:
[October 10](https://github.com/110kc3/rentgen-ofert/actions/runs/38076455489),
[October 13](https://github.com/110kc3/rentgen-ofert/actions/runs/38469114078)
and [October 16](https://github.com/110kc3/rentgen-ofert/actions/runs/38967378733).
All three logs show the same class of count mismatch and use the September 28
cache. The 72-hour scheduler operates, but these are not healthy RCN cycles.
**The seven-day / three-cycle gate fails and remains open.**

Check this push's completed scrape/deploy once next session. The ordinary push
refreshes Śląskie; Opolskie must recover on its existing automatic cadence.
Confirm live healthy snapshots/provenance and reconcile changed derived claims,
then begin at least seven healthy days and three healthy automatic Opolskie
cycles. Require source continuity, zero critical photo deferrals/backlog,
checkpoint persistence, isolated branches, no-op behavior and ordinary plus
fresh-maintenance runtimes ≤180 minutes (preferred ≤150). Investigate failures
and restart after recovery. No manual dispatch or waiting/polling after push.

Production acceptance of this repair remains pending. The selected stability
assessment is complete; elapsed healthy production observation cannot be
substituted by local verification. No expansion or P4 migration is selected.

Audit files, exports and replay inputs remain in `/tmp/rentgen-rcn-20261017/`;
they are not production inputs or committed artifacts.

## Production follow-up — October 17

Commit `6fbb266865cc58d82d934bdfd9206c07fe48525f` passed
[scrape 38982350853](https://github.com/110kc3/rentgen-ofert/actions/runs/38982350853)
and [deploy 38988650534](https://github.com/110kc3/rentgen-ofert/actions/runs/38988650534).
The run passed all 476 tests and publication validation, then updated only
`data-slaskie` to `09aa75c472428a8a9378a34b1f8d686284118b08`. Its 76-file tree
passes the regional allowlist. Live metadata and export hashes agree with the
fresh local source: 315,432 flat / 576,596 building deeds, healthy RCN, 3,850
matched properties and 112 confirmed archive sales. All four contributing
sources remain, critical photo deferrals/backlog and unresolved groups are zero,
and the complete archive checkpoint remains dated October 15.

Total runtime was **4,691.0 seconds / 78.2 minutes**, including 289.7 seconds
of RCN refresh/matching: below the preferred 150-minute gate. The cache date is
October 16 because the job began before midnight; the logs place retrieval
after midnight October 17. This verifies Silesian repair/publication/runtime.

Opolskie is still unchanged at `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b` and
retains degraded September 28 evidence. The read-only scheduler decision skips
until **October 19 22:15:19 UTC**, subject to its hourly tick and scheduling/
queue delays. No workflow was dispatched. Both-region recovery and the seven-day
cohort window remain open; its repaired two-region clock has not started.
The owner subsequently selected the measured index/archive P4 slice; see
[the payload contract and measurements](../PAYLOAD.md) and the current queue.
