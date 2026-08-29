# Whole-Poland rollout: status and next tasks

> Audited: 2026-08-29. Production is current through Śląskie cover-path
> validations `33188821781` and `33199167100`, rejected warm Małopolskie pilot
> `33161251008`, and two-region deploy `33206145269`. P0.1–P0.6 and P1.1–P1.5
> are production-validated. P2 remains manual-only: cover-first and
> single-attempt work passed twice, but its follow-up audit found legacy
> gallery misses suppressing first cover attempts and unsafe all-unresolved
> size/price fallback. The schema-3 safety correction needs one normal
> Śląskie validation before one corrective Małopolskie pass.
> This is the current source of truth for the nationwide rollout. `TODO.md`
> retains the detailed development diary and older measurements.

## Executive status

**Śląskie is a trustworthy warm template and the product is genuinely
region-aware, but the project is still not ready for a 16-voivodeship
schedule.** The disposable Małopolskie pilot is the second published tree and
remains manual-only. Its first warm pass was mechanically green but failed the
rollout gate at 203.1 minutes with 20,608 correctness-critical photo deferrals.
The next rollout action is to production-validate the schema-3 safety
correction on Śląskie, then run one corrective Małopolskie pass. The pilot
cannot be disabled as accepted—and no matrix can begin—until that pass meets
the gate.

| Area | Status | Evidence / gap |
|---|---|---|
| Region-scoped scraper output and caches | Ready | `site/data/<region>`, regional caches and exact branch staging are implemented. |
| Canonical 16-region configuration | Proven live | `site/regions.json` is validated and owns Polish forms, TERYT, cadence, anchor and explicit portal slugs; the complete Śląskie path ran end to end. |
| One data branch per region | Proven for two | `data-slaskie` and `data-malopolskie` hold isolated single-commit data/caches; the pilot touched only its branch. |
| Deploy overlay for multiple region branches | Proven live for two | Latest deploy `33206145269` overlaid both trees; the picker, stable pages, data catalog and sitemap expose both. |
| Portal coverage | P0 gate met | Corrected Otodom floor is 15.8–15.9k, OLX's one-probe blocked policy is proven, and active n-online retains 10.83–10.87k in 20.5–23.9 min. |
| Coverage KPI | Proven in production | Schema v2 has published repeatedly: bounded percentages, explicit missing partitions and healthy/partial/blocked source states all survive real runs. |
| Per-region runtime | Śląskie met; pilot warm rejected | Latest Śląskie finished in 91.8 minutes with a 16.8-second photo phase. Małopolskie's first warm pass took 203.1 minutes, including 96.8 minutes of photos, and deferred 20,608 critical ads. |
| Region picker and durable regional URLs | Proven live for two | National picker, stable regional paths, region-scoped state, legacy redirects and unpublished/unknown responses passed production checks; live pilot canonicals are region-correct. |
| Per-region metadata / OG / sitemap / llms.txt | Proven live | Canonical/JSON-LD documents parse and discovery contains only data-backed published regions. |
| CI region matrix / cadence | Not implemented | The workflow still schedules Śląskie twice daily and accepts other regions only by manual input. |
| Nationwide data hosting | Not decided | The two current trees serve 201.9 MiB combined; GitHub Pages has a published-site limit of 1 GB. |

**Rollout decision:** do not add a scheduled second region. P1 is live;
`malopolskie` is enabled only long enough for a manual disposable pilot—not a
16-region matrix.

## Production snapshot

### Repository and deployment

- The production-validated regional architecture is `4131f03` (`feat: build
  regional catalog and stable pages`), on top of `701795e` (regional-boundary
  enforcement), `60bea36` (cross-category duplicate rejection) and `53ce632`
  (within-page portal clone rejection).
