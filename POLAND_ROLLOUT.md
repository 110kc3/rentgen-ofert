# Whole-Poland rollout: status and next tasks

> **Code update 2026-09-06:** all seven review fixes are implemented locally
> (316 offline tests, including an eight-case browser loading runner). P1
> commit `490be3f` passed its recorded scrape `34004170487` and direct deploy
> `34004170501`; its changed identity/sale counts still need semantic audit.
> The P2 follow-up updates daily price observations, makes browser failures
> retryable, and versions the index plus details together in manifest schema 2.
> Its impending `main` push remains pending production verification. Check
> that commit's scrape/deploy once next session. The owning handoff is in
> [TODO.md](TODO.md#remaining-rollout-and-architecture-work).
> All seven review defects are locally closed; review severities do not rename
> rollout phases. Serial 72-hour Opolskie cadence and the P4 compact-index,
> archive-sharding, versioned-storage and rollback TODOs remain outstanding.
> No cadence, region enablement, hosting or Tailscale change was made.
> The following dated production audit predates the review fixes.

> Audited: 2026-09-04. Production is current through warm Opolskie run
> `33855228296` and deploy `33856444810`; scheduled Śląskie run `33804201172`
> remains its current regional ref, and Otodom is above the approved
> 15.8–15.9k floor, runtime is 90.8 minutes, and photo deferrals/unresolved
> groups remain zero. P0, P1 and the manual P2 pilot are accepted. The disabled
> Małopolskie pilot remains recoverable but absent from the artifact. Corrected
> P3 scout `33497077221` selected Opolskie; cold run `33504082916` passed its
> audit and published the isolated pilot in `33514004545`. Warm run
> `33855228296` passed the exit gate in 14.3 minutes with stable sources, zero
> deferrals/backlog and exact archive/RCN cache reuse. Its automatic deploy is
> `33856444810`. The serial 72-hour cadence is the next implementation slice;
> no matrix or concurrent portal access is authorized.
> This is the current source of truth for the nationwide rollout. `TODO.md`
> retains the detailed development diary and older measurements.

## Executive status

**The product is genuinely region-aware, P0 is accepted, and Opolskie's
cold/warm pilot passed; the project is still not ready for a 16-voivodeship
schedule.** Guarded Śląskie runs retain the positive source baseline with normal
count drift. Małopolskie remains recoverable but disabled. Opolskie's 29.9-minute
cold and 14.3-minute warm scrapes proved source stability, convergence and
isolation. The next slice is its selected serial 72-hour schedule, not a matrix.

| Area | Status | Evidence / gap |
|---|---|---|
| Region-scoped scraper output and caches | Ready | `site/data/<region>`, regional caches and exact branch staging are implemented. |
| Canonical 16-region configuration | Proven live | `site/regions.json` is validated and owns Polish forms, TERYT, cadence, anchor and explicit portal slugs; the complete Śląskie path ran end to end. |
| One data branch per region | Proven for three | `data-slaskie`, `data-malopolskie` and `data-opolskie` are isolated single-commit data/cache refs; each pilot touched only its branch. |
| Deploy overlay for multiple region branches | Proven live for three refs / two enabled regions | Deploys overlay all isolated refs, then publish only enabled Śląskie and Opolskie; disabled Małopolskie remains recoverable and absent. |
| Portal coverage | Collection floor and continuity accepted | Corrected Otodom floor is 15.8–15.9k; subsequent guarded schedules retain it and the latest yielded 16,015. OLX's one-probe blocked policy remains stable. |
| Coverage KPI | Truthful and protective | Schema v2 reports source state; P0.7 compares it with preserved metadata before push. Synthetic 15,949→0 rejection plus repeated production passes cover the failure and positive paths. |
| Per-region runtime | Opolskie accepted | Latest Śląskie took 90.8 minutes, corrective Małopolskie 110.9, cold Opolskie 29.9 and warm Opolskie 14.3; all pass 150 preferred / 180 required. |
| Region picker and durable regional URLs | Proven live for two enabled regions | National picker, stable listing/statistics paths, scoped state and discovery expose Śląskie plus the data-backed Opolskie pilot. |
| Per-region metadata / OG / sitemap / llms.txt | Proven live | Canonical/JSON-LD documents parse and discovery contains only data-backed published regions. |
| CI region matrix / cadence | 72-hour serial contract selected; implementation next | Śląskie alone remains scheduled today. Opolskie passed manual validation and is ready for a serial 72-hour schedule; no concurrent portal access is enabled. |
| Nationwide data hosting | Not decided | Current Śląskie + Opolskie data serves about 125.4 MiB; the larger retained Małopolskie measurement keeps the nationwide capacity warning intact. |

**Rollout decision:** do not add a scheduled second region. P0/P1 and the manual
pilot are accepted. `malopolskie` is disabled and retained as a recoverable
branch. Cold and warm Opolskie are audited and accepted for the selected serial
72-hour cadence. This authorizes only that one non-concurrent schedule; cohort
expansion still waits for seven healthy days.

## Production snapshot

### Repository and deployment

- The production-validated regional architecture is `4131f03` (`feat: build
  regional catalog and stable pages`), on top of `701795e` (regional-boundary
  enforcement), `60bea36` (cross-category duplicate rejection) and `53ce632`
  (within-page portal clone rejection). Continuity guard `cc9a591` is now also
  production-validated on its positive path.
- [Deploy run 33812434670](https://github.com/110kc3/rentgen-ofert/actions/runs/33812434670)
  published the latest two-region artifact after scheduled Śląskie refresh
  `33804201172`. It retained Opolskie's pilot tree and excluded disabled
  Małopolskie.
- Latest Śląskie data is **2026-09-03**, **28,579** unique properties from
  **51,943** raw listings. Otodom contributes 16,015, and OLX remains blocked
  after one bounded probe. The scrape took 90.8 minutes, had zero photo
  deferrals/unresolved groups and advanced `data-slaskie` to `cec3bea`.
- Cold Opolskie data is **2026-09-01**, **3,563** unique properties from
  **5,480** raw listings. Its 29.9-minute scrape created only single-commit
  `data-opolskie` at `e0f29a6`; deploy `33514004545` first published its 7.1-MiB
  served tree beside Śląskie. Warm run `33855228296` advanced it to **3,556**
  from **5,462** at `ee1bf78` and passed the exit gate in 14.3 minutes.
- Pilot Małopolskie data remains recoverable at `data-malopolskie` commit
  `cba13c7`: **32,132** from **63,596**, with four contributing sources and OLX
  blocked. Its catalog entry is disabled, and the live audit confirmed that
  only its artifact/discovery copy disappeared.
- The P1/pilot scrapes ran **224 offline tests before portal work**; queue and
  first warm validation ran the expanded **230-test** gate. The cover-path
  slice expanded it to **235 tests**; this safety slice expands it to **244
  tests** and schema-3 photo arithmetic. P0.7 expands the current suite to
  **255 tests**, including continuity transitions and workflow/deploy order.
  The P3 scout slice expanded the suite to **264 tests**, including
  aggregate parser, request/runtime-budget, source-cutoff and manual-workflow
  contracts. The audited slug/ranking correction expands the current suite to
  **267 tests**.
  The post-generation validator protects every production branch push.

### Latest completed validation runs

The corrected baselines, archive sequence, regional release and photo-safety
iterations all passed pipeline validation and deployed. The first Małopolskie
warm row failed the stricter P2 gate; its corrective row passed. The Otodom
outage row exposed P0.7, then three guarded rows restored and retained the
healthy source floor:

| Run | Trigger | Scrape runtime | Result | Unique / raw |
|---|---|---:|---|---:|
| [32967543284](https://github.com/110kc3/rentgen-ofert/actions/runs/32967543284) | push | 90.0 min | success; deploy `32976169826` | 30,862 / 51,937 |
| [33004188553](https://github.com/110kc3/rentgen-ofert/actions/runs/33004188553) | manual | about 89 min | success; deploy `33011950180` | 30,794 / 51,880 |
| [33007455916](https://github.com/110kc3/rentgen-ofert/actions/runs/33007455916) | schedule | 85.5 min | success; deploy `33018656594` | 30,761 / 51,883 |
| [33047120282](https://github.com/110kc3/rentgen-ofert/actions/runs/33047120282) | forced archive | 177.4 min | success; deploy `33060020329` | 30,781 / 51,906 |
| [33072698054](https://github.com/110kc3/rentgen-ofert/actions/runs/33072698054) | active-only follow-up | 79.6 min | success; deploy `33079583960` | 30,684 / 51,754 |
| [33082048365](https://github.com/110kc3/rentgen-ofert/actions/runs/33082048365) | P1 push | 92.1 min | success; deploy `33090688420` | 30,763 / 51,890 |
| [33098667425](https://github.com/110kc3/rentgen-ofert/actions/runs/33098667425) | Śląskie schedule | 110.7 min | success; deploy `33108035112` | 30,534 / 51,108 |
| [33098785162](https://github.com/110kc3/rentgen-ofert/actions/runs/33098785162) | Małopolskie cold manual | 246.5 min | success; deploy `33126428927` | 40,811 / 61,883 |
| [33135609107](https://github.com/110kc3/rentgen-ofert/actions/runs/33135609107) | photo-queue push | 92.0 min | success; deploy `33144201326` | 30,591 / 51,708 |
| [33161251008](https://github.com/110kc3/rentgen-ofert/actions/runs/33161251008) | Małopolskie warm manual | 203.1 min | CI success, **P2 rejected**; deploy `33174768425` | 33,358 / 63,602 |
| [33188821781](https://github.com/110kc3/rentgen-ofert/actions/runs/33188821781) | cover-path push | about 87.9 min | success | — |
| [33199167100](https://github.com/110kc3/rentgen-ofert/actions/runs/33199167100) | Śląskie schedule | 91.8 min | success; deploy `33206145269` | 30,752 / 51,874 |
| [33242734428](https://github.com/110kc3/rentgen-ofert/actions/runs/33242734428) | schema-3 push | — | success; deploy `33246807232` | Śląskie validation passed |
| [33252714173](https://github.com/110kc3/rentgen-ofert/actions/runs/33252714173) | Śląskie schedule | 89.8 min | success; deploy `33256536544` | 28,253 / 51,810 |
| [33257448934](https://github.com/110kc3/rentgen-ofert/actions/runs/33257448934) | Małopolskie corrective manual | 110.9 min | **P2 accepted**; deploy `33262428730` | 32,132 / 63,596 |
| [33274226173](https://github.com/110kc3/rentgen-ofert/actions/runs/33274226173) | Śląskie schedule | 73.3 min | CI success, **policy failure**; deploy `33277384177` | 19,352 / 35,452 |
| [33299512978](https://github.com/110kc3/rentgen-ofert/actions/runs/33299512978) | continuity-guard push | 91.2 min | success; deploy `33303224401` | 28,222 / 51,767 |
| [33309354137](https://github.com/110kc3/rentgen-ofert/actions/runs/33309354137) | Śląskie schedule | 93.3 min | success; deploy `33313477447` | 28,207 / 51,738 |
| [33334689642](https://github.com/110kc3/rentgen-ofert/actions/runs/33334689642) | Śląskie schedule | 87.6 min | **P0 accepted**; deploy `33338750925` | 28,268 / 51,831 |
| [33348260244](https://github.com/110kc3/rentgen-ofert/actions/runs/33348260244) | closeout push | 95.4 min | success; deploy `33353312262` | 28,277 / 51,826 |
| [33395659119](https://github.com/110kc3/rentgen-ofert/actions/runs/33395659119) | Śląskie schedule | 91.7 min | success; deploy `33404452902` | 28,351 / 51,845 |
| [33437016380](https://github.com/110kc3/rentgen-ofert/actions/runs/33437016380) | scout-correction push | 88.0 min | success; deploy `33444623824` | 28,418 / 51,972 |
| [33447269769](https://github.com/110kc3/rentgen-ofert/actions/runs/33447269769) | Śląskie schedule | 84.2 min | success; deploy `33453345840` | 28,395 / 51,939 |
| [33504082916](https://github.com/110kc3/rentgen-ofert/actions/runs/33504082916) | Opolskie cold manual | 29.9 min | cold accepted for warm; deploy `33514004545` | 3,563 / 5,480 |
| [33804201172](https://github.com/110kc3/rentgen-ofert/actions/runs/33804201172) | Śląskie schedule | 90.8 min | success; deploy `33812434670` | 28,579 / 51,943 |
| [33855228296](https://github.com/110kc3/rentgen-ofert/actions/runs/33855228296) | Opolskie warm manual | 14.3 min | **pilot accepted**; deploy `33856444810` | 3,556 / 5,462 |

### Cold Opolskie pilot evidence

Manual run `33504082916` was dispatched with the default archive/RCN settings,
waited behind the serialized Śląskie scrape and executed from 13:01–13:32 UTC.
It passed all 267 offline tests before portal traffic, validated 71 generated
JSON files / 7.1 MiB served, and completed the scrape itself in **29.9
minutes**.

| Source | Current kept | Search evidence | Runtime |
|---|---:|---|---:|
| Otodom | 1,923 | 34/34 successful requests; houses 98.4%, flats partial at 75.6%, 84.3% overall | 1.4 min |
| OLX | 0 | one Opolskie house-root request, HTTP 403, then synthetic flat block | 0.1 min |
| Gratka | 964 | 29 pages, healthy, 99.8% of 966 stated | 0.9 min |
| Morizon | 964 | 29 pages, healthy, 99.8% of 966 stated | 1.0 min |
| nieruchomości-online | 1,629 | 446 pages across 60 derived towns; 8,029 archived rows; no failed/capped/missing town | 17.0 min |

The 5.5-minute cold photo phase resolved 4,026/4,029 correctness-critical ads,
with zero critical/history deferrals and zero persistent backlog. Three ads had
no hash; one exact-size pair remained unresolved and was safely kept separate
because heuristic fallback was disabled. This is a convergence observation for
the warm run, not evidence of a false merge.

Regional boundaries and publication passed. RCN requested TERYT `16*`, stored
13,022 flat plus 33,261 building deeds and matched 222 properties. Geo located
3,105/3,563 properties and added exactly 500 `16|...` keys; no geocoded point
fell outside the broad regional bounds, and one listing lacked a locality. The
new root commit `e0f29a6` contains exactly the 76 allowed paths and no regional
tree except `site/data/opolskie`; neither sibling data ref moved. Its 9.8-MiB
branch comprises 7.8 MiB regional data (0.8 MiB pipeline-only history), 7.1 MiB
served and 1.9 MiB caches.

Deploy `33514004545` overlaid Małopolskie, Opolskie and Śląskie refs, then
correctly published only the two enabled regions. The 15.6-MiB compressed Pages
artifact deployed on the first attempt. Live picker/catalog counts, both
Opolskie canonical routes, sitemap, `llms.txt` and JSON data return the audited
3,563 count; disabled Małopolskie data remains 404. Subsequent Śląskie deploys
retain Opolskie. Cold Opolskie is accepted for a warm pass, while its partial
Otodom-flat floor and unresolved safe pair remain explicit warm audit points.

### Warm Opolskie evidence — pilot gate accepted

Active-only run `33855228296` executed from 08:49–09:03 UTC on `dc0abb1`, with
`nol_archive=skip`. Its 859.2-second scrape (**14.3 minutes**) passed the
267-test pre-request gate, previous-publication source continuity and generated
data validation. It produced 3,556 unique properties from 5,462 raw rows and
served 7.3 MiB. Relative to cold, source movement was ordinary: Otodom
1,923→1,935, Gratka 964→959, Morizon 964→959 and n-online 1,629→1,609.
Otodom made 34/34 successful requests; houses stayed healthy at 98.6%, flats
stayed partial at 75.9%, and overall coverage was 84.6%. Gratka/Morizon remained
healthy at 99.8%, n-online remained healthy, and OLX repeated one bounded 403.

Photos converged well inside every bound. The phase took 45.6 seconds, reused
4,207 cached results and fetched 361. Of 4,012 critical ads, 4,009 had hashes
and three did not; critical/history deferrals and persistent backlog were zero.
The same one exact-size pair remained unresolved and therefore separate, with
heuristic fallback disabled. A residual unresolved pair is correctness-safe and
does not violate the explicit exit gate, which requires zero critical
deferrals, not a forced identity decision.

The active-only contract is byte-proven: archive cache blob `a970bb2` retained
the complete 2026-09-01 / 8,029-row state and RCN blob `1074a20` was identical
to cold. All 60 n-online towns completed for each type in 291 current-only
pages, with zero archive rows entering the result. The derived town set stayed
at 60 while replacing one changing sitemap locality, which is expected source
drift rather than a regional leak. RCN reused 13,022 flat / 33,261 building
deeds and matches rose 222→235. Geo added another 500 region-scoped keys (1,000
`16|...` total), located 3,104/3,556 properties, and again produced no point
outside the broad Opolskie bounds; one listing lacks a locality.

The run staged exactly 76 paths and force-refreshed only the one-root-commit
`data-opolskie` branch to `ee1bf78`. `data-slaskie` stayed at `cec3bea` and
`data-malopolskie` at `cba13c7`. The warm branch is 10.3 MiB, regional data 8.2
MiB including 0.9 MiB pipeline history, served data 7.3 MiB and caches 2.0 MiB.
Automatic deploy `33856444810` overlaid all three refs, published exactly the
two enabled regions in a 15.7-MiB compressed artifact and succeeded on its
first attempt. Live metadata/catalog, both Opolskie canonical routes, sitemap
and `llms.txt` expose the warm 3,556 count; disabled Małopolskie remains 404.

This accepts the Opolskie cold/warm exit gate: stable explained counts,
truthful source health, zero correctness deferrals/backlog, photos below 60
minutes, total runtime below both 150/180-minute bounds, immutable skipped
caches and exact branch isolation. Opolskie may now receive the selected serial
72-hour cadence. No concurrent matrix or next-region cohort is authorized;
seven healthy days come first.

### Cold Małopolskie pilot evidence

The manual workflow was created at 17:30 UTC, waited behind the serialized
Śląskie run, and executed from 19:21–23:28 UTC. It passed the offline gate,
validated 71 generated JSON files, pushed new isolated branch `data-malopolskie`
at `311f875`, and triggered the successful two-region deploy. The branch is
98.8 MiB; `site/data/malopolskie` is 86.4 MiB including the pipeline-only
history and 79.6 MiB after that file is removed for Pages.

| Source | Current kept | Search evidence | Runtime |
|---|---:|---|---:|
| Otodom | 12,539 | 253 pages; houses healthy, flats partial at page 200/212; 67.3% overall | 11.3 min |
| OLX | 0 | one Małopolskie house-root request, HTTP 403, then synthetic flat block | 0.1 min |
| Gratka | 20,032 | 777 pages, healthy, 99.9% of 20,047 stated | 31.4 min |
| Morizon | 18,377 | 722 pages, partial; one 1.0–1.5M flat band timed out after 26 pages | 55.4 min |
| nieruchomości-online | 10,935 | 837 pages across 60 derived towns; 14,429 archive rows; only Kraków flats capped | 34.1 min |

The regional plumbing behaved correctly: every successful portal used its
Małopolskie root/town path, OLX's rejected URL named `malopolskie`, n-online's
derived list contains 60 regional towns, RCN requested TERYT `12*`, and geo
wrote exactly 500 new `12|…` keys. No obvious Śląskie city leaked into the
40,811-row locality inventory; five Gratka rows have no locality and several
portal rows use a powiat adjective as their fallback, so locality and geo still
need the corrective convergence gate rather than a blanket “complete” claim.

The run's main defect was queue order, not the 90-minute bound. It sent all
12,539 Otodom ads first and recorded 12,381 empty-gallery attempts, then made
14,378 successful Gratka entries; 12,560 Gratka/Morizon twins were already
identified for free. The phase ended with 36,830 ads unattempted, before it
reached untwinned Morizon or n-online. The new queue now:

1. identifies current exact-size and same-town/same-price collisions as the
   correctness queue;
2. orders both queues by free cache hit, oldest persisted deferral,
   never-attempted URL, then prior empty-result retry;
3. stores only truly deferred URLs and their first-wait date in the regional
   phash cache; and
4. publishes queue/outcome/backlog counts in `meta.photos`, validates their
   arithmetic before push, and writes them into the Actions summary.

This preserves the fixed 90-minute publication ceiling while making the warm
gate answerable: zero critical deferrals is distinguishable from “the phase
ended”, and low-yield retries cannot repeatedly stand ahead of untouched work.
Śląskie run `33135609107` production-validated that contract: 41,659 critical
and 1,932 history-only candidates, 43,559 cache hits, 32 fetches, 8,117
ID-settled twins and zero deferrals. Photos took 17.1 seconds, the full scrape
92.0 minutes, all 230 tests and generated-data validation passed, and deploy
`33144201326` matches branch `data-slaskie` at `2282009`.

### First warm Małopolskie evidence — pipeline green, rollout rejected

Manual active-only run `33161251008` executed from 09:54–13:18 UTC on
`2af146c`, refreshed only `data-malopolskie` to `96b1882` and deployed both
trees in `33174768425`. It reused the incomplete 2026-08-27 / 14,429-row
n-online archive state rather than harvesting it again. The n-online archive
and RCN cache hashes stayed byte-identical to the cold branch, and
`data-slaskie` stayed exactly at `2282009`. Region isolation therefore passed
again.

Source collection also stabilized. Morizon's cold timeout recovered to the
full useful inventory and no source suffered a new unexplained loss:

| Source | Cold current | Warm current | Warm evidence | Runtime |
|---|---:|---:|---|---:|
| Otodom | 12,539 | 12,578 | 253 pages; houses healthy, flats partial at page 200/212; 67.6% overall | 12.0 min |
| OLX | 0 | 0 | one correct regional root probe, HTTP 403 | 0.1 min |
| Gratka | 20,032 | 20,048 | 777 pages, healthy, 99.9% | 28.8 min |
| Morizon | 18,377 | 20,051 | 778 pages, zero issues; prior failed band recovered | 32.4 min |
| nieruchomości-online | 10,935 | 10,925 | 574 current-only pages; Kraków flats remained the sole cap | 21.7 min |

The pilot still failed both photo and whole-run gates. Its photo phase consumed
5,806.0 seconds (**96.8 minutes**) despite the configured 90-minute budget, and
the full scrape consumed 12,185.9 seconds (**203.1 minutes**) against the
180-minute ceiling. Of 63,602 raw rows, 48,514 were correctness-critical and
1,916 history-only after 13,172 Morizon twins were settled by portal id. The
phase reused 14,485 cache entries, fetched 13,493 listings and produced hashes
for 27,961, but deferred 22,452 URLs: **20,608 critical** and 1,844 history.

The published 33,358 unique count is 7,453 below the 40,811 cold result. New
Gratka/Morizon/n-online photo evidence necessarily merges duplicates that the
cold run kept separate, so this is not evidence of a source collapse: raw rows
rose by 1,719 and every source was stable or recovered. It is also not yet an
accepted convergence number, because 42.5% of current correctness candidates
still had no decision.

Cache/source inspection identifies why. Positive entries reached 20,089 for
Gratka and 6,878 for untwinned Morizon, but only 887 for n-online. Otodom still
held 12,381 empty entries and only 158 positive hashes. A current Otodom detail
URL returned HTTP 403 while the cover URL already present on its search card
returned HTTP 200 `image/jpeg`. Separately, photo work was still using the
scraper session's five-retry 405/429/5xx ladder; in-flight failures let a best-
effort phase overrun its wall-clock budget by 6.8 minutes.

The corrective contract is therefore narrow and evidence-backed:

1. uncached correctness-critical ads hash the already-scraped card cover once;
2. history-only ads retain full-gallery hashing after correctness work;
3. positive cover-only cache entries carry `scope: cover`, while old/normal
   entries remain backward-compatible gallery evidence;
4. photo requests use a single-attempt session, bounding overrun to in-flight
   request time rather than a retry ladder; and
5. `meta.photos` schema 2, the data validator and Actions summary distinguish
   cover/gallery cache hits and fetches, plus critical with-photo,
   without-photo and deferred outcomes.

A cover match is still positive identity evidence. A cover non-match does not
claim the galleries differ; it conservatively keeps those ads separate, which
is safer than the no-photo size/price fallback. The ordinary push-triggered
Śląskie run `33188821781` and following schedule `33199167100` both
validated the schema-2 contract. The latter finished in 91.8 minutes with a
16.8-second photo phase, zero deferrals and branch `data-slaskie` at
`0e9dc1a`; deploy `33206145269` published 30,752 unique properties from 51,874
raw rows.

The follow-up audit found that zero deferrals did not mean complete evidence.
Of 41,797 critical candidates, 36,690 had hashes and 5,107 did not. Otodom's
cache contained 8,086 negative entries, 7,869 already old enough to suppress a
retry. Legacy negatives had no scope, so an old failed *gallery* attempt could
return before a first attempt at the now-accessible critical cover. Worse, an
exact-size group whose members all remained unresolved could still reach the
loose size/price fallback and merge without photo evidence.

The schema-3 safety contract closes both holes:

1. negative attempts persist `scope: cover`; absence remains the
   backward-compatible gallery scope;
2. switching from a legacy/gallery miss to the cover path resets the miss
   allowance, and a critical listing may bypass that gallery miss once;
3. photo-enabled normalization keeps an all-unresolved exact-size group
   separate, while exact portal-ID twins still merge;
4. only explicit `RENTGEN_PHOTOS=0` enables the old heuristic fallback; and
5. metadata and generated-data validation report unresolved groups/listings
   and enforce that fallback is off whenever photo processing is enabled.

Push run `33242734428` and schedule `33252714173` validated schema 3. The
schedule completed in 89.8 minutes with a 14.9-second photo phase; 41,750 of
41,762 critical ads had hashes, only 12 did not, and unresolved groups,
deferrals, backlog and heuristic fallback were all zero. Branch `data-slaskie`
advanced to `c0fdb96`, and deploy `33256536544` published 28,253 unique
properties from 51,810 raw rows.

### Corrective Małopolskie evidence — pilot gate accepted

Manual active-only run `33257448934` used `nol_archive=skip`, executed from
14:22–16:14 UTC on `c7e21df`, and passed all 244 offline tests plus generated
data validation. Its scrape took 6,655.6 seconds (**110.9 minutes**) against the
180-minute limit. Photos took 543.8 seconds (**9.1 minutes**) against the
60-minute limit: 48,476 of 48,483 critical ads had hashes, only seven did not,
and critical/history deferrals, unresolved groups and backlog were all zero.
The old size/price heuristic remained disabled.

Source inventory was stable relative to the rejected warm run:

| Source | Rejected warm | Corrective warm | Corrective evidence | Runtime |
|---|---:|---:|---|---:|
| Otodom | 12,578 | 12,583 | 253 pages; houses healthy, flats partial at page 200/211; 67.8% overall | 11.7 min |
| OLX | 0 | 0 | one correct regional root probe, HTTP 403 | 0.1 min |
| Gratka | 20,048 | 20,036 | 777 pages, healthy, 99.9% | 27.7 min |
| Morizon | 20,051 | 20,036 | 777 pages, zero issues; 100% against a lower bound | 28.9 min |
| nieruchomości-online | 10,925 | 10,941 | 576 current-only pages; Kraków flats sole cap | 22.5 min |

Raw inventory moved only 63,602→63,596 (-6). Unique properties moved
33,358→32,132 because the number of merged offers increased by exactly 1,220;
the remaining six are the raw-row change. Non-development properties still top
out at eight offers. The phash cache rose from 28,012 to 49,402 positive
entries, its 22,452-URL backlog emptied, and negatives fell from 12,403 to
1,803. This is an explainable evidence-convergence result, not a source
collapse.

The job force-refreshed only `data-malopolskie` to single-commit `cba13c7`: 71
regional paths, no Śląskie path. The explicitly skipped 2026-08-27 / 14,429-row
n-online archive cache and the RCN snapshot kept their exact Git blobs. Branch
contents measure 121.8 MiB total, 106.7 MiB regional data, 10.6 MiB pipeline
history, 96.1 MiB served and 15.1 MiB caches. Deploy `33262428730` published
both trees. The live picker, listing/statistics paths and regional canonicals
returned HTTP 200. Małopolskie now has four locality-less properties,
28,848/32,132 geocoded, 60 n-online towns for each type and no obvious Śląskie
locality leak. The manual pilot exit gate is accepted.

### Audited Śląskie source-health baseline

These are the latest audited schema-v2 values from schedule `33334689642` and
data ref `d124f03`:

| Source | Current kept listings | Reported search state | Assessment |
|---|---:|---|---|
| Otodom | 15,947 | `partial`; 16,259 served in 264/264 successful pages, flats capped at 200 pages | Recovered and stable at the approved 15.8–15.9k floor. |
| OLX | 0 | `blocked`, one real root row, HTTP 403 | Runner/IP block; one probe ends the portal in about three seconds. |
| Gratka | 12,496 | `healthy`, 99.9%; 564 pages, zero issues | Stable useful inventory. |
| Morizon | 12,496 | `partial`, 100% against a lower-bound total; 564 pages, zero issues | Stable useful inventory and no failed partition. |
| nieruchomości-online | 10,892 current | `healthy`; 580 current-only pages; 47,754 archived rows cached from 2026-08-27 | The cache remained available and no archive rows entered the current result. |

Outage run `33274226173` had 19,352 / 35,452 and no Otodom; truthful coverage
still pushed `2460527`, motivating P0.7. Guard push `33299512978` recovered
Otodom to 15,927 and rebuilt 28,222 / 51,767. Two schedules then retained
15,891 and 15,947 while publishing 28,207 / 51,738 and 28,268 / 51,831. All
three ran the 255-test/pre-push continuity path, staged only 76 Śląskie paths
and deployed successfully.

Later schedule `33395659119`, correction push `33437016380` and schedule
`33447269769` kept the same accepted shape. The latest retained Otodom 16,030
through 264/264 successful requests and published 28,395 / 51,939 in 84.2
minutes. Its critical-photo result is 41,822/41,835 with zero deferrals,
backlog or unresolved groups; deploy `33453345840` retained the one-region
artifact.

### What production now proves

- **Per-region branches succeeded.** The first validation run seeded from the
  old shared `data` branch, created `data-slaskie`, and the next run fetched and
  force-refreshed it. The site deployed the new data successfully.
- **The delist change succeeded.** The phase fell from 27–44 minutes in bad
  runs to tens of seconds on the corrected warm path.
- **Schema v2 works live.** Percentages stay bounded, Otodom's page-200 cap is
  explicit, OLX is blocked rather than a clean zero, and Gratka is independently
  healthy.
- **The bounded n-online path succeeded.** Four active runs kept
  **10,864 / 10,860 / 10,862 / 10,826** current rows in 581–582 pages and
  20.5–23.5 minutes, while retaining the cached archive date/count in coverage.
  That is far below the 40-minute gate.
- **The forced n-online path succeeded.** Run `33047120282` served 58,655
  unique rows in 1,817 pages: 10,901 current and 47,754 archived. Its n-online
  phase took 75.3 minutes, the whole scrape took 177.4 minutes, Katowice flats
  were the sole cap, and no town failed. Following run `33072698054` then used
  `current-only` mode, reported zero archive rows, and left the archive cache's
  Git blob and SHA-256 byte-identical. Its n-online phase took 20.5 minutes.
- **The warm photo backlog has converged.** Four corrected active runs completed
  all correctness candidates in roughly 32–74 seconds with no budget
  exhaustion. Schema 3 then processed Małopolskie's corrective queue in 9.1
  minutes with zero deferrals/unresolved groups, so P0.5 and the P2 photo gate
  are accepted.
- **The corrected Otodom recovery succeeded.** Duplicate-category cards,
  repeated portal clones and promoted cards from other voivodeships had
  inflated the earlier 16.3k count. After rejecting them, all three runs kept
  **15,921 / 15,876 / 15,875** valid regional rows with 263/263 successful
  requests and no refusal. P0.2 therefore approves 15.8–15.9k as its explicit
  evidence-backed floor; the forced/follow-up runs retained 15,887/15,866 with
  the same request shape, and schema-3 run `33252714173` retained 15,949. The
  later two-root 403 is a transient source outage that should have retained
  that good branch; experimental bands remain opt-in and additive.
- **The OLX policy succeeded.** All five runs made one house page-one probe,
  received HTTP 403, stopped in seconds, skipped the flat request synthetically
  and published one issue with source health `blocked`. P0.3 is accepted.
- **Payload validation and continuity policy succeeded.** Run `33274226173`
  proved structural validation alone did not
  compare source state with the prior publication. The workflow now preserves
  prior metadata before scraping and the validator makes a categorical
  contributing-source regression red before staging/push, leaving the existing
  branch and success-only Pages deployment untouched. The observed failure is
  fixture-tested; three production runs exercised the recovered/positive path
  with normal drift. P0.7 and P0 are accepted without inducing an outage.
- **The regional product succeeded live.** P1 scrape `33082048365` refreshed
  only `data-slaskie`; its archive cache retained the forced-refresh SHA-256
  and its 500 new geo entries use the `24|…` scope. The shared cache retained
  11,175 pre-P1 unprefixed entries, but production lookup ignores them. Direct
  and automatic deploys exposed one published region, stable canonical paths
  and valid JSON-LD while keeping Małopolskie `noindex`/data-less at that P1
  checkpoint and unknown slugs 404. P2 deploy `33126428927` subsequently
  exposed the second complete tree without changing those invariants.

### Runtime and scheduling capacity

Representative phase times from accepted corrective Małopolskie run
`33257448934`:

| Phase | Time |
|---|---:|
| Otodom | 11.7 min |
| OLX (blocked) | 0.1 min |
| Gratka | 27.7 min |
| Morizon | 28.9 min |
| nieruchomości-online | 22.5 min |
| Photo hashing | 9.1 min |
| History preparation/update | 2.8 min |
| Delist + RCN + geo + write | 8.2 min |
| **Whole scrape** | **110.9 min** |

The seven guarded Śląskie measurements span 84.2–95.4 minutes; accepted
Małopolskie took 110.9 minutes. At roughly 100 minutes per warm region, one
daily sweep of 16
regions would need about **26.8 runner-hours per day**, or **13.4 hours** at
`max-parallel: 2`. That is arithmetic, not an operating plan:
most cold caches, different inventories and portal blocking remain unmeasured,
and parallel regions can worsen shared runner-IP pressure. A matrix is still
not justified: only one pilot has converged and every other region is unknown.
The corrected P3 scout now supplies relative inventory evidence, but not warm
runtime or safe runner-IP concurrency evidence.

The capacity gate should be **at most 180 minutes per warm region**, with a
preferred target of **150 minutes** for headroom, before a two-wide daily
schedule is considered. Otherwise the product must explicitly accept a slower
cadence.

**Capacity contract selected 2026-09-01:** new regions use serial portal access
and, after cold/warm acceptance, at most one refresh every 72 hours. At the
180-minute hard gate, 15 added regions average five runs / 15 runner-hours per
day; two worst measured 95.4-minute Śląskie runs bring the total to about 18.2
hours. A 48-hour serial sweep would require about 25.7 hours/day and is
arithmetically impossible. The existing `rentgen-scrape` lock remains global;
`max-parallel: 2` is deferred until a separate concurrency experiment proves it
does not worsen portal refusal. Each region stays manual through cold and warm
validation, and cohorts still require seven healthy days before expansion.

### Storage and Pages capacity

Current regional branch contents:

| Part | Śląskie latest healthy | Małopolskie retained pilot |
|---|---:|---:|
| Whole per-region branch | 181.8 MiB | 121.8 MiB |
| Regional data including pipeline history | 150.2 MiB | 106.7 MiB |
| Pipeline-only `history.json.gz` removed before deploy | 32.4 MiB | 10.6 MiB |
| **Data if served** | **117.7 MiB** | **96.1 MiB** |
| Caches on the branch | 31.5 MiB | 15.1 MiB |
| `index.json` alone | 21.5 MiB | 23.2 MiB |

The latest measured healthy pair would serve about **213.8 MiB** before the
small application shell and generated pages. The pilot closeout returns the
artifact to the 117.7-MiB Śląskie tree while retaining Małopolskie's recovery
branch. That
reduces current publication size but does not change nationwide capacity math.

GitHub currently documents a **1 GB published-site limit**, a 10-minute deploy
timeout and a soft 100 GB/month bandwidth limit: [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
The custom Pages artifact may be larger at upload time, but that is not a safe
reason to design beyond the published-site limit: [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

At today's measured shapes, the two measured regions would already consume
about one fifth of the published-site limit. Poland was previously estimated at
roughly eight Śląskie inventories before full coverage and archive growth, leaving too
little safety margin for the final architecture. A hosting decision and
migration rehearsal belongs before region four, not after the artifact
approaches the limit.

## Audit findings and their disposition

1. **The old `?region=` state was not durable. Resolved in P1.** Stable regional
   paths are canonical, filter updates preserve other query/hash state, and
   legacy `?region=` plus implicit-Śląskie `?f=` shares redirect safely.
2. **Saved filters leaked between regions. Resolved in P1.** Filter and map
   localStorage keys now include the canonical region slug.
3. **The regional UI was a partial fallback. Resolved in P1.** The browser
   consumes a deploy-derived view of the canonical catalog, including optional
   anchors/districts; unknown and unpublished regions get useful responses.
4. **Discovery metadata was single-region. Resolved in P1.** The root picker,
   stable regional pages, canonical/OG metadata, Dataset JSON-LD, sitemap and
   `llms.txt` are regenerated from the branches actually overlaid.
5. **The old published coverage percentages could not gate rollout.** Schema v1
   combined an unbanded parent with overlapping child bands; failed bands could
   disappear from the denominator and lower-bound totals could exceed 100%.
   P0.1 is now proven live: parent-owned totals, unique-ID unions, bounded
   percentages and explicit failed leaves all appear in the published output.
6. **n-online is not “the portal that is never truncated.” Resolved for the
   warm path.** P0.4 publishes per-town diagnostics, stops the normal path at a
   confirmed archive boundary and completes in 20.5–23.5 minutes. The measured
   forced archive walk took 75.3 minutes, named Katowice flats as its sole cap
   and reported no failed towns; the immediate current-only follow-up retained
   its cache byte-for-byte.
7. **No automated test gate protected the expensive scrape. Resolved in P0.6.**
   Production runs execute the fixture-only suite before portal requests.
8. **A green workflow meant only “some data published.” Partially resolved.**
   Health remains separate from process success, and generated-data validation
   blocks malformed publications while writing the source/runtime/byte summary
   operators need. It does not yet compare a source with the previous good
   publication; finding 11 is the remaining operational half.
9. **Portal order and retrying detail pages were not a cold photo-work policy.**
   Małopolskie first deferred 36,830 ads in portal order. Correctness-first,
   age-persisted ordering was production-validated on Śląskie, but the warm
   pilot still deferred 20,608 critical ads because blocked detail pages and
   retries consumed 96.8 minutes. Cover-first, single-attempt photo work is the
   measured correction and passed twice on Śląskie.
10. **Legacy gallery misses and all-unresolved groups made zero deferrals an
    unsafe completeness signal.** Schema-2 run `33199167100` had zero
    deferrals but 5,107 critical rows without hashes: old negative entries
    could suppress a first cover attempt, after which size/price fallback could
    merge a wholly unresolved group. Negative attempt scope, first-cover
    migration, safe photo-mode normalization and schema-3 invariants were
    validated twice on Śląskie and then accepted on corrective Małopolskie.
11. **Truthful source health did not protect the previous good branch.** Run
    `33274226173` correctly marked Otodom blocked after two HTTP-403 roots, but
    still force-pushed a 35,452-row raw tree over the preceding 51,810-row
    publication. P0.7 now compares categorical source continuity before push:
    it preserves first runs and persistently blocked sources, but fails when a
    previously positive/non-blocked source becomes blocked, unknown, absent or
    zero unless an operator explicitly overrides it. Four guarded runs then
    exercised baseline recovery and positive drift in production; the exact
    outage/rejection and no-push/deploy behavior remain fixture-contract tested.

## Decisions for the next implementation round

- Keep **voivodeship = build, history, cache and branch unit**. That part of the
  architecture is sound.
- Keep OLX code, but treat it as an **optional source on GitHub-hosted runners**.
  A first-request 403 should end the portal immediately and publish an explicit
  blocked status. Full OLX collection should run only from an environment that
  can actually reach it.
- Keep Otodom's restored full baseline as the default. Any subdivision
  experiment remains explicitly opt-in and additive.
- Keep the canonical region catalog as the only slug/TERYT/Polish-form/portal
  map; scraper, frontend, branch tooling and discovery consume it directly or
  through the generated browser derivative.
- Use GitHub Pages for the application shell, but plan to put nationwide data
  in versioned, CORS-enabled object storage (R2 or another S3-compatible store).
  Compact the JSON either way because it also improves first load.
- Treat **`malopolskie`** as the completed first pilot. Its cold, rejected warm
  and accepted corrective runs now cover URL slugs, town derivation, RCN
  `12*`, dense-city pagination, branch isolation and a no-anchor dashboard. It
  is now disabled so a manual-only snapshot cannot age in the public artifact;
  retain `data-malopolskie` at `cba13c7` for reversible recovery.
- Preserve the last good regional branch when a formerly contributing source
  becomes categorically unavailable. Normal count drift and already-blocked
  OLX must not trip the guard; intentional source removal needs an explicit
  override.
- Do not promise daily freshness for all 16 regions until the measured capacity
  supports it. Start with a documented slower cadence if necessary.

## Prioritized task plan

### P0 — make Śląskie a trustworthy rollout template

No second scheduled region is added in this phase.

**Current pick-up point:** P0 and P1 are live-validated, P2 passed, and seven
guarded runs accepted P0.7. The disposable pilot is disabled and its live
removal is audited. Corrected P3 scout `33497077221` passed. Cold Opolskie run
`33504082916` and warm run `33855228296` passed their audits. Opolskie remains
manual until the selected serial 72-hour cadence is implemented; no matrix or
cohort expansion is authorized.

- [x] **P0.1 Redesign the coverage model and region health result.**
  - Record parent inventory total once per source/type.
  - Treat successful price bands as disjoint partitions; do not add a parent
    and its children into one denominator.
  - Report unique served, unique kept, missing/failed partitions and whether a
    portal total is exact or only a lower bound.
  - Split current and archived counts for n-online.
  - Emit `healthy`, `partial`, `blocked` or `unknown` per source and region.
  - **Accept when:** percentages are bounded and comparable between runs;
    losing a band cannot improve them; parent searches intentionally replaced
    by bands do not produce “raise the cap” errors; the UI can distinguish a
    blocked source from a source with zero matching listings.
  - **Implemented 2026-08-13:** coverage schema v2 records parent, partition,
    direct and overlapping-supplement roles; carries private type-scoped IDs
    only long enough to compute unique served/kept unions; fixes the denominator
    to the parent inventory; lists failed, capped, missing and unaccounted
    partitions; bounds `pct` to 0–100; separates n-online current/archive; and
    emits source/type/region health. The dashboard keeps zero-result sources in
    its filter and labels a clean `0`, `blokada`, `brak danych` or partial state.
  - **Verification:** repeated production runs through 2026-08-26 publish
    bounded percentages and the expected source/type health. Production ran
    206 tests before scraping; P1 brings the local suite to **224/224**.

- [x] **P0.2 Restore and re-measure Otodom.**
  - Remove the unproven “~320-page budget” assumption from behavior and docs.
  - First restore at least the pre-scout coverage floor, then test subdivision
    separately and additively.
  - Log elapsed time, successful requests and first refusal for every run.
  - **Accept when:** two consecutive scheduled runs keep at least 16k Otodom
    listings or a new evidence-backed floor is explicitly approved; no tested
    strategy can cut the published baseline in half silently.
  - **Implemented 2026-08-23:** removed the 12-page scout; the default
    is the full 200-page unbanded baseline. Otodom bands require
    `RENTGEN_OTODOM_BANDS=1` and run only after that baseline. Each run logs
    elapsed time, application-level successful/attempted pages and first
    refusal evidence.
  - **Accepted 2026-08-24:** scheduled runs `32658518259` and `32700052454`
    kept 16,267/16,280 listings; both logged 263/263 successful requests and no
    refusal. The preceding push run kept 16,308 with the same request shape.
  - **Corrected floor approved 2026-08-26:** those counts included category
    clones, repeated result-page cards and promoted cards from other regions.
    Runs `32967543284`, `33004188553` and `33007455916` rejected them and kept
    15,921/15,876/15,875 valid Śląskie rows, again with 263/263 successful
    requests and no refusal. The acceptance rule explicitly permits this new
    evidence-backed floor.

- [x] **P0.3 Settle the OLX runner policy.**
  - On a first-request 403, stop the whole portal for that run without cooldown,
    town expansion or bands.
  - Retain a low-frequency reachability probe or a local/residential execution
    path so the scraper is not discarded.
  - Make source-count claims dynamic; never say “five portals” for a four-source
    dataset.
  - **Accept when:** a blocked CI run uses at most one probe per type (preferably
    one for the portal), finishes in seconds and publishes `blocked: 403`.
  - **Implemented 2026-08-23:** the first root 403 performs no cooldown
    or follow-up requests and stops the portal. The unrequested type receives a
    synthetic blocked row that counts as zero searches/pages/issues; generated
    source-count copy uses positive contributors and names blocked sources.
  - **Accepted 2026-08-24:** the push run and both scheduled runs made one real
    request, stopped in about three seconds and published one `blocked: 403`
    issue while explaining the skipped type synthetically.

- [x] **P0.4 Bound n-online and separate archive harvesting.**
  - Identify which towns hit 200 pages instead of hiding them in a two-row
    aggregate.
  - Avoid walking tens of thousands of archive records twice daily merely to
    recover a small active set; give archive refresh its own cadence/cache.
  - Define town coverage and a stable priority order for cold regions.
  - **Accept when:** the phase is at most 40 minutes on warm Śląskie, every
    capped town is named, and active-vs-archive coverage is explicit.
  - **Implemented 2026-08-24:** normal runs keep current offers and stop
    after two consecutive archive-only pages; `auto`/`force`/`skip` controls a
    per-region, seven-day archive harvest cache. The previous full `meta.json`
    bootstraps the first cache marker. Per-town request/live/archive/new/stop
    diagnostics flow into schema v2, and warnings name capped/failed towns.
    A live Katowice-flat smoke kept 1,534 current offers and stopped after 48
    pages (46 current + two archive-boundary pages) instead of page 200.
  - **Warm path accepted 2026-08-26:** three corrected runs kept
    10,864/10,860/10,862 current offers, used 582 pages, finished in
    21.6–23.5 minutes and retained archive cache `2026-08-24 / 47,922` in the
    coverage summary.
  - **Forced path accepted 2026-08-27:** run `33047120282` refreshed 47,754
    archived rows, retained 10,901 current rows and walked 1,817 pages in 75.3
    minutes. Katowice flats were the sole capped town/type and no town failed;
    the complete scrape stayed inside the 180-minute ceiling at 177.4 minutes,
    validated 119.4 MiB and deployed successfully.
  - **Following active path accepted 2026-08-27:** explicit `skip` run
    `33072698054` kept 10,826 current rows in 581 pages and 20.5 minutes,
    reported zero archive rows, and retained the exact 2026-08-27 / 47,754
    cache blob and SHA-256. The full scrape took 79.6 minutes, validated 119.0
    MiB, refreshed only `data-slaskie`, deployed in `33079583960`, and its live
    `meta.json` matched the branch.

- [x] **P0.5 Keep photo correctness work within the warm publication budget.**
  - Process current cross-source size collisions first because they determine
    today’s dedupe result.
  - Use remaining budget for unique-listing fingerprints needed only for future
    relist history.
  - Persist backlog age/count so “budget exhausted” is measurable per region.
  - **Accept when:** all correctness-critical candidates are processed, the
    phase is at most 60 minutes on a warm region, and history-only backlog never
    blocks publishing.
  - **Accepted by measurement:** four corrected active runs completed
    every correctness candidate in roughly 32–74 seconds with no budget
    exhaustion, which closes the Śląskie warm gate.
  - **Cold-pilot follow-up implemented 2026-08-28:** Małopolskie exposed the
    deferred backlog the warm template did not. Current dedupe collisions now
    lead an age-persisted queue; never-attempted work precedes prior empty
    retries, and meta/validation/CI distinguish critical from history-only
    deferrals. This does not reopen P0. Push run `33135609107` validated zero
    deferrals and a 17.1-second phase on Śląskie.
  - **First P2 warm measurement rejected 2026-08-28:** run `33161251008`
    deferred 20,608 of 48,514 correctness candidates, took 96.8 minutes in
    photos and 203.1 minutes overall. Otodom detail pages returned 403 while
    their card images returned 200; photo requests also inherited the scraper's
    retry ladder. Critical cold entries now hash one card cover, gallery work
    remains history-only, single-attempt requests bound phase overrun, and
    schema-2 metrics make cover/gallery and critical no-photo outcomes explicit.
  - **Safety follow-up implemented 2026-08-29:** two Śląskie runs validated
    that correction, but the second still had 5,107 critical rows without
    hashes despite zero deferrals. Legacy gallery negatives now cannot suppress
    a first cover attempt; photo-enabled all-unresolved groups stay separate;
    and schema-3 metrics/validation enforce that heuristic fallback is off.
  - **Corrective pilot accepted 2026-08-29:** run `33257448934` processed
    48,483 critical Małopolskie ads in 9.1 minutes with only seven without a
    hash, zero deferrals/unresolved groups and fallback disabled. The complete
    run took 110.9 minutes.

- [x] **P0.6 Add a cheap CI quality gate and run summary.**
  - Run all offline tests before any network work.
  - Validate every generated JSON file and manifest/shard count.
  - Publish one concise per-phase/per-source summary, including output bytes.
  - **Accept when:** a parser/unit failure spends no portal requests and a green
    job exposes health, runtime, counts, coverage and size without log mining.
  - **Implemented 2026-08-24:** CI installs the test requirements and
    runs the fixture-only suite before `Scrape listings`. The pipeline records
    phase timings in `meta.json`; a post-scrape/pre-push validator parses every
    JSON/JSON.GZ file, checks count/hash/shards/meta/coverage invariants and adds
    source, phase and byte tables to `$GITHUB_STEP_SUMMARY`.
  - **Accepted 2026-08-26:** all three corrected runs passed 206 offline tests
    before portal work, validated 71 files and 118.4–118.5 MiB before the branch
    push, and deployed successfully.
  - **Reconfirmed 2026-08-27:** the forced/following pair ran the same 206-test
    pre-request gate, validated 119.4/119.0 MiB and both deployed successfully.

- [x] **P0.7 Keep a categorical source outage from replacing good data.**
  - Preserve the prior regional `meta.json` long enough to compare source
    continuity after the new generated tree validates.
  - If a source that was positive and non-blocked becomes `blocked`, `unknown`
    or zero, fail before the force-push. A red update already suppresses the
    deploy workflow and leaves the prior branch live.
  - Do not fail a first regional run, a source already known blocked (OLX), or
    ordinary positive count drift. Provide an explicit, logged operator
    override for intentional source removal/reset.
  - Test new-region, persistent-block, catastrophic-loss, recovery and override
    cases, plus workflow placement before `region_storage stage`/push.
  - **Accept when:** the `33274226173` Otodom 15,949→0 shape is rejected while
    a normal warm fixture and persistent OLX zero pass; the data ref remains at
    its previous commit on rejection.
  - **Implemented and accepted 2026-08-30:** the update job
    copies prior `meta.json` to `$RUNNER_TEMP` before scraping. After complete
    payload validation, `validate_data.py` compares each prior positive,
    non-blocked source with the new source state and exits before staging on a
    blocked/unknown/absent/zero transition. First publication, persistent block,
    positive drift and blocked-to-positive recovery pass. The manual Boolean
    `allow_source_regression` input becomes an explicitly logged CLI override.
    Eleven new test cases reproduce 15,949→0, each unavailable condition,
    removal, recovery/override and workflow placement; all **255 offline tests
    pass**. The existing success-only deploy condition is also pinned by the
    workflow contract test. Push `33299512978` and schedules `33309354137` /
    `33334689642` then preserved a recovered positive baseline through normal
    drift, completed in 91.2/93.3/87.6 minutes, refreshed only `data-slaskie`
    and deployed successfully.

**P0 exit gate:** two consecutive warm Śląskie runs publish without a source
continuity regression, finish within 180 minutes (150 preferred), expose
truthful health/coverage, and retain the expected data branch/deploy behavior.

**P0 exit accepted 2026-08-30:** the earlier collection/runtime evidence
included four active runs that finished
in 79.6–90.0 minutes with stable corrected source floors and the required
gate/branch/deploy chain. The forced refresh stayed within 180 minutes, and its
following active run proved that archive work remained isolated behind the
retained cache. P0.7 then recovered Otodom and passed two consecutive schedules
with truthful health, stable counts, zero photo deferrals/unresolved groups,
isolated branch updates and successful deploys. All P0 gates are closed.

### P1 — make the product genuinely region-aware

- [x] **P1.1 Add one canonical 16-region catalog.** Include slug, Polish label,
  TERYT prefix, enabled state, cadence and optional anchor. Validate portal
  slugs rather than assuming all four portals share them.
  - **Implemented 2026-08-27:** `site/regions.json` is schema-validated as the
    exact 16 official TERYT prefixes; scraper URL roots, RCN/geo, frontend and
    locality-label parsing consume it without a second production mapping.
- [x] **P1.2 Fix regional navigation and state.** Preserve `region` when filters
  update the URL, scope localStorage by region, keep all app/stats links in the
  selected region, and give invalid/unpublished slugs a useful response.
  - **Implemented 2026-08-27:** stable paths win over legacy query state;
    filter/map storage keys are regional, legacy links retain filters and
    unknown/unpublished slugs explain themselves.
- [x] **P1.3 Build a national root picker from deployed data.** Generate a small
  catalog containing count, updated time, health and data size for every
  published region. Do not hardcode counts in the UI.
  - **Implemented 2026-08-27:** deploy-derived `data/regions.json` and `/` use
    only enabled, complete overlaid data for publication state, counts,
    freshness, health, contributing sources and served bytes. `enabled: false`
    is a tested artifact-only kill switch; the branch remains recoverable and
    sibling data remains published.
- [x] **P1.4 Generate real regional pages/discovery.** Prefer stable paths such
  as `region/<slug>/` and `region/<slug>/stats/` over query-only SEO. Generate
  canonical, title, description, OG, Dataset JSON-LD, sitemap and `llms.txt`
  entries for each published region; make `/` the Poland picker.
  - **Implemented 2026-08-27:** deploy regenerates listing/stats pages for all
    configured slugs, marks unpublished pages `noindex`, and exposes discovery
    entries only for published data.
- [x] **P1.5 Verify branch/cache isolation with two fixture regions.** A region
  refresh must not carry another region’s phash/RCN cache or remove its
  deployed data. Shared cache files may intentionally fork, but this should be
  documented and tested.
  - **Implemented 2026-08-27:** one helper stages an exact regional allowlist
    and replaces one deploy tree only after verifying it exists. Temporary-git
    tests use Śląskie plus Małopolskie to prove cache/index isolation, sibling
    preservation, missing-tree safety and stale-shard removal. Shared
    `geo_cache.json`/`nol_towns.json` are intentional forks; geo keys carry the
    regional TERYT prefix.

**P1 exit accepted 2026-08-27:** commit `4131f03`, direct deploy `33082048338`,
scrape `33082048365` and automatic deploy `33090688420` all passed. The live
picker/routes/discovery checks and regional branch/cache audit matched the
fixture invariants, so the one-region production path is safe for P2.

### P2 — pilot one new region manually

- [x] Run a cold `malopolskie` workflow manually, not on cron.
  - **Completed 2026-08-27:** run `33098785162` created only
    `data-malopolskie`, published 40,811 / 61,883 current rows and deployed in
    `33126428927`; the catalog cadence remains `manual`.
- [x] Validate all portal region URLs, locality normalization, n-online’s
  derived town list, RCN prefix `12*`, geo convergence, output sizes and every
  health/coverage state.
  - **Cold evidence recorded:** all configured roots were exercised (OLX's
    correct root returned 403), n-online derived 60 towns, RCN used `12*`, geo
    wrote 500 scoped keys, branch/served bytes are measured, and every source
    published an explicit state. Five missing localities, powiat fallbacks and
    4,370 cold-run listings awaiting coordinates keep convergence open through
    the corrective run.
  - **Corrective evidence accepted 2026-08-29:** all four reachable source
    inventories stayed stable, both n-online types retained 60 towns, archive
    and RCN cache blobs stayed unchanged, locality-less properties fell to four,
    geocoded properties reached 28,848/32,132 and no obvious Śląskie locality
    leaked into the regional index. Every source retained explicit health.
- [x] Run a second warm pass to measure cache benefit and convergence.
  - **Completed but rejected 2026-08-28:** active-only run `33161251008`
    recovered Morizon and preserved branch/cache isolation, but 20,608 critical
    photo deferrals and 203.1-minute runtime failed the pilot gate. Pipeline
    success/deploy `33174768425` does not override that result.
- [x] Run one corrective warm pass after the schema-3 safety slice is validated.
  - **Accepted 2026-08-29:** exactly one manual run `33257448934` used
    `nol_archive=skip`. It had zero critical/history deferrals, zero unresolved
    groups, 9.1-minute photos, 110.9-minute total runtime and the exactly
    reconciled 32,132 / 63,596 unique/raw relationship. It remains off cron.
- [x] Verify the deploy contains both regions, the picker/counts work, regional
  filters survive reload/share, and no Śląskie text leaks into Małopolskie.
  - **Cold deploy verified:** both trees, picker counts, listing/statistics
    canonicals and sitemap entries are live. Browser reload/share behavior and
    the final post-warm comparison remain open.
  - **Corrective deploy verified:** deploy `33262428730` succeeded; the current
    live picker and both listing/statistics paths return HTTP 200 with regional
    titles/canonicals and the correct 32,132 Małopolskie count. The current
    255-test suite covers regional reload/share state, branch sibling
    preservation and publication continuity.
- [x] Record the complete pilot in this document with run IDs, timings, request
  counts, source yields, archive size and branch/served bytes.
  - **Cold and rejected-warm evidence complete:** both are recorded above;
    the corrective comparison is recorded above with cache, path, runtime,
    source, locality, size and deploy evidence.

**Pilot exit gate:** cold plus a gate-accepted warm run, no unexplained count
collapse, zero correctness-critical photo deferrals, photo work within 60
minutes, total warm runtime within 180 minutes, truthful regional metadata and
an easy way to disable the pilot without affecting Śląskie.

**Pilot exit accepted 2026-08-29:** the cold, rejected warm and corrective warm
sequence is complete. The accepted run met every numerical gate, refreshed
only `data-malopolskie`, and the tested catalog kill switch can unpublish the
pilot without deleting its branch or touching Śląskie.

**Pilot disposition accepted 2026-08-31:** `malopolskie.enabled` is `false`, so
CI rejects an accidental manual refresh. Deploys `33348260226` and
`33353312262` removed its data and picker/discovery entries and made the stable
route an unpublished `noindex` placeholder. Branch `data-malopolskie` remains
at `cba13c7`; Śląskie advanced normally. The closeout is production-complete.

### P3 — prove scheduling capacity before building the full matrix

P0.7 is production-audited, the pilot disposition is recorded, and its live
unpublication retained both Śląskie and the recoverable pilot branch.

- [x] Implement the scout as a separate `workflow_dispatch` job with
  `contents: read`, the shared serialized portal lock and no data-branch,
  cache, photo, cron or matrix path. It emits 128 target rows at most (16
  regions × four regional sources × two types), makes one request with no retry
  per target, and stops a refusing source globally rather than repeating the
  refusal. A 40-minute runtime budget turns remaining targets into explicit
  skipped rows so partial evidence survives before the 50-minute job backstop.
  Aggregate JSON is retained for 30 days and the run summary exposes comparable
  source totals and slug-review candidates. Nieruchomości-online is explicitly
  excluded because it has no region-wide search root. Nine new fixture/contract
  tests bring the offline gate to **264 tests**.
- [x] Run the manual scout once and audit every target/status row and bad-slug
  candidate. Run
  [33411783792](https://github.com/110kc3/rentgen-ofert/actions/runs/33411783792)
  completed successfully with 128 unique rows, 97 real requests, no retries,
  203.5/2,400 seconds used and no budget exhaustion. It reported 92 `ok`, one
  OLX `blocked`, 31 `skipped_after_block` and four Otodom `not_found` rows.
  Gratka and Morizon returned 32/32 each, Otodom returned 28/32, and no redirect
  was observed.
- [x] Resolve the audit defects. Both Otodom 404 pairs belonged to
  `kujawsko-pomorskie` and `warminsko-mazurskie`; their indexed portal roots use
  `kujawsko--pomorskie` and `warminsko--mazurskie`. Those explicit portal slugs
  are corrected while canonical slug validation remains strict. The first
  summary also ranked each four-probe partial sum beside fourteen six-probe
  sums; only regions matching the common exact declaration shape now receive an
  ordinal rank, and an empty common shape produces no ranking. Three
  regressions bring the gate to **267 tests**.
- [x] Rerun the corrected scout. Run
  [33497077221](https://github.com/110kc3/rentgen-ofert/actions/runs/33497077221)
  produced 128 unique rows in 187.2 seconds: 96 `ok`, one OLX `blocked`, 31
  explicit skips, zero 404/off-slug/parser/network errors and no exhausted
  budget. Otodom, Gratka and Morizon each returned 32/32. Both corrected Otodom
  pairs were HTTP 200, all successful pages were non-empty, and all 16 regions
  shared the exact same six-target declaration shape.
- [x] Choose the next pilot and capacity contract. Opolskie ranked last in both
  scouts at 4,275 then 4,281 (+0.14%), 30.3% below Świętokrzyskie at 6,145. It
  was enabled at `manual` cadence for a cold run without a branch/publication.
  New accepted regions use the 72-hour serial contract above; daily/two-wide is
  rejected for now.
- [x] Run and audit cold Opolskie workflow `33504082916`. It passed the source,
  locality/TERYT `16*`, n-online town, RCN/geo, photo, runtime, branch-isolation,
  served-byte and automatic two-region deploy checks above.
- [x] Audit warm Opolskie run `33855228296`. It passed in 14.3 minutes with
  stable sources, zero deferrals/backlog, immutable archive/RCN caches and exact
  branch isolation.
- [ ] Implement Opolskie's serial 72-hour cadence, then hold the cohort for at
  least seven healthy days before selecting another region.
- [ ] Add regions in cohorts **1 → 2 → 4 → 8 → 16**, with at least seven days of
  healthy measurements before doubling.
- [ ] Scale photo, geo and delist budgets per region/backlog instead of applying
  Śląskie’s constants blindly.
- [ ] Deploy once after a cohort/matrix completes, not once per region job.
- [ ] Define an operational SLO: freshness, minimum source health, maximum
  runtime, maximum served bytes and rollback/disable behavior.

### P4 — move the data ceiling before region four

- [ ] Compact the grid index (column header + row arrays or equivalent) and
  measure browser parse time and bytes, not just gzip size.
- [ ] Shard the archive and lazy-load details, as current listings already do.
- [ ] Prototype versioned object storage: immutable data objects, a tiny mutable
  manifest, CORS, cache headers, atomic publish and rollback to the previous
  manifest.
- [ ] Keep the static UI and small region catalog on Pages; make the data base
  URL configurable per manifest/region.
- [ ] **Accept when:** projected 16-region data remains below 70% of its hosting
  limit, a partial upload cannot publish a broken manifest, and the browser can
  load old and new storage backends during migration.

### P5 — nationwide rollout

- [ ] Rank onboarding order from the scout measurements; do not guess from
  population alone. Leave the largest/most refusal-prone regions until the
  smaller cohorts have run stably.
- [ ] Review each portal’s current terms and set a documented request budget
  before increasing crawl volume; nationwide scale is materially different
  from the current personal Śląskie deployment.
- [ ] Expand by the cohort gates above, publishing health/freshness in the
  region picker.
- [ ] Remove the pre-split shared `data` fallback only after every live region
  has a verified `data-<region>` branch and a rollback snapshot.

## Nationwide definition of done

- [ ] All 16 voivodeships are discoverable from the root picker and have stable
  regional URLs.
- [ ] Every enabled region shows last successful update, source health,
  completeness/partial status and current listing count.
- [ ] No Śląskie-only labels, filters, metadata or saved state leak into other
  regions.
- [ ] The declared cadence fits measured runtime without relying on portal-hostile
  concurrency.
- [ ] Data storage has at least 30% headroom under the chosen service limit and
  supports atomic rollback.
- [ ] Unit/schema tests gate network work; two-region isolation and deploy
  overlay are regression-tested.
- [ ] A blocked portal degrades visibly without erasing the previous good
  region or pretending to be complete.
- [ ] Each region can be disabled independently without changing code or
  deleting another region’s data.

## Deferred until after the rollout

Auctions, rentals/yield, new portals, agency statistics, alerts and card
sparklines remain useful product work, but they do not improve nationwide
correctness or capacity. They should not interrupt P0–P4.
