# Identity and runtime P1s — 2026-09-29

Scope selected by the owner: pull/check the latest production state and implement
the two September-review P1s (identity normalization and weekly runtime). `main`
was already at `0c6db2cd38b794744f7ff71d05bda6ebcfea2068` after a fast-forward-only
pull. No historical property splitting, new region, manual workflow dispatch or
manual data-branch rewrite is included.

## P0 production recovery is verified

The P0 push-triggered update
[36277340006](https://github.com/110kc3/rentgen-ofert/actions/runs/36277340006)
passed 396 tests, recovered the last-good cache, then completed a fresh WFS
snapshot with **200,895 flat / 473,617 building transactions**. It restored
2,985 matches and passed publication validation. The resulting data deployment
[36283978359](https://github.com/110kc3/rentgen-ofert/actions/runs/36283978359)
succeeded. This resolves the September 26 audit's uncertainty about completing
the fresh building layer.

The latest actual Silesian scrape checked was
[36496055900](https://github.com/110kc3/rentgen-ofert/actions/runs/36496055900),
with successful data deployment
[36505568591](https://github.com/110kc3/rentgen-ofert/actions/runs/36505568591).
Subsequent hourly no-op checks are not counted as scrapes. Frozen publications:

| Evidence | Śląskie | Opolskie |
|---|---|---|
| Data ref | `3d4653af51c789b96ffb0e7d14de2ba91159d033` | `024ec06d559c9630be2af5993a430aacbb6780c8` |
| Published UTC | Sep 29 00:56:44 | Sep 28 01:16:17 |
| Cards / raw offers | 30,544 / 52,009 | 3,705 / 5,420 |
| RCN health / snapshot date | healthy / Sep 26 | healthy / Sep 28 |
| Flat / building transactions | 200,895 / 473,617 | 13,426 / 34,356 |
| Matched properties | 3,027 | 160 |
| Benchmark towns / gap pairs / confirmed sales | 60 / 51 / 55 | 50 / 5 / 5 |
| Ordinary runtime | 111.3 min | 28.5 min |

These are observed pre-P1 results, not proof of the new implementation. Source
coverage remains partial, including OLX's blocked probe and portal serving caps.

## Identity behavior

- Share exact floor parsing across photo identity and RCN: Otodom `FIRST`,
  `GROUND`, `SECOND`…`TENTH`, OLX `floor_0`, `floor_3`, numeric floors and existing
  Polish ground/basement labels. Otodom emits recognized floors as integers;
  unknown raw enums stay intact. Ranges and attic labels do not invent a floor.
  The RCN scorer retains its existing floor/storey tolerance `(floor, floor+1)`.
- Remove trailing recognized county labels from Gratka/Morizon breadcrumbs,
  leaving the actual preceding locality. The allowlist covers the two enabled
  regions; it is checked against the
  [ZPE administrative map](https://zpe.gov.pl/a/mapa-administracyjna-polski/D14B88qSv).
  County-only breadcrumbs become unknown, never the county seat. Other unknown
  names remain unchanged. Old county-labeled history is not automatically remapped.
- Separate unambiguous trailing building numbers from street names. Formatting
  variants join when photo evidence agrees; known building-number disagreements
  veto merging and RCN street matches. Preserve street numerals (`11 Listopada`
  differs from `3 Listopada`), terminal years, military-unit numbers, and building
  separators (`13/2` differs from `132`). Explicit address numbers take precedence.
- Existing exact portal-ID twins and history's exact-URL fallback remain intact.
  Known town/street/room/floor contradictions still veto photo identity, including
  contradictions across all members of a cluster. No old record is split merely
  because the matching rules changed.

## Runtime behavior

The published `history_prepare` phase was 1,654.7 seconds (27.6 minutes), but its
old timer also included deduplication. A streaming census found 58,022 history
records / 3,810,548 observations and only five currently mergeable URL groups.
This does not support rewriting historical compaction as the first optimization.

Photo clustering and history matching now reject cheap attribute contradictions
before comparing gallery hashes. Hamming distance uses integer `bit_count()`;
address folding/tokenization uses bounded caches. Deduplication gets a separate
`runtime.phases.dedupe` timer, leaving `history_prepare` for load/compact/archive
ingestion. The logical order change is tested independently of identity changes.

N-online always finishes the ordinary current-stock pass first. Due archive work
then receives a **15-minute maintenance budget** with a separate no-retry HTTP
session and request timeouts bounded by the remaining budget. A schema-2 regional
checkpoint retains pending town/type/page cursors and seen portal IDs. It resumes
on each subsequent run until finished; only completion advances the seven-day
refresh cadence. Failed pages retain their cursor and rotate behind other towns.
Current URLs are not emitted again as archived URLs. Schema-1 states remain
readable; corrupt/foreign-region checkpoints fail closed.

`archive_harvest` exposes partial/completed mode, pending partitions, cycle record
count, elapsed time, budget and requests. During a partial cycle the last completed
refresh date/count remain distinct from current cycle progress. Checkpoints are
saved after history is saved and published together through the existing regional
transaction. `force` also respects the budget; `skip` pauses without dropping
progress. No workflow or regional staging scope changed.

A request/parse already in flight can overrun the deadline; this is a maintenance
budget, not a hard wall-clock process kill. Offset pages may shift between runs,
so an archive cycle is a best-effort traversal, not a frozen source snapshot.
Existing history remains retained. Complete stock collection means completing the
ordinary bounded pass, not claiming every listing on a capped/blocked portal.

## Verification

- `.venv/bin/python -m pytest -q`: **442 passed**. New cases cover floor enums
  including OLX, county breadcrumbs, building-number contradictions, photo identity,
  RCN matching, exact bit distances, interrupted/resumed archive work, duplicate
  pages, current/archive URL separation, regional isolation, corrupt states and
  bounded request timeouts. Existing source-continuity and regional workflow tests
  also pass. `git diff --check` passes.
- Frozen-history RCN replay reproduces the published baseline exactly: **3,027
  matched records / 4,869 events / 55 records with a sold claim**. New rules
  yield **3,214 matched records / 5,096 events / 67 records with a sold claim**.
  Of the matched records, 1,044 are newly matched, 857 lose all previous claims,
  and 350 retained records have changed events. This is evidence reconciliation,
  not a monotonic count-recovery goal. The original 58,022 records are retained.
  All **seven removed sold claims** fail a now-known exact-floor contradiction.
  Of **19 added sold claims**, 18 gain room/floor evidence previously hidden by
  Otodom enums and one becomes unambiguous when incompatible floors are rejected.
  Each added deed agrees with the normalized floor under the existing storey
  tolerance. These are derived history claims; no new site payload was published
  locally and the post-push archive count remains to be observed.
- Photo benchmark: the first 250 records from the largest exact-size/room bucket
  in the frozen history (1,780 gallery hashes) produced the same **242 groups**
  with exactly the same record membership. Holding the new identity rules fixed,
  the old photo-first/string-bit implementation took **2.887 s**, versus
  **0.066 s** for contradiction-first/integer-bit matching. This is a local kernel
  sample, not an end-to-end runner prediction.

Replay inputs were extracted with `git show <frozen-ref>:<path>` into a temporary
directory: `site/data/slaskie/history.json.gz` and `cache/rcn_slaskie.json.gz`.
A streaming `ijson` pass retained every history field except `observations` and
`photo_urls`, neither of which the RCN matcher reads. Integer gallery hashes
remained arbitrary-precision integers. This reduced memory use without changing
matching inputs; no production history was edited. `ijson` was a temporary audit
dependency, not added to the project. `rcn.match(records, rcn.load_snapshot(path))`
ran in separate Python processes against the baseline package archived from
`0c6db2c` and the working package, then compared each record's derived `sales`.
For the photo benchmark, load the baseline `normalize.py` with the current
`compatible` predicate, build listing dictionaries from history snapshots and
`hashes`, and compare sorted group membership before timing interpretation.

## Original production-verification handoff

The impending P1 push and its data publication/deployment remain **pending**.
Check the commit once next session; do not wait or poll CI after pushing. Inspect
current source continuity, RCN health and changed claims, new dedupe timing,
archive cursor progress across runs, eventual completion and sibling-region
preservation. Observe an ordinary and weekly/RCN-refresh run at **≤180 minutes,
preferably ≤150**. Local speedup and a bounded archive slice do not establish that
end-to-end target. The seven-healthy-day cohort gate remains open; no expansion
is selected. The canonical next check lives in [TODO.md](../../TODO.md).

## Production follow-up — September 29

Checked `31d271cddae989c42b2bbb76aa41ff759d315063` once on continuation. The
push-triggered scrape [36538655200](https://github.com/110kc3/rentgen-ofert/actions/runs/36538655200)
and its data deployment [36547243890](https://github.com/110kc3/rentgen-ofert/actions/runs/36547243890)
succeeded. The subsequent scheduled Silesian scrape
[36568321119](https://github.com/110kc3/rentgen-ofert/actions/runs/36568321119)
and deployment [36579144419](https://github.com/110kc3/rentgen-ofert/actions/runs/36579144419)
also succeeded. Both scrapes passed 442 tests and full generated-payload
validation, including the compressed history, before publication.

The latest frozen ref is `ce7c68a6e99ffd4647c77d1533c45e62ab904e58`, published
at 13:58:06 UTC. The live metadata/index/manifest agree: **30,367 cards / 52,024
raw offers**, manifest version `4eeece3a604284fc577e`, healthy RCN with the same
September 26 layer counts, **3,232 matches / 60 benchmark towns / 59 gap pairs /
67 confirmed sales**. The deployed listing and statistics routes return HTTP 200
for both regions. This follow-up checks live HTTP/data and recorded CI; it does
not claim a new interactive browser audit.

| Metric | Pre-P1 publication | Latest P1 publication |
|---|---:|---:|
| Total scraper runtime | 111.3 min | 88.9 min |
| Dedupe + history preparation | 1,654.7 s (combined timer) | 270.0 + 8.4 = 278.4 s |
| History update | 444.7 s | 44.7 s |
| Current Otodom | 16,042 | 16,088 |
| Current Gratka | 12,560 | 12,542 |
| Current Morizon | 12,559 | 12,539 |
| Current n-online | 10,848 | 10,855 |
| Recognized county labels used as current locality | 2,672 | 0 |

The baseline Otodom total is derived from the pre-P1 source counts, and all
four positive sources pass `validate_source_continuity` with no override or
regressions. OLX remains blocked. Critical photo deferrals, unresolved size
groups and photo backlog are zero. County-label counts compare the frozen
current indexes with the shared allowlist, not old historical snapshots.
A live scraper changes inputs between runs; these observed timings are not a
controlled performance experiment, but the ordinary runtime meets the preferred
150-minute gate.

All 76 files in the new Silesian data tree pass `region_storage._allowed` for
Śląskie. Opolskie remains byte-identical at ref
`024ec06d559c9630be2af5993a430aacbb6780c8`; its live version is
`213e3a66272095f960ae` with 3,705 cards. Hourly check
[36543243297](https://github.com/110kc3/rentgen-ofert/actions/runs/36543243297)
correctly skipped portal work and logged its next eligible refresh as
**2026-10-01 01:16:17 UTC**. Queue time on that run must not be mistaken for a
37-minute Opolskie scrape.

**Remaining acceptance:** both P1 scrapes used cached archives, last refreshed
September 24. The bounded archive cycle is first due October 1; there is no
production evidence yet for partial checkpoints, resumption or completion.
The next weekly RCN refresh is due October 3 from the September 26 snapshot.
These maintenance runtimes and the next P1 Opolskie publication remain pending,
as does the seven-healthy-day cohort gate. No manual workflow was dispatched.
The documentation follow-up push has no new scraper changes; any resulting
Actions verification remains pending, with no post-push waiting or polling.