- The [live site](https://110kc3.github.io/rentgen-ofert/),
  [Śląskie metadata](https://110kc3.github.io/rentgen-ofert/data/slaskie/meta.json)
  and [Małopolskie metadata](https://110kc3.github.io/rentgen-ofert/data/malopolskie/meta.json)
  all return HTTP 200.
- [Deploy run 33206145269](https://github.com/110kc3/rentgen-ofert/actions/runs/33206145269)
  published both regional trees. The generated catalog reports 30,752 Śląskie
  properties / 119.3 MiB and 33,358 Małopolskie / 82.6 MiB served.
- Latest Śląskie data is **2026-08-28 19:57 UTC**, **30,752** unique properties
  from **51,874** current raw listings. Pilot Małopolskie data is
  **2026-08-28 13:17 UTC**, **33,358** from **63,602**.
- Both regions have four contributing sources: Otodom, Gratka, Morizon and
  nieruchomości-online. OLX contributed zero after one bounded HTTP-403 probe.
- The P1/pilot scrapes ran **224 offline tests before portal work**; queue and
  first warm validation ran the expanded **230-test** gate. The cover-path
  slice expanded it to **235 tests**; this safety slice expands it to **244
  tests** and schema-3 photo arithmetic. The
  post-generation validator protects every branch push.

### Latest completed validation runs

The corrected baselines, explicit archive sequence, regional release, cold
pilot, queue validation and first warm pilot all passed pipeline validation and
deployed. The Małopolskie warm row failed the stricter P2 rollout gate; the two
following Śląskie rows validated the cover-path correction without accepting
the pilot:

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

One ordinary Śląskie run must validate schema 3 before the corrective
active-only Małopolskie run is dispatched.

### Latest Śląskie source health

These are the published schema-v2 values from schedule `33199167100`:

| Source | Current kept listings | Reported search state | Assessment |
|---|---:|---|---|
| Otodom | 15,957 | `partial`, 71.9%; flat root stops at page 200 | Correct regional floor; 263 pages completed with no refusal. |
| OLX | 0 | `blocked`, one real root row, HTTP 403 | Runner/IP block; one probe ends the portal in about three seconds. |
| Gratka | 12,515 | `partial`, 99.9%; 564 pages, zero issues | Full useful inventory, with the small declared-total gap explicit. |
| Morizon | 12,515 | `partial`, 100% against a lower-bound total; 564 pages, zero issues | Useful inventory matches Gratka and no partition failed. |
| nieruchomości-online | 10,887 current | `healthy`; 579 current-only pages; 47,754 archived rows cached from 2026-08-27 | The cache remained available and the run served no archive rows into its current result. |

The published unique count is lower than the source sum because Gratka and
Morizon substantially overlap and are merged.

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
  exhaustion, so P0.5 remains closed for the Śląskie template. The cold pilot
  proved explicit queueing is required for onboarding; its first warm pass
  then proved ordering alone is insufficient when a portal's detail pages are
  blocked. Cover-first, no-retry correction targets that P2-specific evidence.
- **The corrected Otodom recovery succeeded.** Duplicate-category cards,
  repeated portal clones and promoted cards from other voivodeships had
  inflated the earlier 16.3k count. After rejecting them, all three runs kept
  **15,921 / 15,876 / 15,875** valid regional rows with 263/263 successful
  requests and no refusal. P0.2 therefore approves 15.8–15.9k as its explicit
  evidence-backed floor; the forced/follow-up runs retained 15,887/15,866 with
  the same request shape, and experimental bands remain opt-in and additive.
- **The OLX policy succeeded.** All five runs made one house page-one probe,
  received HTTP 403, stopped in seconds, skipped the flat request synthetically
  and published one issue with source health `blocked`. P0.3 is accepted.
- **The publication gate succeeded.** Every corrected/forced/following run
  executed the offline suite before scraping, validated 71 generated JSON
  files and 118.4–119.4 MiB before pushing, refreshed only `data-slaskie`, and
  triggered a successful Pages deploy.
- **The regional product succeeded live.** P1 scrape `33082048365` refreshed
  only `data-slaskie`; its archive cache retained the forced-refresh SHA-256
  and its 500 new geo entries use the `24|…` scope. The shared cache retained
  11,175 pre-P1 unprefixed entries, but production lookup ignores them. Direct
  and automatic deploys exposed one published region, stable canonical paths
  and valid JSON-LD while keeping Małopolskie `noindex`/data-less at that P1
  checkpoint and unknown slugs 404. P2 deploy `33126428927` subsequently
  exposed the second complete tree without changing those invariants.

### Runtime and scheduling capacity

Representative phase times from the latest active-only run `33072698054`:

| Phase | Time |
|---|---:|
| Otodom | 10.2 min |
| OLX (blocked) | 0.1 min |
| Gratka | 18.3 min |
| Morizon | 19.7 min |
| nieruchomości-online | 20.5 min |
| Photo hashing | 1.0 min |
| History preparation/update | 6.8 min |
| Delist + RCN + geo + write | 3.1 min |
| **Whole scrape** | **79.6 min** |

At the corrected roughly 86.0-minute active average, one daily sweep of 16
Śląskie-sized regions would need about **22.9 runner-hours per day**, or
**11.5 hours** at `max-parallel: 2`. That is arithmetic, not an operating plan:
most cold caches, different inventories and portal blocking remain unmeasured,
and parallel regions can worsen shared runner-IP pressure. A matrix is still
not justified: one cold and one rejected warm pilot are measured, but its
corrective convergence and every other region remain unknown.

The capacity gate should be **at most 180 minutes per warm region**, with a
preferred target of **150 minutes** for headroom, before a two-wide daily
schedule is considered. Otherwise the product must explicitly accept a slower
cadence.

### Storage and Pages capacity

Current regional branch contents:

| Part | Śląskie | Małopolskie latest warm |
|---|---:|---:|
| Whole per-region branch | 181.8 MiB | 105.0 MiB |
| Regional data including pipeline history | 150.9 MiB | 91.2 MiB |
| Pipeline-only `history.json.gz` removed before deploy | 31.6 MiB | 8.6 MiB |
| **Data actually served** | **119.3 MiB** | **82.6 MiB** |
| Caches on the branch | 30.9 MiB | 13.8 MiB |
| `index.json` alone | 22.9 MiB | 23.4 MiB |

The live two-region data payload is therefore **201.9 MiB** before the small
application shell and generated pages.

GitHub currently documents a **1 GB published-site limit**, a 10-minute deploy
timeout and a soft 100 GB/month bandwidth limit: [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
The custom Pages artifact may be larger at upload time, but that is not a safe
reason to design beyond the published-site limit: [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

At today's measured shapes, two incomplete regions already consume about one
fifth of the published-site limit. Poland was previously estimated at roughly
eight Śląskie inventories before full coverage and archive growth, leaving too
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
8. **A green workflow meant only “some data published.” Resolved in P0.1/P0.6.**
   Health remains separate from process success, and the generated-data
   validator blocks malformed/incomplete publications while writing the source,
   runtime and byte summary operators need.
9. **Portal order and retrying detail pages were not a cold photo-work policy.**
   Małopolskie first deferred 36,830 ads in portal order. Correctness-first,
   age-persisted ordering was production-validated on Śląskie, but the warm
   pilot still deferred 20,608 critical ads because blocked detail pages and
   retries consumed 96.8 minutes. Cover-first, single-attempt photo work is the
   measured correction and passed twice on Śląskie.
10. **Legacy gallery misses and all-unresolved groups made zero deferrals an
    unsafe completeness signal.** The latest run had zero deferrals but 5,107
    critical rows without hashes: old negative entries could suppress a first
    cover attempt, after which size/price fallback could merge a wholly
    unresolved group. Negative attempt scope, first-cover migration, safe
    photo-mode normalization and schema-3 invariants are implemented and now
    await production validation.

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
- Pilot **`malopolskie`** first after the P0 gate. It is a meaningful cold-region
  test for URL slugs, town derivation, RCN `12*`, dense-city pagination and a
  no-anchor dashboard. `dolnoslaskie` remains the fallback pilot.
- Do not promise daily freshness for all 16 regions until the measured capacity
  supports it. Start with a documented slower cadence if necessary.

## Prioritized task plan

### P0 — make Śląskie a trustworthy rollout template

No second scheduled region is added in this phase.

**Current pick-up point:** P0 is complete and live-validated, including the
forced/following archive sequence. Publish P1, then proceed to exactly one
manual pilot.

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

**P0 exit gate:** two consecutive warm Śląskie runs publish without a silent
source regression, finish within 180 minutes (150 preferred), expose truthful
health/coverage, and retain the expected data branch/deploy behavior.

**P0 exit accepted 2026-08-27:** four active runs finished in 79.6–90.0 minutes
with stable corrected source floors and the required gate/branch/deploy chain.
The forced refresh stayed within 180 minutes, and its following active run
proved that archive work remained isolated behind the retained cache.

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
- [ ] Validate all portal region URLs, locality normalization, n-online’s
  derived town list, RCN prefix `12*`, geo convergence, output sizes and every
  health/coverage state.
  - **Cold evidence recorded:** all configured roots were exercised (OLX's
    correct root returned 403), n-online derived 60 towns, RCN used `12*`, geo
    wrote 500 scoped keys, branch/served bytes are measured, and every source
    published an explicit state. Five missing localities, powiat fallbacks and
    4,370 cold-run listings awaiting coordinates keep convergence open through
    the corrective run.
- [x] Run a second warm pass to measure cache benefit and convergence.
  - **Completed but rejected 2026-08-28:** active-only run `33161251008`
    recovered Morizon and preserved branch/cache isolation, but 20,608 critical
    photo deferrals and 203.1-minute runtime failed the pilot gate. Pipeline
    success/deploy `33174768425` does not override that result.
- [ ] Run one corrective warm pass after the schema-3 safety slice is validated.
  - Let its push-triggered Śląskie workflow finish and audit it once. Only if
    schema-3 unresolved-group metrics, disabled fallback and branch validation
    pass, dispatch exactly one manual
    Małopolskie run with `nol_archive=skip`; do not add it to cron or watch it.
  - Accept only with zero critical deferrals, photo runtime at most 60 minutes,
    complete runtime at most 180 minutes and an explainable stable unique/raw
    relationship.
- [ ] Verify the deploy contains both regions, the picker/counts work, regional
  filters survive reload/share, and no Śląskie text leaks into Małopolskie.
  - **Cold deploy verified:** both trees, picker counts, listing/statistics
    canonicals and sitemap entries are live. Browser reload/share behavior and
    the final post-warm comparison remain open.
- [ ] Record the complete pilot in this document with run IDs, timings, request
  counts, source yields, archive size and branch/served bytes.
  - **Cold and rejected-warm evidence complete:** both are recorded above;
    append the corrective comparison before accepting this item and exit gate.

**Pilot exit gate:** cold plus a gate-accepted warm run, no unexplained count
collapse, zero correctness-critical photo deferrals, photo work within 60
minutes, total warm runtime within 180 minutes, truthful regional metadata and
an easy way to disable the pilot without affecting Śląskie.

### P3 — prove scheduling capacity before building the full matrix

- [ ] Scout one page per source/type for all 16 regions to rank them by declared
  inventory and detect bad slugs cheaply.
- [ ] Choose and document one of two capacity contracts:
  - daily refresh with warm runtime at most 180 minutes and `max-parallel: 2`,
    after confirming that two concurrent regions do not worsen blocking; or
  - a slower 48/72-hour cadence with serial portal access.
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
