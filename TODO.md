# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-08-28

## Current (2026-08-28) — P0/P1 live; P2 warm pilot missed its photo gate

The corrected Śląskie baseline is published and stable. Five runs on main SHA
`701795e` rejected cross-category clones, duplicate cards within a portal result
page and promoted cards from another voivodeship, including the explicit
forced/following archive sequence:

| Run | Trigger | Scrape runtime | Unique / raw | Otodom | n-online current | Deploy |
|---|---|---:|---:|---:|---:|---|
| `32967543284` | push | 90.0 min | 30,862 / 51,937 | 15,921 | 10,864 | `32976169826` |
| `33004188553` | manual | about 89 min | 30,794 / 51,880 | 15,876 | 10,860 | `33011950180` |
| `33007455916` | schedule | 85.5 min | 30,761 / 51,883 | 15,875 | 10,862 | `33018656594` |
| `33047120282` | forced archive | 177.4 min | 30,781 / 51,906 | 15,887 | 10,901 | `33060020329` |
| `33072698054` | active-only follow-up | 79.6 min | 30,684 / 51,754 | 15,866 | 10,826 | `33079583960` |

All five made 263/263 successful Otodom requests with no refusal. The old
16.3k count included out-of-scope promoted/cloned records; **15.8–15.9k is the
approved evidence-backed regional floor**, not a regression. OLX made one
bounded HTTP-403 probe and remained explicitly `blocked`.

P1 commit `4131f03` then passed direct deploy `33082048338`, the complete
push-triggered scrape `33082048365` and automatic deploy `33090688420`. The
regionalized scrape ran for 92.1 minutes, passed all 224 offline tests before
portal work, validated 30,763 unique properties from 51,890 raw rows (119.3
MiB), staged only the 76 allowed Śląskie paths and refreshed `data-slaskie`.
Its n-online path remained current-only (10,871 rows / 581 pages), the archive
cache retained the same SHA-256, and geo wrote 500 new TERYT-scoped `24|…`
keys. The shared file also retained 11,175 pre-P1 unprefixed keys, which the
regional lookup path deliberately ignores.

Cold Małopolskie workflow `33098785162` then ran manually on commit `18afb78`,
after waiting behind the routine serialized Śląskie scrape. Its 247.6-minute
job / 246.5-minute scrape passed 224 tests, created only `data-malopolskie` at
`311f875`, validated 40,811 unique properties from 61,883 current raw rows and
deployed both regions in `33126428927`. The branch is 98.8 MiB, its regional
data is 86.4 MiB including pipeline history, and 79.6 MiB is actually served.
The live picker, regional listing/statistics canonicals, sitemap and data
catalog all expose both complete enabled trees; Małopolskie remains manual-only.

The cold evidence is useful rather than an exit pass. Portal collection took
132.3 minutes, RCN's cold `12*` pull 20.5 minutes and the photo phase exhausted
all 90 minutes: 14,536 listings got hashes, 12,560 Morizon twins needed none,
and **36,830 were never attempted**. Of 26,922 cache entries, 12,381 are first
Otodom empty-gallery attempts while 14,378 are successful Gratka hashes; the
portal-ordered queue reached neither untwinned Morizon nor n-online. The warm
pass would therefore repeat low-yield work before measuring convergence.

The queue slice fixed that measurement. Current dedupe collisions lead the
photo queue; within correctness and history queues, free cache hits and
oldest persisted deferrals lead, never-attempted URLs precede negative-cache
retries, and the order is stable. Deferred URLs retain their first-wait date in
the regional phash cache without becoming false photo misses. `meta.photos`,
the generated-data validator and the GitHub summary now expose critical versus
history counts, cache/fetch outcomes and critical/backlog deferrals. The local
offline gate is **230/230**.

Push validation `33135609107` accepted the new queue on warm Śląskie. The job
waited behind scheduled run `33134866042`, but its own scrape took 92.0 minutes
and passed all 230 pre-request tests. Photos took 17.1 seconds: 41,659 current
correctness candidates plus 1,932 history-only candidates, 43,559 cache hits,
32 fetches, 8,117 ID-settled twins and **zero critical/history deferrals**. It
validated 30,591 unique properties from 51,708 raw rows (119.1 MiB served),
refreshed only `data-slaskie` at `2282009`, and deployed in `33144201326`; the
live metadata matches. Otodom retained 15,863, n-online 10,735, Gratka 12,555,
and Morizon recovered its prior timeout shortfall to 12,555 with no issue.

Warm Małopolskie run `33161251008` then completed and deployed in
`33174768425`, but it **did not pass the pilot exit gate**. Source collection
was stable and Morizon recovered fully: Otodom 12,578, Gratka 20,048, Morizon
20,051 and n-online 10,925 current rows. The explicit active-only path reused
the 2026-08-27 / 14,429-row n-online archive cache; that cache, the RCN snapshot
and `data-slaskie` at `2282009` stayed byte/ref unchanged. The branch advanced
only `data-malopolskie` to `96b1882` and the generated tree deployed normally.

The rollout result is nevertheless a rejection: the scrape took **203.1
minutes**, beyond the 180-minute ceiling. Photos alone took 96.8 minutes and
left 22,452 URLs deferred, including **20,608 of 48,514 correctness-critical
ads**. It produced 33,358 unique properties from 63,602 raw rows, down from
40,811 / 61,883 cold; the added Morizon/n-online fingerprints explain why more
cross-portal duplicates can now merge, but the count is not a convergence
baseline while 42.5% of the critical queue remains unprocessed.

The cache identifies the bottleneck precisely. Gratka has 20,089 positive
entries and untwinned Morizon 6,878; n-online reached only 887. Otodom still has
12,381 empty results because its detail pages answer HTTP 403, while a sampled
search-card image from the same live ad answers HTTP 200 image/jpeg. The photo
phase also inherited the portal scraper's status-retry ladder, allowing its
nominal 90-minute budget to overrun by 6.8 minutes.

This corrective slice makes cold correctness work cover-first: an uncached
critical ad hashes its already-scraped card image once, while history-only work
keeps the full-gallery path. Cover evidence is tagged in the persisted cache so
it is not confused with a gallery. Photo downloads use a single-attempt HTTP
session, and `meta.photos` schema 2 plus the generated-data validator expose
cover/gallery cache hits and fetches as well as critical rows with photos,
without photos or deferred. The fixed budget and conservative merge rule are
unchanged: a cover match can prove identity; a non-match keeps the ads apart.

### P0 evidence now accepted

- **The twice-daily n-online path is current-only.** The portal orders current
  offers before its archive and the walk stops after two consecutive
  archive-only pages. Four corrected active runs retained 10.83–10.86k current
  offers in 581–582 pages; the phase took 20.5–23.5 minutes, well below the
  40-minute gate, and published compact per-town stop diagnostics.
- **Archive harvesting has its own cadence and cache.** `RENTGEN_NOL_ARCHIVE`
  is `auto` (default, seven days), `force`, or `skip`; the cadence is adjustable
  with `RENTGEN_NOL_ARCHIVE_DAYS`. A per-region
  `cache/nol_archive_<region>.json` records refresh date, counts and whether the
  harvest capped/failed. The first run bootstraps it from the last full
  `meta.json`, so rollout does not immediately repeat the 1,700-page walk.
  Full refreshes still return archived ads to the durable history store.
- **The forced archive path is measured.** Run `33047120282` refreshed the
  n-online cache on 2026-08-27: 47,754 archived and 10,901 current rows in
  1,817 pages. The n-online phase took 75.3 minutes; Katowice flats were the
  sole capped partition and no town failed. The whole scrape took 177.4
  minutes, validated 119.4 MiB and deployed in `33060020329`.
- **The following active path did not inherit archive work.** Explicit `skip`
  run `33072698054` used 581 pages and 20.5 minutes for 10,826 current rows,
  reported zero current-run archive rows, and retained the 2026-08-27 / 47,754
  cache with the exact same Git blob and SHA-256. Its 79.6-minute scrape,
  119.0-MiB validator, branch push and deploy `33079583960` all passed.
- **Town coverage is explicit.** Each type publishes compact per-town request,
  live/archive, new-unique and stop statistics. Coverage summaries name capped
  and failed towns, and warnings now say `capped partition(s): katowice`.
  Seed order is stable, then newly observed towns rank by inventory, then
  cached fallbacks.
- **The expensive workflow is gated.** CI installs test dependencies and runs
  the offline suite before any portal request. After scraping,
  `scripts/validate_data.py` parses every JSON/JSON.GZ file, checks the manifest
  count/hash, exact shard set and URL-to-shard mapping, verifies meta/coverage
  invariants, and writes source/phase/size tables to the GitHub job summary.
  A failure prevents the data-branch push.
- **Phase timings are data, not log archaeology.** `meta.json.runtime` records
  each source plus photo/history/delist/RCN/geo/write and total seconds.
- **Warm Śląskie needs no extra photo time, but cold regions need bounded
  evidence.**
  Four corrected Śląskie runs processed the old queue in roughly 32–74 seconds
  with no exhaustion. Małopolskie then proved portal order is not a safe cold
  queue: its full 90 minutes still deferred 36,830 ads. Correctness-first,
  age-persisted ordering made that backlog explicit. Its first warm pass still
  deferred 20,608 critical ads because blocked detail pages and status retries
  made gallery fetching too expensive; cover-first, single-attempt hashing now
  addresses that measured bottleneck without raising the publication budget.
- **Every publication was protected.** The offline gate preceded portal work,
  the generated-data validator checked all 71 JSON files and 118.4–119.4 MiB,
  and the regional branch push and Pages deployment succeeded after each run.

### Regional product now live

- `site/regions.json` is the single schema-1 catalog for all 16 official
  voivodeships: canonical slug, Polish forms, TERYT, enabled/cadence, optional
  anchor/districts and an explicit slug for each region-wide portal. Runtime
  code no longer carries a second slug/TERYT/label map.
- The deploy generates `/` as a national picker and stable
  `region/<slug>/` + `region/<slug>/stats/` pages from the data branches that
  were actually overlaid and enabled. Counts, freshness, health and served
  bytes feed the picker and `data/regions.json`; metadata, JSON-LD, sitemap and
  `llms.txt` include published regions only. Setting `enabled: false` removes
  only that region's copy from the Pages artifact while leaving its recoverable
  data branch and every sibling untouched. Unpublished/unknown slugs explain
  themselves.
- Browser filter and map state is keyed by region. Stable app/stats links and
  legacy redirects preserve shared filters, including old Śląskie `?f=` links.
- Regional branch staging and deploy overlay now use one tested helper. A real
  temporary-git two-region fixture proves that phash/RCN/archive caches do not
  cross branches, sibling deployed data survives, and stale shards disappear.
- UUG geocoding selects the candidate matching the catalog TERYT prefix and
  scopes cache keys by that prefix. Same-named places in different regions can
  no longer reuse the wrong centroid.
- Verification currently covers **235 offline tests**, including catalog,
  generator, navigation, two-region storage, ambiguous-geocoder and persisted
  photo-queue regressions.
- Production checks after `33090688420` proved the one-region product; deploy
  `33126428927` then proved the live two-region picker, stable
  listing/statistics canonicals, sitemap and catalog. Valid unpublished regions
  still return a useful `noindex` page without exposing a data tree; unknown
  regions return 404.

### Next

1. Push this corrective slice; let the ordinary Śląskie workflow validate
   schema-2 photo metrics and the no-retry/cover path. Do not watch it.
2. After that workflow finishes, audit it once. If it passes, dispatch one
   corrective Małopolskie pass with archive work explicitly skipped; do not
   watch it.
3. Accept only with zero critical deferrals, a photo phase at most 60 minutes,
   whole runtime at most 180 minutes and an explainable stable count. Then
   disable the disposable pilot and prove `data-slaskie` stayed unchanged. Do
   not add Małopolskie to cron or create a 16-region matrix.

## Superseded (2026-08-13) — stop before region two and repair the template

**Current source of truth:** [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md). That
document contains the evidence, decisions, acceptance gates and full P0–P5
plan. The long sections below are the development diary and preserve the
measurements that led here.

The two validation runs that the previous section was waiting for have landed:
`31576707243` (250 min) and `31631007171` (263 min), both green and published.
They proved the per-region branch and delist changes, but they also make a
16-region matrix the wrong next move:

- `data-slaskie` was created, refreshed and deployed successfully;
- the delist sweep fell to 37–42 seconds;
- Otodom fell from the stable 16.6k baseline to **8,461 / 8,541** kept, with
  405s beginning after only ~5–6 minutes despite the 12-page scout;
- OLX returned 403 on both types in both runs and contributed zero;
- n-online took 71–76 minutes and its flat crawl hit a per-town cap;
- photo hashing still took 94–98 minutes and left 5,872 / 4,420 records behind;
- a warm region now costs 250–263 minutes, so 16 regions at
  `max-parallel: 2` need ~34 hours, not one day;
- the live Śląskie payload is already ~102 MB excluding pipeline-only history.

**Do next, in this order:**

1. [x] Fix coverage semantics and add explicit per-source/region health
       (`healthy`, `partial`, `blocked`, `unknown`). Schema v2 is implemented
       locally; its first published run remains to be inspected.
2. [x] Restore the Otodom coverage floor and re-measure two scheduled runs.
3. [x] Make an OLX page-one 403 fail fast and report the source as blocked.
4. [ ] Bound n-online/archive work and split photo correctness work from the
       history-only backlog.
5. [ ] Add the offline-test/schema gate before any scrape requests.
6. [ ] Meet the P0 exit gate in `POLAND_ROLLOUT.md`; only then build regional
       navigation and manually pilot `malopolskie`.

### Done in this slice — truthful coverage and health (P0.1)

- Parent region searches now own each source/type inventory total exactly once;
  price leaves never inflate the denominator. Internal type-scoped listing IDs
  union parent, band, retry and overlapping town results into unique served and
  kept counts, and private ID sets are stripped before JSON publication.
- Coverage schema v2 names direct/parent/partition/supplement roles, reports
  exact or lower-bound totals, bounds percentages to 0–100, and lists failed,
  capped, missing and unaccounted partitions. Intentional parent/scout and
  recursively replaced band rows no longer generate operator warnings.
- Health is explicit per type, source and region: `healthy`, `partial`,
  `blocked`, or `unknown`. Whole-scraper exceptions become coverage rows instead
  of disappearing; n-online distinguishes an all-town refusal from a clean zero
  and separates current from archived observations.
- The dashboard retains every expected source in its filter even when it
  contributed zero. A clean zero is shown as `0`; blocked and unknown sources
  are visibly labelled, and partial sources carry a warning marker.
- Verification: `python -m compileall -q scraper`, `node --check site/app.js`,
  `git diff --check`, and **189/189** offline tests pass. The code has not yet
  produced a live schema-v2 dataset, so P0.2 plus live inspection is next.

## Superseded (2026-08-12) — the page budget, the sweep, the twins, and one branch per region

**Historical pick-up pointer only:** this section originally pointed to “What
to do next” at its end. Its validation runs have now landed; use the 2026-08-13
section and `POLAND_ROLLOUT.md` instead. Picks 1, 2, 4, 5 and 6 of the previous
list shipped here; pick 3 (OLX's slot) remained open at this snapshot.

### What the two runs before this commit established

`31502042693` (push, 291 min) and `31526243162` (schedule, 294 min), both green,
both published. They judged the previous batch and it came out two for three:

| | expected | measured |
|---|---|---|
| item 1 — otodom waits out its 405 | seven bands recovered | **nothing recovered**, and otodom went 12–13 → 30–33 min |
| item 2 — the OLX failure is legible | a fingerprint on the refusal | **`403 Forbidden` on request #1**, both runs — a block, not a layout change |

- **OLX is blocking the runners, and escalating.** Worked 2026-08-10 16:25 →
  challenge body 21:09 → worked 2026-08-11 07:14 → `403` 14:32 → `403` 19:24.
  The 28 s cooldown cannot touch it. Item 2 did its job: the HTTP error path is
  separate from the parse path now, so this is a fact rather than a guess.
- **otodom's `pct` rose 70.3 → 77.9% and that is an artifact.** Seven dead bands
  contribute nothing to the *denominator* either, so losing them harder made the
  fraction look better. Kept listings: 16 622 / 16 635 / 16 697 / 16 629 — flat
  across every run ever measured, bands or no bands.

### The 405 is a page budget, which is why waiting could not fix it

The first 405 arrives after **322 successful otodom pages**, and it arrives
inside `300k-400k` between its pages 5 and 11 in all four runs. **200 of those
322 are the unbanded flat walk** — which collects 12 518 of 18 334, i.e. exactly
the ads the bands are then sent to fetch. The band yields say it outright:
`200k-300k page 1/35: +4`, `page 2: +0`, `page 3: +2`.

- [x] **The unbanded otodom search is a scout now** (`otodom.SCOUT_PAGES = 12`).
      It walks far enough to state the total, seed the dedupe and pick up the
      priceless ads that no price filter can return, then stands aside. The cap
      only bites once the portal has stated a total past its serving window —
      the same question `bands.overflows` asks, asked one page in — so the house
      search, which needs no bands, still walks to `max_pages`. A scout row is
      excluded from `coverage.warnings`: "raise RENTGEN_MAX_PAGES or subdivide
      the search" is precisely what it just did. At this historical snapshot it
      stayed in the `truncated` count; schema v2 (2026-08-13) later reclassified
      it as a non-actionable diagnostic row.
- [x] **A failed retry no longer overwrites a better attempt** (`bands.best_of`).
      The retry restarts at page 1, and its row replaced the first
      unconditionally — so `300k-400k`, which had walked to page **11**, was
      recorded as `failed after 1 page(s)`, and `check_totals` lost the total it
      had read: accounted ads fell **6 821 → 3 529**, reported as otodom's price
      filter dropping 14 805 ads. The listings were never at risk (the walkers
      merge into the caller's `seen`/`out` as they go); every number *about* the
      search was. A recovered walk always wins; between two refusals, the one
      that got further does.

### The delist sweep, cut

Diagnosed in the 2026-08-11 section, fixed here. Its cost was
response-time-driven — 300 sequential GETs where a dead ad answers at once and a
live, slow or throttled one costs the full 20 s timeout **and then the shared
session's 405/429/5xx ladder on top**.

- [x] **All three fixes, because they are complementary.** The checks run
      concurrently (`MAX_WORKERS = 8`, as photomatch); on `net.probe_session()`,
      which does not retry at all — "could not tell" is a perfectly good answer
      to a yes/no question and the record comes round next run; under
      `RENTGEN_DELIST_BUDGET_MIN` (default 10), with unasked records left
      *unasked*, not concluded, keeping their place at the front of the
      oldest-first queue. `is_gone`'s timeout drops 20 s → 8: that 20 was the
      scraper's, appropriate for a page we need the contents of and far too
      patient for a liveness probe.

### Twins cost no photo fetch

- [x] **`link_twins` runs before the photo phase**, not inside `dedupe` after
      it. A morizon ad carrying gratka's ad id in its thumbnail is already
      identified; hashing it answers a question nobody is asking. It now carries
      `_identified_by` and `photomatch.attach_hashes` skips it outright —
      **~8 700 detail fetches a run** on the published 2026-08-11 numbers,
      against a phase that was starving 9 177–18 296 listings of a budget it
      cannot stretch. `_build` unions the gratka half's hashes onto the merged
      property, so nothing downstream goes without; the skip is recorded as
      neither a hit nor a photo miss, so the cache learns nothing false.

### One branch per region

- [x] **`data` → `data-<region>`** (rollout Step 5's first item). The shared
      branch is what region #2 would have broken: śląskie alone is ~150 MB and
      every region's job would fetch, and force-push over, all of everyone's.
      A job now pulls `data-$REGION`, and pushes back only `site/data/$REGION`
      plus the caches that region owns (`phash_`/`rcn_`) and the two that are
      not region-scoped — named explicitly, so a job seeded from the shared
      branch does not drag another region's 15 MB phash cache onto its own.
      `deploy.yml` overlays the pre-split `data` branch first and every
      `data-*` branch on top, so **the split needs no flag day** and a region
      that has not re-pushed yet keeps publishing. It looks before it wipes: a
      branch without its region's directory leaves what the shared branch
      supplied rather than deleting it and publishing nothing.
- Concurrency stays **one scrape at a time across regions**, deliberately. The
  portals see one pool of runner IPs whichever voivodeship we ask about, and
  two of them are already refusing us. Parallelism belongs in a matrix with
  `max-parallel` set explicitly, when there is a second region to run.

Tests: **169 → 181**, still fully offline. Each new one was confirmed to fail
against the unfixed code before being kept.

### What to check on the run this commit triggers

- **otodom.** `flat/slaskie` should walk 12 pages, not 200, and the seven bands
  `400k-500k` … `1500k-3M` should have coverage rows with pages in them. If the
  405 still arrives in `300k-400k`, the budget is wall-clock rather than pages
  and the scout cap bought only time — say so and stop guessing.
- **otodom's kept count**, which has been 16 6xx in every run ever measured.
  This is the first change that can move it.
- **The delist sweep**, 27–34 min → single digits, and how many it left for
  next run.
- **The photo phase**: `identified by their twin` in the log, ~8 700 of them,
  and whether `skipped, photo budget exhausted` finally reaches zero (the trend
  is 18 296 → 12 857 → 11 096 → 9 886 → 9 177 as the cache warms).
- **`data-slaskie` exists** and the site still publishes from it. The deploy
  log should say `overlaid slaskie from data-slaskie`.

### What to do next (in this order)

1. **Settle OLX's slot** — the one pick left from the previous list, and now a
   decision rather than an investigation. It is a hard `403` on request #1, two
   runs running, and no amount of waiting reaches it. It was 31 min for 1 751
   kept (~1.8% of the dataset) on the last run where it worked. Keep the
   scraper but make a 403 abort the portal immediately instead of burning two
   28 s waits; drop the per-town × per-band product to towns only; or drop the
   portal. Whatever the answer, it is 16× on the whole-Poland matrix.
2. **The rest of Step 5** — the branch split has landed, so what is left is the
   region matrix (`max-parallel: 1–2`, staggered crons, per-region
   `RENTGEN_VERIFY_MAX`), the region picker with per-region counts, and
   per-region meta / OG / sitemap. Then **pilot ONE region end to end** —
   małopolskie or dolnośląskie.
3. **Step 6, the hosting ceiling** — decide before region #4, and the payload
   re-encoding is worth doing whichever way the hosting question goes.

## Superseded (2026-08-11, later) — the stack waits for otodom, and says what OLX served

*(Superseded as a pick-up pointer by the 2026-08-12 section above. Run
`31502042693` judged these: item 2 worked and item 1 did not — see there.)*

### Item 1 — teach the stack to wait for otodom

The 405s were fatal on first contact and nothing anywhere paced one search
against the next. Both halves fixed:

- **`net.py` retries `405`** alongside 429/5xx (`RETRY_STATUSES`). Otodom
  phrases its refusal as `405 Not Allowed`, not 429; the scraper only ever
  GETs URLs that answer GET, so a 405 here means "not you, not now". A refusal
  now costs up to ~30 s of capped back-off inside the request instead of
  killing the search.
- **`bands.subdivide` paces searches**: `SEARCH_PAUSE` = 4× the between-page
  delay (2.8 s at the CI default of 0.7), because a search is a burst of
  requests and only its pages were ever spaced apart. After a band the portal
  refused outright, `ERROR_COOLDOWN` = 40× (28 s) and **one** more walk of the
  same band — the retry's row *replaces* the failed one, so a recovered band
  can never be counted twice by `check_totals`. One retry, never a loop: a
  band still refused after the wait keeps its error row and the queue moves on.
- **`bands.Pacer` owns both, one per portal per run**, and the *unbanded*
  search goes through it too. That hole was worth closing on its own:
  `overflows` will not subdivide an error row — rightly, a filtered search
  fails the same way — so a refusal on page 1 of the first search leaves no
  bands to fall back on and the portal contributes nothing. That is precisely
  how run 31422141701 lost OLX on both types. Towns go through it as well.
- **The waiting is budgeted, not per search.** A portal refusing everything
  refuses the retries too, and otodom walks ~25 bands × 2 types while OLX walks
  ~120 towns — one unbudgeted 28 s cooldown each is an hour of sleeping against
  a cap with no headroom. `MAX_COOLDOWNS = 10` per portal caps it at ~5 min
  each, ~19 min across the four banded portals, and only when they are refusing.
- **OLX's town loop is paced the same way** — a town is a search, not a page.
- `delay=0` (tests, dev) disables all of it, so the offline suite stays instant.

Cost when nothing is refused: one 2.8 s pause per search — against the ~146
OLX searches and few dozen band searches of the green runs, roughly **+8 min**
on a 283–306 min run under a 350 cap. Worst case, a portal refusing every
band: +28 s and one extra walk each, bounded and self-limiting.

**What it should recover:** the seven dead bands (`400k-500k` … `1500k-3M`),
and with them otodom's 70.3% and the `price bands account for 6 821 ads but
the unbanded search states 18 314` warning, which was a consequence of them —
plus any portal that would otherwise have been lost whole to a page-1 refusal.
**What proves it:** those bands' coverage rows present in the next run, that
warning gone, otodom's `pct` up, and — if a portal refuses anything — the
`was refused — waiting Ns and asking once more` lines and what followed them.

### Item 2 — make the OLX failure legible

`olx.fingerprint(resp)` now goes into the log line whenever the state blob is
missing: HTTP status, body length, `<title>`, any challenge marker
(captcha / datadome / cf-chl / "just a moment" / …), and whether the body is
an OLX page at all. The old message guessed `(layout changed?)`; blocked and
re-skinned need opposite fixes, CI keeps nothing but the log, and this Pi
cannot re-probe OLX (it 403s us). The HTTP error path is now separate from the
parse path, so a transport failure and a 200-that-isn't-results no longer read
the same.

Tests: **169**, up from 159, still fully offline. Each new one was confirmed to
fail against the unfixed code before being kept.

### A third run landed while this was being written

`31468177600` (schedule, 07:14–12:31, **316 min**, published 30 005 properties
from 54 327 raw). Two things it settles:

- **otodom's 405 reproduces a third time, in the same shape.** `flat/300k-400k`
  died at page 7, then `400k-500k`, `500k-650k`, `650k-800k`, `800k-1M`,
  `1M-1500k` and `1500k-3M` each died on page 1 — seven bands, `3M+` served
  normally right after. Three runs, one pattern: this is the bug the push above
  targets, not a portal having a bad night. otodom finished at 70.7% with its
  unbanded flat search capped at our 200 pages (12 499 of 18 319).
- **OLX served normally** — 146 searches, 518 pages, 1 748 kept — so run
  31422141701's zero was a *transient* refusal, not a layout change. It also
  logged `olx house/bytom: failed after 1 page(s)`: a single refused town,
  which is now covered by the town-level retry.

### The 6 → 44 min swing is the delist sweep, not the history phase

Corrected against all three run logs — the phase table above mislabels it. Time
between the `archived ads ingested` line and the `delist sweep` line, which
brackets `delist.sweep` and nothing else:

| run | delist sweep | checked | confirmed gone |
|---|---|---|---|
| 31408840562 | **6 min** | 300 | 16 |
| 31422141701 | **44 min** | 300 | 1 |
| 31468177600 | **42 min** | 300 | 0 |

Same 300 checks every time. `sweep` walks them **sequentially**, each a
`session.get(..., timeout=20)` on the shared retry session: a URL that is
really gone answers at once (404, or a redirect onto an index page), while one
that is live, slow, or being throttled costs the full timeout and then the
retry ladder on top. The confirmed-gone counts (16 / 1 / 0) track exactly that
split — the phase's cost is response-time-driven, which is why it looked
"not input-driven". It is 12% of the budget for 300 HTTP HEAD-ish questions.

Three fixes, any of which would do, in order of preference: **parallelise it**
the way `photomatch` already does (8 workers ≈ 5 min); give it **its own lean
session** — a liveness probe wants no 429/405 retry ladder at all, "could not
tell" is a perfectly good answer and the record comes round again next run;
and/or a **wall-clock budget** like the photo phase's.

Related, and worth watching in the run just pushed: adding 405 to the retry
list makes a refusing portal more expensive *here* too. The 405s have only ever
appeared on search URLs, never on the `/pl/oferta/...` detail pages that this
sweep and the photo phase fetch, so this should cost nothing — but the delist
phase's wall time is the place it would show up.

Also from run 3: the photo phase took 93 min and **skipped 11 096** listings
with the budget exhausted (18 296 in run 1, 12 857 in run 2). Item 2 below is
about handing those listings the ~8 700 fetches the twins do not need.

### What to do next (in this order)

0. **Verify items 1 and 2 in the next run** — the three checks above, plus
   whichever fingerprint OLX logs if it refuses again. Everything below is
   still śląskie-only work, which is the ordering rule.
1. **Settle OLX's slot.** 31 min for 1 751 kept on the run where it worked,
   nothing at all on the run where it did not. Keep it, drop the per-town ×
   per-band product down to towns only, or drop the portal. Item 2's
   fingerprint is what makes the "nothing at all" case answerable. Whatever the
   answer, it is 16× on the whole-Poland matrix.
2. **Move `_link_twins` ahead of the photo phase.** The 8 712 twins are no
   longer an estimate, and a twinned morizon ad needs no photos at all — that
   is ~8 700 listings out of a 100 338 input where 12 857 got starved. It
   converts a confirmed win into budget.
3. **Cut the delist sweep** — diagnosed above, no longer a mystery: 42–44 min
   of the budget in two runs out of three, for 300 sequential URL checks that
   mostly answer "still live, slowly". Parallelise it, give it a lean session,
   or budget it; it is the single largest recoverable block of time in the run
   and the +8 min this batch spends comes straight back out of it.
4. **Step 5: split `data` per region.** At ~306 min/region the CI matrix — one
   350-min job per region — is the only shape that fits, and the branch split
   has to land before region #2 exists.

## Superseded (2026-08-11) — two green runs; the fixes worked, three new things did not

*(Its items 1 and 2 shipped in the section above; items 3–6 carried over. The
measurements below are what the next run is judged against.)*

### The pipeline is green and the data is live

| run | trigger | scrape | `!!` | published |
|---|---|---|---|---|
| 31408840562 | push (`f203ace`) | **283 min** | 17 | 32 962 properties from 54 517 raw |
| 31422141701 | schedule | **306 min** | 15 | 29 825 properties from 52 612 raw |
| 31468177600 | schedule | **316 min** | 18 | 30 005 properties from 54 327 raw |

`origin/data` reads `16c829d data: slaskie refresh 2026-08-11T02:16Z` — the
first write in 30 hours. The three fixes, scored:

| | before | after |
|---|---|---|
| OLX searches / phase time | 2 044 / 126–144 min | **146 / 31 min** |
| gratka `pct` (counts served, not new) | 55.6% | **87.3%** |
| false "short of total" lines | 20 | **0** |
| total `!!` | 1 948 | **15** |

The rest of the 2026-08-10 checklist, closed: `cache/phash_slaskie.json.gz` is
**15.2 MB** with the plain `.json` gone from the branch — it grew into the 5.3×
win rather than banking it (98 559 urls now) — and the `data` branch totals
151 MB.

**The deploy gate is in place but untested.** Nothing has failed since it
shipped, so it has never actually had to skip a deploy. It stays unproven until
a scrape fails.

### Step 3 verified: the gratka↔morizon merge works in production

`('gratka','morizon')` is no longer zero. Source combinations across the
published 29 825 properties:

| combination | properties |
|---|---|
| `gratka+morizon` | 4 648 |
| `gratka+morizon+nieruchomosci-online` | 2 131 |
| `gratka+morizon+nieruchomosci-online+otodom` | 1 350 |
| `gratka+morizon+otodom` | 583 |
| **total twin-merged** | **8 712** |

Against an estimate of 7 089. morizon-only is down to **1 344** and gratka-only
to 811, from ~9 500 morizon singletons that merged with nothing. The base64
thumbnail key is identity, and it holds at scale.

### Three things the green runs exposed

- **otodom 405s, and nothing in the stack makes it wait.** Band `300k-400k`
  dies at page 5 with `405 Client Error: Not Allowed`, and then every one of the
  seven bands after it fails on page 1 — `400k-500k` through `1500k-3M`, all of
  them, in both runs. `net.py`'s retry `status_forcelist` is
  `(429, 500, 502, 503, 504)`: **405 is not in it**, so the refusal is fatal on
  first contact with no backoff, and `time.sleep(delay)` only paces *pages
  within* a search, never one search against the next. The very next search
  (`3M+`) succeeded, so whatever trips it is transient — the code simply has no
  mechanism to wait it out. The `!! otodom flat: price bands account for 6 821
  ads but the unbanded search states 18 314` warning is a *consequence* of this,
  not a second bug: seven dead bands have nothing to contribute to the sum. Net
  effect: otodom is the largest portal and sits at **70.3%**, its main search
  still truncated at our 200-page cap (12 509 of 18 314) — the exact hole
  Step 2's bands were built to close.
- **OLX served nothing on the second run.** `OLX: __PRERENDERED_STATE__ not
  found (layout changed?)` on page 1 of *both* searches, 50 seconds after run 1
  finished walking 518 OLX pages — so almost certainly a block wearing a
  layout-change error message. The code cannot tell those two apart, and this Pi
  cannot settle it (OLX 403s this IP; see the portal-probing note). Run 1 is
  therefore the only honest measurement of the fixed phase: **31 min for 1 751
  kept listings**.
- **The budget has no headroom and does not behave.** 283 and 306 min against
  the 350 cap — and run 2 was 23 min *slower* while OLX contributed literally
  nothing, because the history phase went **6 → 44 min** on comparable input
  (6 100/47 828 vs 6 484/47 726 archived ads ingested). Whatever governs that
  phase's cost, it is not the input size, and it swallowed half the spare budget
  on its own.

Per-phase, both runs, in minutes:

| run | otodom | olx | gratka | morizon | n-online | photo | history | delist | RCN |
|---|---|---|---|---|---|---|---|---|---|
| 31408840562 | 12 | 31 | 19 | 21 | 81 | 100 | 6 | 9 | 4 |
| 31422141701 | 13 | **0** | 20 | 22 | 89 | 109 | **44** | 8 | 1 |

### Where its list went

Items 1 and 2 (`405` + between-search pacing; the OLX fingerprint) shipped —
see the section at the top of this file. Items 3–6 carried over unchanged and
are now that section's 1–4.

## Done (2026-08-10) — the bands batch put CI over the timeout; three fixes

*(Superseded as a pick-up pointer by the 2026-08-11 section above. The run
this commit triggered landed at 283 min and published; everything below was
confirmed.)*

### The pipeline had been red for three runs, and the site did not show it

Every `Update listings` run after the 2026-08-09 bands batch was killed at the
5h50m timeout, so none of them reached `Push refreshed data`. `origin/data`
still read `data: slaskie refresh 2026-08-09T11:03Z` — **the last pre-bands
run** — while `Deploy site` kept going green every few hours.

| run | trigger | otodom | **olx** | gratka | morizon | n-online | scrape | photo input |
|---|---|---|---|---|---|---|---|---|
| 31302206296 | push (7d6424e) | 14 | **132** | 18 | 20 | 75 | 259 min | 101 961 |
| 31329965895 | schedule | 14 | **126** | 18 | 20 | 76 | 254 min | 101 992 |
| 31367424054 | schedule | 13 | **144** | 20 | 22 | 83 | 283 min | 101 853 |

Identical three times over — reproducible, not a flaky portal. The scrape alone
took 4–4¾ h of the 5h50 budget and the photo phase never finished.

- [x] **OLX read an empty search as a refusal, then subdivided it.** `_walk`
      decrements `page` on an empty page and asks `total_pages > page`; on an
      empty *first* page that is `1 > 0`, so `stopped` became `portal_cap` —
      which `bands.overflows` treats as overflow. Every empty town was bisected
      into nine seed bands, each equally empty, each bisected again to
      `MAX_DEPTH`: `olx flat/kozy/1375k-1437k` is a village of 4 000 being asked
      for its 1.4M flats. **1 890 of the run's 1 948 `!!` lines were this one
      bug**, and OLX spent 2 044 searches / 2 404 requests — roughly 110 of its
      144 minutes — to keep 1 730 listings. A real refusal still states
      `visibleElements`, which is what now tells the two apart. Pinned from both
      sides by `test_an_empty_town_is_not_subdivided` and
      `test_an_empty_page_the_portal_says_has_ads_is_still_a_refusal`.
- [x] **gratka/morizon never reported what they were served.** The 2026-08-09
      served-vs-kept fix landed for otodom and OLX only, so `coverage.seen_by`
      fell back to the *new* count for the other two — and a band's new count is
      legitimately a fraction of its stated total, because the unbanded pass
      already took the overlap. Result: `gratka flat/slaskie/0-200k: collected
      82 of 536 (15.3%) — subdivide it`, for a band that had walked all 16 of
      its pages and seen every ad in it. 20 false lines per run, and an
      understated `pct` (gratka read 55.6%). Both now pass `served=`.
- [x] **A cancelled scrape no longer deploys.** `deploy.yml`'s `workflow_run`
      trigger fires on `completed` with no conclusion filter, so each of the
      three timeouts triggered a green deploy that republished the same stale
      `data` branch — the reason a 30-hour-old dataset looked healthy. The job
      now runs only when the scrape actually succeeded; push and manual dispatch
      are unaffected, and a skipped deploy leaves the previous Pages deployment
      live exactly as before.
- [x] Tests: **156 → 159**, still fully offline. Each new test was confirmed to
      fail against the unfixed code before being kept.

### What the failed runs did establish

Worth having even though nothing was published — these are measurements, not
predictions, and two of them contradict the 2026-08-09 plan.

- **The n-online dedupe did not do what Step 3 assumed.** Keying on the ad id
  does make most towns exit early (only `flat/katowice` still hits the 200-page
  cap, and the phase walks 1 696 pages rather than every town to the cap), but
  the phase went **75 → 83 min** and the listing count did not move: 58 613 →
  58 845. The cross-town duplication is at *property* level downstream, not at
  ad-id level. **The photo phase's input therefore went up, 90 341 → 101 853** —
  the opposite of the halving Step 4's photo-budget item is written around.
- **otodom improved but not as far as predicted**: 48.7% → 69.9% of its stated
  total (the note expected the high 90s), with 8 truncated searches left.
- **gratka and morizon served 12 354 and 12 355** — one database behind two
  frontends, exactly as Step 3 argued, though `_link_twins` runs after the photo
  phase so the 7 089 merges still have not actually run in CI.
- **OLX's cost/benefit is now a real question**: 144 minutes for 1 730 kept
  listings, because most of what it serves is Otodom-syndicated and dropped by
  design. Fixing the empty-search bug removes ~110 of those minutes; whether the
  remainder earns its place is Step 4 work.

Projected budget with the OLX fix in: ~170 scrape + ~100 photo (budget-bounded,
so it does not scale with input) + 20 history + 8 delist + 8 RCN ≈ **306 min**
against the 350 cap. It should fit. It has no headroom, which is the whole of
Step 4's case.

**What to check on the run this commit triggers** — every line answered in
the 2026-08-11 section above:
- It has to **finish** — `Push refreshed data` running at all is the headline,
  and `origin/data` should stop reading `2026-08-09T11:03Z`.
- OLX should drop from ~140 min to ~30 and from 2 044 searches to a few dozen.
  The `!!` count should fall from 1 948 to something a person reads.
- `('gratka','morizon')` **must stop being zero** in the source-pair histogram —
  the Step 3 regression test, still unrun since the merge shipped.
- Published count somewhere around 45–60k: up from the bands, down ~7 000 from
  the morizon merge. If morizon still shows ~9 500 singletons, `_link_twins` is
  not firing.
- `cache/phash_slaskie.json.gz` at ~12 MB, plain `.json` gone from the branch.
- Photo phase: how many listings it skipped with the budget exhausted, out of
  ~101 000. That number is the input to the Step 4 decision.
- If it still overruns, `RENTGEN_BANDS=0` is the fastest lever, then
  `RENTGEN_NOL_TOWNS`.

## Done (2026-08-09) — rollout steps 2, 3 and 4a, plus three defects found on the way

*(Superseded as a pick-up pointer by the 2026-08-10 section above.)*

Every number here was measured against the real CI run or the real published
data.

### What run 31281062431 proved (the acceptance test for steps 0+1)
4 h 16 m, success. Both steps confirmed, and the dataset roughly doubled:
**18 385 → 34 137 properties**.

| portal | before | after | portal states | pct |
|---|---|---|---|---|
| otodom | 1 482 | **11 199** | 23 002 | 48.7% |
| gratka | 1 750 | **9 505** | 12 369 | 76.8% |
| morizon | 1 750 | **9 505** | ≥11 000 | 86.4% |
| olx | ~470 | **1 519** | 13 567 | 11.2% |
| n-online | 11 089 | 11 172 | — | — |

Phases: scrape 123 min (otodom 12, olx 18, gratka 9, morizon 10, **n-online 75**),
photo 96 min (**15 350 skipped, budget exhausted**), history 20, delist 8, RCN 8.
`cache/phash_slaskie.json` reached **62.86 MB**, and the log carried **126 `!!`
warnings**, nearly all false.

Those numbers reordered the plan. Three defects were sitting under Step 2 that it
would have multiplied, so they shipped in the same batch.

- [x] **Step 2 — price-band subdivision (`scraper/bands.py`).** One helper, four
      portals. The unbanded search runs first and is kept (priceless ads live
      only there); while a search's stated total exceeds its portal's reachable
      window — otodom 7 200, gratka/morizon 7 000, olx 1 000, all named
      constants in `bands.WINDOW` — the price range is bisected and the halves
      walked, merging by URL. Bands are half-open `[lo, hi)` so a boundary price
      lands in exactly one band. `check_totals` asserts the seed bands sum to at
      least the unbanded total, which is how a portal's price filter silently
      dropping ads gets caught. Additive throughout: a bad band costs one
      request and can never lose a listing already held. `RENTGEN_BANDS=0`
      disables it. otodom also gained **`&limit=72`** (515 → 258 pages).
      gratka's and morizon's parameters were **re-probed live 2026-08-09** and
      answer exactly as recorded; otodom's are the 2026-08-08 measurements, as
      its edge now 403s this IP after a probe burst.
- [x] **A real bug the band work surfaced.** gratka/morizon broke their page loop
      on an empty *batch* (nothing new on this page) rather than an empty *page*.
      A band re-sorts the results, so its first pages are usually ads the
      unbanded pass already took — every band would have quit at page 1 and
      silently lost everything behind it. olx/otodom already broke on the raw
      page and were fine. Pinned by
      `test_a_band_whose_first_page_is_all_duplicates_keeps_going`.
- [x] **An errored search no longer triggers subdivision.** A request that failed
      fails the same way with a price filter on it; treating it as overflow made
      one broken search recurse into dozens. Caught by the existing OLX tests
      the moment bands were switched on.
- [x] **Step 3 — the gratka↔morizon duplicate: worse than estimated, and now free.**
      In the published data morizon appeared in **zero** merged source-pairs —
      9 501 of its 9 505 cards were singletons and **not one carried a photo
      hash**. Confirmed live: galleries moved to `img1.staticmorizon.com.pl`,
      which `photomatch._morizon` never matched.
      - **The merge key needs no fetching at all.** Both portals serve
        `<host>/thumb/<base64>/<rendition>/<slug>.jpg`, and the base64 decodes to
        the same `d-gr.cdngr.pl/kadry/…/<gratka ad id>_<photo>.jpg` origin — which
        a morizon *card thumbnail on the search page* already carries. They are
        one database behind two frontends. Measured on the published data:
        **7 089 of 9 501 morizon cards — 100% of the `gr-ogl` flavour — resolve
        to a gratka ad we already hold**, and re-running `normalize._link_twins`
        over the real records links exactly those 7 089. That is **20.8% of
        everything published**. The other 2 383 are `gr-col`, a different id
        space, and still go through photos — which now work.
      - Two traps a plain regex fix walks into, both now pinned by fixtures
        trimmed from the live pages: **blog teasers ride the same `/thumb/` path
        and their slug also ends `.jpg`**, so a host-only pattern hashes stock
        article art; and the first five gallery URLs are the xs/s/m/l/og
        renditions of **one** photo, so `MAX_IMAGES = 5` was hashing a single
        photo five times on *both* portals. Hashing is now per distinct origin.
      - The old `test_morizon_has_photo_extractor` asserted against two invented
        URLs, which is exactly why it stayed green while morizon returned nothing
        for months. It reads a real page now.
- [x] **n-online was burning 75 of the 123 scrape minutes to gain 83 listings.**
      Its `seen` set keyed on the URL, but every town sub-domain serves its
      neighbours' offers under its own hostname — one ad arrives as
      `gliwice.…/26859971.html` *and* `katowice.…/26859971.html`. Every page
      therefore looked fresh: **58 613 rows collapsed to 11 172 properties** and
      the `dup_pages` early exit could never fire, so every town ran to the cap.
      Keyed on the ad id (already extracted as `source_id`) it dedupes and stops
      early. This also more than halves the photo phase's input — of the 90 341
      listings hashed last run, 47 441 were n-online duplicates.
- [x] **Step 4a — phash cache: gzip + base64-packed hashes.** v1 wrote each
      256-bit hash as a ~78-character decimal string in plain JSON. Verified on
      the real production file: **65.92 MB → 12.35 MB (5.3×)**, round-trip clean
      on all 72 090 entries, v1 read transparently and deleted on save so it
      stops being pushed. Clear of the 50 MB warning and of the 100 MB hard limit
      that would fail the push outright.
- [x] **Negative photo caching.** `put()` no-op'd on empty results, so all 9 505
      morizon detail pages were re-fetched every single run, always returned
      nothing, and were charged to the photo budget that was starving 15 350
      other listings. An empty result is now a miss: retried `MISS_RETRIES` (3)
      times, then believed for `MISS_RECHECK_DAYS` (7) so a portal that starts
      serving photos again is picked back up. Budget-skipped listings are
      explicitly **not** recorded as misses — otherwise a few starved runs would
      teach the cache that half the region has no photos.
- [x] **The 126 false warnings.** `coverage` now records what a portal *served*
      alongside what we *kept*, and judges truncation on the former. OLX town
      searches read "collected 3 of 63" only because we drop Otodom-syndicated
      ads by design. `pct` now means "how much of the portal did we get to see";
      the kept count rides alongside as `listings`.
- [x] Tests: **119 → 156**, still fully offline. New `tests/test_bands.py` (12),
      `tests/test_photomatch.py` (13), `tests/test_cache.py` (8), plus the
      coverage and n-online cases. The band tests drive the real scraper page
      loops through a fake portal that honours the price parameters over **one
      global ad set**, so "the bands recovered everything the wall hid" is a real
      assertion — they recover the full stated total rather than listings the
      fake invented.

**What to check on the next CI run:**
- `coverage.by_source.*.pct` should jump: otodom 48.7% → high 90s,
  gratka/morizon 76.8/86.4% → ~100%, and olx should stop reading 11.2% now that
  it counts served ads rather than kept ones.
- The published count moves two ways at once — **up** from the bands, **down** by
  ~7 000 from the morizon merge. Somewhere around 45–60k is the expectation. If
  morizon still shows ~9 500 singletons, `_link_twins` is not firing.
- **`('gratka','morizon')` must stop being zero** in the source-pair histogram.
- Scrape time: n-online should collapse from 75 min while the other four grow;
  the photo phase's input should drop well below 90 341.
- `cache/phash_slaskie.json.gz` should appear at ~12 MB and the plain `.json`
  disappear from the data branch.
- If the run approaches the 350-min timeout, `RENTGEN_BANDS=0` is the fastest
  lever, then `RENTGEN_NOL_TOWNS`.

## Done (2026-08-08, late) — whole-Poland steps 0 + 1: the cap, and the truth

*(Superseded as a pick-up pointer by the 2026-08-09 section above — steps 2 and
3 have since shipped. Kept for the measurements.)* Steps 0 and 1 are done and
described here; every number they rest on was measured and is written down in
the plan section below.

- [x] **Step 0 — CI no longer pins the page cap.** `update.yml` set
      `RENTGEN_MAX_PAGES: "50"` in the scrape step, silently overriding the 200
      default in `main.py`. Every "we raised the cap" measurement so far was a
      local one; CI never ran it. The env var is gone from the workflow (with a
      comment saying why), so the default lives in exactly one place.
- [x] **Step 1 — every portal's own count is now recorded and compared.**
      A stop reason alone lies: gratka 404s past page 200 *identically* to how
      it 404s past a genuine last page, so a truncated search looked finished.
      Each scraper now reads the portal's stated total and the coverage row
      carries it:
      - **otodom** `pagination.totalItems` — the old code read `totalResults` /
        `count` off `searchAds`, neither of which exists, so `portal_total` was
        null on every row ever written.
      - **gratka** "9856 ogłoszeń" from the meta description (exact).
      - **morizon** "ponad 9000 ogłoszeń" — rounds to whole thousands, so it is
        stored as a LOWER bound (`total_is_min`): below it proves truncation,
        above it proves nothing. Shared parser: `normalize.stated_total()`.
      - **olx** `visibleElements` (5 503) vs `totalElements` (1 000 = its cap).
- [x] **Two silent truncations became loud.** `gratka`/`morizon` classify a
      clean-looking 404 as `portal_cap` when the collected count falls short of
      the stated total (5% slack, `coverage.COMPLETE_ENOUGH`); `olx` classifies
      `visibleElements > totalElements` as `portal_cap`, **which is the trigger
      the per-town subdivision built on 2026-08-08 was waiting for — it had
      never once fired**, because OLX states its cap as a smaller total plus a
      matching `totalPages: 25` and the walk therefore ended as "end".
- [x] **`meta.json` → `coverage.by_source` gains `portal_total` + `pct`**, and
      the run log prints one `coverage <source>: N listings … of M the portals
      state (P%)` line per portal. Two runs are now comparable by one number
      instead of a diff of stop reasons. `pct` is a FLOOR, not a defect rate:
      each scraper filters while parsing (otodom drops INVESTMENT bundles, olx
      drops Otodom-syndicated and price-on-request ads), so a complete search
      legitimately lands below 100%.
- [x] Tests: `tests/test_coverage.py` +8 (119 total, offline) — the gratka
      404-wall case, morizon's lower-bound total (including "collected more
      than the rounded total" staying silent), the OLX stated-cap case and its
      subdivision, and `stated_total()` against both portals' real meta strings.
- [x] `timeout-minutes` 300 → 350: the first run after this is the heaviest one
      the project has had (uncapped pages + OLX subdivision firing for the first
      time + a cold phash cache for everything newly visible).

**What to check on the next CI run** (the acceptance test for both steps, and
the input to Step 2). That was **Actions run 31281062431** — it passed, and its
numbers are in the 2026-08-09 section at the top of this file. Predictions vs
what actually happened:
- `meta.json` → `coverage.by_source.*.pct` — the first real coverage numbers.
- gratka/morizon should report `portal_cap` at ~7 000 of 9 856 (their 200-page
  wall), otodom `cap` at 200 of 515 pages, olx `portal_cap` **plus 60 town
  subdivision rows**.
- Run time: the scrape phase was 60 min; expect meaningfully more (n-online's
  per-town cap also rose from 50 to 200 pages). If the job approaches the 350-min
  timeout, drop `RENTGEN_NOL_TOWNS` or give n-online its own smaller cap.

## Done (2026-08-08) — overflow detection + subdivision (rollout step 1)
- [x] **The caps were ours, not the portals'.** Probed gratka directly:
      `domy/slaskie` reports **2509 ogłoszeń**, paginates to **page 72** and
      404s on 73 — no portal-side limit at all. Same shape on morizon. So the
      old `RENTGEN_MAX_PAGES=50` was the entire truncation. Raised the default
      to **200** and measured it live: gratka houses **1 751 → 2 508 (+757)**,
      stop reason flipping from `cap` to `end` at page 72, matching the
      portal's own count. The scrapers all terminate on the portal's end, so a
      generous cap costs nothing where it isn't needed.
- [x] **`scraper/coverage.py`** — every search records why it ended: `end`
      (portal ran out), `cap` (we cut it off), `portal_cap` (portal refused to
      go deeper), `error`. Folded into `meta.json` → `coverage` and printed as
      a warning per truncated search, so truncation stops being something you
      have to infer from suspiciously round counts. Otodom and OLX state their
      own `totalPages`, which is what makes "is the cap still binding?"
      answerable from each CI run.
- [x] **OLX subdivision.** OLX is the one portal that caps *itself* — it stops
      serving at page 25 while still claiming hundreds of `totalPages`, and no
      value of `RENTGEN_MAX_PAGES` helps. A capped OLX search is now re-run per
      town (same slug position as the region: verified on the reachable sibling
      portals, `gratka.pl/nieruchomosci/domy/gliwice` and
      `morizon.pl/domy/gliwice/` both answer) and merged by URL. **Additive by
      design** — region results are kept and town results merged in — so a
      wrong slug costs one request and can never lose a listing.
      A test caught the detection bug this hid: OLX signals its cap with an
      *empty* page, which broke the loop before the cap check ever ran.

Still open from this round:
- [x] **Does otodom still overflow at 200 pages? YES, by 2.5×** — answered
      2026-08-08 evening by probing otodom directly from the Pi (it now answers
      a residential IP; the old 403 is gone). Śląskie flats:
      `pagination.totalItems = 18 505`, **515 pages**. See the rewritten
      whole-Poland plan below — this, plus the fact that CI never actually used
      the new 200-page default, reorders everything again.
- [ ] **Watch the run time and the photo budget.** More listings means more
      gallery hashing; `RENTGEN_PHOTO_BUDGET_MIN=90` absorbs it over several
      runs by design, but the first run after this change will be heavy.
      Status after the 2026-08-08 18:00 UTC run: the photo phase used **80 of
      the 90 minutes** and the budget is now the binding constraint (2 h 40 m
      run: 60 min scrape, 80 min photo, 20 min history/RCN/geo/write).

## Done (2026-08-08) — de-Gliwice-ing (whole-Poland rollout step 2)
- [x] **`normalize.CITY` deleted** — dead constant, referenced nowhere.
- [x] **n-online town list is per region now.** The portal has no region-wide
      search, so it needs a town list — and (probed 2026-08-08) it publishes
      nothing to build one from: `/sitemap.xml` 404s, robots.txt declares no
      sitemap, and its region landing pages name no towns at all. So
      `resolve_towns()` derives the list from the localities the other four
      portals already returned this run (they run first in `SOURCES` precisely
      for this, so a brand-new region works on its FIRST run), ranked by
      listing count, capped at `RENTGEN_NOL_TOWNS=60`, cached in
      `cache/nol_towns.json` so a dead portal can't wipe it. Śląskie keeps its
      hand-curated seed list, which also wins on spelling. `town_name()`'s
      `slug.title()` fallback is gone — an unmapped slug now yields no locality
      rather than inventing "Dabrowa-Gornicza" and splitting dedupe keys.
      `slugify()` is tested against every seeded sub-domain.
- [x] **Dashboard anchor city is per-region config.** `REGION_CONFIG` in
      `app.js` carries the label, the anchor city (with its Polish genitive for
      "od Gliwic") and the district→city fold that used to be
      `GLIWICE_DISTRICTS`. A region with no anchor hides the distance control
      instead of silently filtering everything out. Page title/h1 relabel for
      non-śląskie regions (static meta stays śląskie until a region picker
      exists). ⚠️ Found while testing: `const REGION` was declared *below* the
      new config that reads it — temporal dead zone, the page died on load.
      Caught by running the real `app.js` in node, not by `node --check`.
- [x] **`distOf` prefers the listing's own `ll`** over the ~90-entry
      `TOWN_COORDS` table, which closes the "Precise distances" backlog item:
      the radius filter now works in any region, and coverage went 82.2% →
      84.9% in śląskie. `TOWN_COORDS` stays as the fallback purely because
      archive entries still have no `ll`.
- [x] **Dropped the `startswith("Gliwice")` locality fold** in gratka/morizon.
      Checked against live data first: no locality starting with "Gliwice"
      other than "Gliwice" exists, so it never fired — and generalising it
      would corrupt real villages ('Żarki-Letnisko' is not 'Żarki', 'Góra
      Włodowska' is not 'Góra'). Deleted rather than generalised.
- [x] Stale "scraper for Gliwice" module docstrings corrected to region-wide.

Found while doing this, NOT fixed (own item):
- [ ] **Powiat names sit in the `locality` field of 2 586 listings.** Always the
      lowercase adjectival form — `cieszyński` (406), `bielski` (372),
      `tarnogórski` (292), 17 in total — so a powiat shows up as a "town" in the
      dashboard's town multi-select, and those listings are geocoded to a powiat
      rather than a place. `resolve_towns()` now skips them (case is a reliable
      filter: all 318 real localities are capitalised), but the underlying
      breadcrumb parsing in gratka/morizon still lets them through. Fix where
      `_locality()` picks the last segment: if it is lowercase, fall back to the
      segment before it.

## Done (2026-08-08) — "Sprzedane wg RCN shows nothing"
Reported as a broken filter; it was not broken. The real findings, in order:
- [x] **The filter works** — the deployed `app.js` run against the live
      `archive.json` returns 43 rows and renders them. It looked dead because
      **none of the 43 are in Gliwice**, and the town filter persists between
      visits (localStorage + URL), so a Gliwice-shaped view is always empty.
- [x] **Root cause: the register, not the tool.** RCN is fed by each powiat's
      own office. Gliwice's newest deed is **2026-02-25** — 164 days stale —
      while Katowice/Częstochowa/Bytom sit at 18–19 days and neighbouring
      Knurów (a different office: powiat gliwicki, not the city) is current.
      A sale is confirmed by a deed dated around when the ad vanished, so **no
      Gliwice listing can ever be confirmed sold** until that office catches
      up. Both RCN layers agree on the date, so it is the office, not a layer.
- [x] **`rcnstats.py` publishes freshness**: `towns.<t>.deeds {last, lag}` for
      every benchmarked town plus a `stale[]` list of laggards. Threshold
      calibrated on the real snapshot (479 towns): `STALE_MIN_DEEDS = 1000`
      gives 7 real towns; at 50 it was 64 hamlets with no market at all
      (Paczynka's last deed is 2021) and the cities were buried. Register
      casing is normalised too — it ships `RYBNIK` next to `Rybnik`.
- [x] **Surfaced in three places**: the negotiation block ("powyższe liczby są
      starsze niż wyglądają"), the Statystyki chart note, and the empty
      *Sprzedane wg RCN* view.
- [x] **Empty views now name the culprit filter.** On an empty grid the filter
      is re-run with each dimension relaxed and the ones that would restore
      results become one-click buttons with their counts. Chip-clearing was
      factored into `clearFilter()` so chips and the empty state share it.
- [x] **Counts on the archive segments** (`Archiwum · 1 534`,
      `Sprzedane wg RCN · 43`) from `meta.json`, dropping to the filtered count
      with a "0 z 43" tooltip when your other filters exclude everything.

Still open from this round:
- [ ] **Gliwice cannot confirm sales until the powiat reports.** Nothing to fix
      in code — worth re-checking `rcnstats.json`'s `stale[]` every few weeks.
      If Gliwice is still ~6 months behind by 2026-10, the *Sprzedane wg RCN*
      view is decorative for this region and could be folded into *Archiwum*.

## Done (bug sweep — 2026-07-11)
Full-codebase review (4 areas: scrapers, pipeline, RCN/stats, dashboard);
every fix below is covered by `tests/test_bugfixes.py` (90 tests total).
- [x] **delist**: bare `zakończone` marker falsely delisted live ads whose
      description contains the word (now anchored to ogłoszenie/oferta);
      the sweep ran right after `observe_archived` and un-set the `delisted`
      flag the archive evidence had just set (`last_seen` now counts only live
      observations; "resurfaced" clear only when live *today*); sorting sweep
      candidates could crash on `(seen, url)` ties (dict comparison).
- [x] **morizon had no photo extractor** — an entire portal (~3.5k raw ads)
      never got gallery hashes, so cross-portal dedupe/relist detection was
      dead for it; also added to `SOURCE_RANK`.
- [x] **history**: observations now record EVERY portal offer of a merged
      card, not just (primary url, min price) — the old scheme made a primary
      flipping portals look like a relist and the cheapest offer vanishing look
      like a price change (relisted on real data: 7 952 → ~1 450, the rest were
      artifacts). Relist now = an old URL went quiet BEFORE a live URL first
      appeared. Timeline labels cross-portal postings "listed", not "relist".
- [x] **storage safety**: `history.json` (83 MB) written atomically
      (tmp+rename) and a CORRUPT store now fails the run loudly instead of
      silently restarting history from zero and overwriting months of data;
      phash/geo/RCN caches also write atomically.
- [x] **scrapers**: OLX state regex ended at the first `";` even inside an
      escaped string (dropped the rest of the category); Otodom stopped
      paging on a page of INVESTMENT-only results; n-online stopped a town's
      pagination on the first all-duplicate page (towns cross-list each other)
      and `slug.title()` leaked diacritic-less fake localities ("Dabrowa-
      Gornicza"); gratka/morizon stripped the literal string "śląskie" from
      breadcrumbs — any other `RENTGEN_REGION` made the voivodeship the city.
- [x] **RCN**: `_fold` didn't collapse whitespace ('Bielsko - Biała' town key
      got 0 deed candidates); building numbers compare space-free ('13 A' ==
      '13A'); declension tolerance no longer equates distinct streets
      (Górna != Górnika); snapshot dedup is per WFS page so field-identical
      mirrored deeds aren't collapsed; rcnstats window is real calendar
      months (was 720 days); marketstats counts withdrawals whose week has no
      live observation; dedupe area-unify can no longer wipe areas to null;
      card zł/m² now belongs to the cheapest offer shown as the price.
- [x] **dashboard**: XSS — scraped title/district/image/urls reached
      `innerHTML` unescaped in cards (portals are attacker-controlled input);
      inline `onclick="window.open('${url}')"` was JS-injectable → delegated
      `data-href` handler; the 📌 pin command is now single-quoted for the
      shell (street names with `$(...)` could execute in the user's
      terminal); "Najnowsze" sort parses the three portal date formats
      (string-compare mis-sorted within a day and sank 48% of listings);
      market/owner filters are ignored in Archiwum (fields don't exist
      there); DOM-histogram tooltip no longer shows "undefined".

## Done (storage switch — 2026-07-11)

Data + caches no longer live in main's git history (`history.json` was 83 MB
and marching toward GitHub's 100 MB hard limit at ~40 MB of new history per
refresh). Now:
- [x] **Orphan `data-<region>` branch**, force-pushed as a SINGLE commit per
      run, holds exactly that region's data/per-region caches plus the two
      intentional shared-file caches. Main carries code only. The pre-split
      `data` branch remains a deploy/seed fallback.
- [x] **Region = directory** from day one: `site/data/slaskie/{listings.json,
      history.json.gz, archive.json, meta.json, rcnstats.json, stats.json}`,
      caches `cache/phash_<region>.json` + `cache/rcn_<region>.json.gz`
      (`geo_cache.json` stays a shared file; every new/used production key
      includes the regional TERYT prefix, while retained pre-P1 keys are inert).
      Dashboard + Statystyki read `data/<region>/` from
      stable `region/<slug>/` pages; legacy `?region=` links redirect.
- [x] **`history.json` gzipped** (~8-10x smaller; only the pipeline reads it;
      pre-gzip plain file picked up once as a fallback). Deploy strips it from
      the Pages artifact.
- [x] **update.yml** pulls the data branch before scraping, force-pushes the
      refreshed snapshot after; **deploy.yml** overlays main's `site/` with
      the data branch's `site/data/`; `.gitignore` blocks data on main;
      README documents the new local-scrape flow.
- [ ] **Shrink main's history once** (drops the repo ~95 MB -> a few MB):
      `git filter-repo --invert-paths --path site/data --path cache` +
      force-push. ON HOLD until the owner confirms local clones have nothing
      unpushed (every clone must be re-cloned afterwards). Nothing breaks if
      deferred — the repo just stays fat.

Follow-up (separate, still important): the **Payload split** backlog item —
`listings.json` (44 MB, `cache: no-store`) → slim grid index + lazy detail
shards + hashed filenames. Do it before adding a second region.

## Done (cena vs transakcje RCN — 2026-07-07)
- [x] **`scraper/rcnstats.py` -> `site/data/rcnstats.json`** (~21 KB): per-town
      / size-bucket / market (p|w) deed zł/m² benchmarks (n, med, p25, p75)
      from the RCN snapshot, last 24 months, min 5 deeds per bucket. Flats
      only — the budynki layer's price is usually a building-value fragment
      (voivodeship median ~200 zł/m²), so house benchmarks would mislead.
- [x] **Ask-vs-sold gap stats** (same file): properties we watched vanish AND
      matched to a deed give median (deed − last ask)/ask % and median days on
      market, per town + voivodeship-wide. |gap| > 40 % pairs dropped as
      mismatches. Currently 0 pairs — history has `kind:"past"` sales but only
      5 delisted records so far; fills in as the delist sweep + RCN matching
      run forward. The dashboard hides the stat until data exists.
- [x] **Dashboard**: "vs transakcje RCN: +18 %" line on every card with a
      benchmark (63 % of listings today; tooltip = median, n, bucket, window;
      ppm outside 500–40 000 zł/m² excluded as typos/udział), expandable
      **"💬 Argumenty do negocjacji"** block (deed benchmark + p25–p75 range,
      how sales end locally, days on market / relist / cuts), new sort
      **"Cena vs transakcje RCN ↑"**, header line with the global gap stat.
- [x] `meta.json` gets `rcn_stats: {towns, gap_pairs}`; tests in
      `tests/test_rcnstats.py` (61 total, offline).

## Done (Statystyki page — 2026-07-07)
- [x] **`scraper/marketstats.py` -> `site/data/stats.json`** (~32 KB, builds in
      ~2 s): weekly series from history observations (active supply, median
      asking zł/m², new / confirmed-withdrawn / price cuts — global per type +
      active/median for the 40 busiest towns) and monthly RCN deed series
      since 2018 (median transacted zł/m² + n for flats, wtórny/pierwotny
      globally, wtórny per town; months with < 5 deeds -> null). Plus
      days-on-market histogram and % of listings that ever cut price.
      Developer records excluded from history-derived series.
- [x] **`site/stats.html` + `stats.js` + `stats.css`** — separate dashboard,
      linked from the main header. Hand-rolled responsive SVG (no libs):
      ceny ofertowe vs transakcje RCN line chart (the two-line chart nobody
      else has), weekly supply, small-multiple bars for nowe/wycofane/obniżki,
      DOM histogram, stat tiles (incl. the rcnstats gap stat when it exists).
      Town select + Mieszkania/Domy + 2 lata/5 lat/max range. Charts follow
      the dataviz method: validated 3-slot palette (light+dark), legend +
      end-of-line direct labels, crosshair/per-bar tooltips, "tabela danych"
      under every chart, nulls break lines (deed registry lags months —
      e.g. Gliwice powiat stops at 2026-02 in the current snapshot).
- [x] Tests `tests/test_marketstats.py` (67 total, offline). Note: weekly ask
      medians for the first 1–2 weeks are coverage-ramp artifacts (portals
      were added over days), not market moves.

## Done (map view — 2026-07-07)
- [x] **`scraper/geo.py`.** Listings carry no coordinates, so unique
      locality / locality+street strings are geocoded through GUGiK's free
      UUG service into a committed cache (`cache/geo_cache.json`; misses
      cached too, retried after 60 days). EPSG:2180 -> WGS84 in pure Python
      (inverse transverse Mercator, no pyproj). Budgeted: towns first (one
      lookup covers hundreds of listings), then streets by demand,
      `RENTGEN_GEO_MAX` (500) new lookups per run — street precision keeps
      improving run over run. Listings gain `ll: [lat, lon]` +
      `llp: "s"|"t"` (street/town); `meta.json` gains `geocoded`.
- [x] **Dashboard map (🗺 Mapa toggle).** Leaflet + markercluster, lazy-loaded
      from unpkg only when first opened (main page load unchanged). Shows the
      *current filtered view*; markers colored by the "vs transakcje RCN" gap
      (green below / gray par / red above / blue no data), legend with counts,
      popup = mini card with photo, price, gap and link. Town-precision pins
      get a deterministic ≤400 m scatter (seeded by URL) so they cluster
      instead of stacking on the centroid. Dark-mode tile filter. Map state
      remembered in localStorage. Archive entries have no `ll` yet — map in
      Archiwum mode shows nothing (known gap).

## Backlog (product: "deweloperuch dla wszystkich ogłoszeń")
- [ ] **Obniżki view + alerts.** "Price cut in the last 7 days" view sorted by
      % cut; CI-generated RSS/Atom feeds (global + per-town) so alerts need no
      server; localStorage watchlist + "changes since your last visit" diff.
- [ ] **Sort: longest on market** (motivated sellers; data already on cards).
- [x] **Storage switch — done 2026-07-11** (see the Done section at the top):
      data lives on the force-pushed orphan `data` branch, region = directory.
- [x] **Payload split — done 2026-07-11.** `scraper/payload.py` replaces the
      44 MB no-store `listings.json` with: `manifest.json` (tiny, no-store,
      carries a content hash) + `index.json` (12.5 MB slim grid fields, fetched
      cacheably as `?v=<hash>`) + `d/NN.json` (64 detail shards keyed by
      FNV-1a(url)%64 — offers/timeline/photos, fetched only when a card is
      expanded; same hash implemented in app.js, parity-tested). Offers list
      became a collapsible section. Verified in a real browser: first paint
      from the index alone, 1 shard fetch on first expand, 0 before.
- [ ] **Multi-voivodeship / whole Poland — NEXT.** The regional data layout,
      all 16 RCN mappings and `data-<region>` branches are implemented, but only
      Śląskie is live. The 2026-08-13 production audit found that coverage,
      runtime, regional navigation and hosting must be gated before region two.
      Current status and ordered work: [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md).
- [ ] **Licytacje komornicze — "deweloperuch dla licytacji"** (nationwide
      bailiff auctions + RCN gap per auction). Feasibility verified
      2026-07-14; full plan in its own section below ↓.

## Historical plan: scraping whole Poland (notes 2026-07-07, re-audited 2026-08-08)

> Superseded as the active plan on 2026-08-13 by
> [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md). Keep this section as the measurement
> and design history; its unchecked boxes and scheduling arithmetic are not the
> current pick-up list.

Region (voivodeship) stays the unit of everything: one scrape job, one data
dir, one dashboard, one RCN snapshot per region. "Poland" = 16 regions, not
one giant run. Scale, measured 2026-08-08 from otodom's own pagination totals:
śląskie holds **18 505 flats** on otodom alone (we publish 18 385 properties
from all five portals), mazowieckie is 772 pages ≈ 28k, and `cala-polska` is
4 188 pages ≈ **150 000 flats** — so Poland is ~8× śląskie *at full coverage*,
and we are currently at roughly a fifth of śląskie.

### Status of this plan (re-measured 2026-08-08 evening — READ THIS FIRST)
**Krok 1 and Krok 3 are DONE** (2026-07-11). Krok 0's de-Gliwice-ing is done
(2026-08-08). What is left is coverage, dedupe correctness, and Krok 2.

Every number below was measured, not estimated: the 2026-08-08 18:00 UTC run's
`meta.json` + run log, plus direct probes of each portal from the Pi. **Otodom
now answers a Polish residential IP** (search pages returned 200 with a full
`__NEXT_DATA__`), so portal shape no longer needs a CI round-trip to measure —
and local scraping is a real fallback for capacity, not a theory.

**Finding 1 — the 200-page default never took effect.** `update.yml` pins
`RENTGEN_MAX_PAGES: "50"` in the scrape step, which overrides the new default.
The 2026-08-08 18:00 run therefore still stopped every portal at page 50. The
+757 gratka houses measured yesterday were never collected in CI.

**Finding 2 — every portal states its true size, and we are far below it.**
Śląskie *flats* alone, portal's own count vs what we collected:

| portal | portal says | we collected | how it is stated |
|---|---|---|---|
| otodom | **18 505** (515 pages) | 1 482 | `pagination.totalItems` |
| gratka | **9 856** (282 pages needed) | 1 750 | "9 856 ogłoszeń" in the HTML |
| morizon | **~9 000** (rounded) | 1 750 | "9 000 ogłoszeń", rounds to 1000s |
| olx | **5 503** visible, serves 1 000 | ~250 native | `visibleElements` vs `totalElements` |
| n-online | town-by-town, no region count | 11 089 (both types) | — |

Otodom's śląskie flats alone outnumber our entire published dataset (18 385
properties, all portals, both types). Whole-Poland scale from the same source:
`.../sprzedaz/mieszkanie/cala-polska` reports **4 188 pages ≈ 150 000 flats**;
mazowieckie alone is 772 pages.

**Finding 3 — the reachable window per portal is a hard, measured number.**
- **otodom**: serves the full depth (page 500 of 515 answers), but deep pages
  come back thin and erratic (page 300 → 4 items, 450 → 12, 490 → 1), so deep
  pagination is not a trustworthy way to enumerate. `&limit=72` is honoured and
  halves the requests (515 → 258 pages, verified).
- **gratka / morizon**: **hard 404 past page 200** (bisected: 200 → 200 OK,
  201 → 404, on both portals). 200 × 35 = **7 000 ads per search, ever** —
  and our new default cap of 200 sits exactly on that wall, so a search that
  ends there looks finished while dropping 2 856 gratka flats.
- **olx**: `totalElements: 1 000` with `visibleElements: 5 503` — the cap is
  reported as a *smaller total*, and `totalPages: 25` matches it, so our
  current detection records "end" and the town subdivision built yesterday
  never fires. That is why OLX contributes 470 listings for a whole region.
- **n-online**: no region search, already subdivided per town — the only
  portal that was never truncated, and the reason it leads the source counts.

**Finding 4 — price bands subdivide all four portals, and are verified.**
Every paginated portal accepts a price range, so subdivision needs no
per-portal location taxonomy (otodom's is `region/powiat/gmina/city`, the
others' is one slug — they will never share a tree):

| portal | param | probe |
|---|---|---|
| otodom | `?priceMin=300000&priceMax=400000` | 3 348 items / 93 pages |
| gratka | `?cena-calkowita:min=200000&cena-calkowita:max=300000` | 1 209 ogłoszeń |
| morizon | `?ps[price_from]=200000&ps[price_to]=300000` | 1 000 ogłoszeń |
| olx | `?search[filter_float_price:from|to]` | ≤200k → 575 = visibleElements |

**Finding 5 — morizon has been photo-blind since some CDN change, and it costs
~2 400 duplicate cards.** In the published data, `('gratka','morizon')` appears
as a merged source pair **zero** times, while 2 428 of the 3 501 morizon cards
have a gratka card with an identical (type, area, rooms, price, town) — same
titles, e.g. "Klasyczna elegancja przy Parku Repeckim!". Cause: detail pages
now serve galleries from `img1.staticmorizon.com.pl`, which `photomatch._morizon`
does not match (it looks for `thumbs.cdngr.pl` / `img*.morizon.pl`), so every
morizon listing carries an empty `phashes` and can never merge with anything.
Two bonuses found while diagnosing it:
- the morizon URL embeds the **same base64 origin** as gratka's
  (`aHR0cHM6Ly9kLWdyLmNkbmdyLnBs…` → `d-gr.cdngr.pl/kadry/…/48544917_…jpg`,
  gratka's own ad id inside it) — an exact, free merge key for the pair with no
  image fetch at all;
- the first 5 gallery URLs on both portals are the **xs/s/m/l/og renditions of
  one photo**, so `MAX_IMAGES = 5` currently hashes a single photo five times.
  Dedupe by the base64 payload and take one rendition each.

So "whole Poland" is still not 16× the current pipeline: **the pipeline sees
roughly a fifth of the region it already claims, and inflates what it does see
by ~13% with unmerged morizon duplicates.** Fix coverage and dedupe first —
both fixes get multiplied by 16 afterwards, and both change every cost estimate.

### Measured cost per region (śląskie, 2026-08-08 18:00 UTC run)
| | |
|---|---|
| total runtime | 2 h 40 m, 2×/day |
| — scrape | 60 min (otodom 3, olx 2, gratka 3, morizon 3, **n-online 48**) |
| — photo hashing | 80 min — **hit the 90-min budget**, 53 150 listings |
| — history + archive ingest | 9 min |
| — delist sweep | 5 min (300 checks against a **21 639-record** stale backlog) |
| — RCN match + stats + geo + write | 6 min |
| published to Pages | 53 MB for 18 385 listings ≈ 2.9 KB/listing |
| on the `data` branch | 141 MB — site/data 74 + phash **54.3** + RCN 12.2 |
| RCN snapshot | 12.2 MB gz, 666k deeds |

What that implies at 16 regions, *after* the coverage fix roughly doubles each
region's listing count:
- **phash cache already trips GitHub's 50 MB file warning** (54.3 MB, printed
  in the push step of the last run). Doubled, and for a region larger than
  śląskie, it crosses the **100 MB hard limit** and the run simply fails to
  push. Gzip it (like history/RCN) and store the 256-bit hashes base64-packed
  instead of 78-char decimal strings — that is ~5× off the top.
- **Pages 1 GB**: ~100 MB per full-coverage region × 16 ≈ 0.9–1.4 GB, plus an
  archive that only grows. It will be breached — not on day one, but within the
  first year. Decision point, see step 6.
- **`data` branch ~2.3 GB fetched by every job**: `update.yml` checks out
  `site/data cache` from one shared branch regardless of region. One branch per
  region before region #2.
- **The delist sweep never catches up**: 300 checks/run against 21 639 stale
  records is a 72-run backlog *today*, in one region.
- Runtime is not a billing problem (public repo, unmetered minutes) but it is a
  scheduling one: 16 × ~3 h at `max-parallel: 1–2` fills the day. Portal
  politeness, not minutes, is the real constraint.

### Krok 0 — de-Gliwice the code (prereq, cheap)
- 4/5 scrapers already take `RENTGEN_REGION` as a URL slug (otodom, olx,
  gratka, morizon — verify each portal uses the same 16 slugs; otodom/olx do).
- **n-online is the exception**: hardcoded `SLASKIE_TOWNS` list (per-city
  subdomains), other regions degrade to a single-town search. Either build a
  town list per region (their sitemap / city index) or accept n-online as
  śląskie-only at first.
- Hardcoded bits to regionalize: `normalize.py CITY = "Gliwice"`,
  gratka/morizon strip the literal string `"śląskie"` from locations,
  `app.js` `GLIWICE_DISTRICTS` + `TOWN_COORDS` + the distance-from-Gliwice
  filter (make the anchor city a per-region config, or drop the distance
  filter outside śląskie), page titles.
- **Pagination-cap audit per portal.** `RENTGEN_MAX_PAGES=50` truncates big
  regions (OLX caps searches at ~25 pages ≈ 1000 ads regardless!). Detect
  overflow (last page == cap) and subdivide the search: per-city/per-powiat
  URLs, or price-band slices. Mazowieckie region-wide is definitely over
  every portal's cap — without this, coverage silently drops and the delist
  sweep starts URL-checking thousands of "missing" listings.

### Krok 1 — layout: region = build unit  ✅ DONE 2026-07-11
- `site/data/<region>/…` + per-region caches (`cache/phash_<region>.json`,
  `cache/rcn_<region>.json.gz`). P1 completed the canonical 16-region catalog,
  stable dashboard/stats paths and deploy-derived root picker on 2026-08-27.

### Krok 2 — CI
- Matrix over regions with `max-parallel: 1–2` and staggered crons (each
  region 1×/day spread over 24 h, instead of 2×/day everywhere) — the portals
  see the same runner IPs regardless of region, so parallel regions multiply
  ban risk, not throughput.
- Onboard ONE region at a time: the first run per region is heavy (photo
  hashing fetches galleries for every ambiguous listing).
- Per-region `RENTGEN_VERIFY_MAX` budget; per-region concurrency group so a
  slow region can't wedge the others.
- Realistic failure mode is portal 403s on GH runner IPs. Fallbacks, in
  order: lower frequency, local scrape + push (already supported — output
  files ARE the cache), self-hosted runner.

### Krok 3 — storage  ✅ DONE 2026-07-11 (option (a))
- Orphan `data` branch, force-pushed as one commit each run; history gzipped
  (63 MB → 21 MB) and stripped from the Pages artifact by `deploy.yml`; payload
  split into slim index + 64 lazy detail shards. Main carries code only.
- **What the 2026-08-08 re-audit adds**: the per-file and repo-history limits
  are solved, but two new ceilings appear at 16 regions — the 1 GB Pages cap
  (~850 MB projected) and the whole-branch fetch in `update.yml`. See "Measured
  cost per region" above. Option (c) (R2/S3) remains the escape hatch if the
  Pages cap is reached before the region set is complete.

### Rollout order (rewritten 2026-08-08 evening, from the measurements above)

The ordering rule: anything that is wrong *per region* gets fixed before it is
copied 16 times. Steps 0–4 are all "śląskie only" work that never touches the
region count, and they are what makes the region count worth raising. **Steps 0
and 1 shipped on 2026-08-08; the live work starts at Step 2.**

**Step 0 — unpin the page cap in CI.  ✅ DONE 2026-08-08** (see the Done
section at the top). `RENTGEN_MAX_PAGES: "50"` is gone from `update.yml`; the
200 default in `main.py` is now the only cap.

**Step 1 — portal ground truth in `coverage.py`.  ✅ DONE 2026-08-08.** Every
portal's stated total is read and compared (otodom `pagination.totalItems`,
gratka/morizon `normalize.stated_total()`, olx `visibleElements` vs
`totalElements`); a short-of-total 404 and OLX's stated cap are now
`portal_cap`, and `meta.json` → `coverage.by_source` carries `portal_total` +
`pct`. Details and the numbers to expect are in the Done section at the top.

**Step 2 — price-band subdivision (`scraper/bands.py`).  ✅ DONE 2026-08-09**
(see the Done section at the top). One helper, four portals, half-open `[lo, hi)`
bands, additive, `RENTGEN_BANDS=0` to disable; otodom also gained `&limit=72`.
The reachable windows live in `bands.WINDOW` as named constants. gratka's and
morizon's parameters were re-probed live on the day and answer exactly as
recorded; otodom's are the 2026-08-08 measurements (its edge 403s the Pi after a
probe burst). `check_totals` asserts the seed bands sum to at least the unbanded
total, which is how a portal's price filter dropping ads gets caught.
**Caveat found 2026-08-11**: on otodom the bands largely do not run at all — the
portal 405s partway through and seven of nine bands die on page 1, so
`check_totals` fires on a shortfall that looks like a price filter and is really
the refusal. Item 1 of the 2026-08-11 pick list.

**Step 3 — the dedupe defects.  ✅ DONE 2026-08-09** (see the Done section at
the top). The gratka↔morizon merge needs no image fetch at all — a morizon
search-page thumbnail already carries gratka's ad id — and links **7 089** of
9 501 morizon cards when re-run over the real published records, 20.8% of
everything published. Gallery hashing is now one URL per distinct photo origin
on both portals, blog teasers on the same CDN path excluded, fixtures pinned to
real pages.
- [x] **Verified on run 31422141701 (2026-08-11)**: `('gratka','morizon')` is
      not zero — **8 712** published properties carry both, against the 7 089
      estimate, with morizon-only down to 1 344 and gratka-only to 811. The
      regression test passed on the merge's first completed CI run.

**Step 4 — make one region affordable at ~2× the listings.**
- [x] **phash cache**: gzipped and base64-packed — **65.92 → 12.35 MB (5.3×)**
      measured on the real production file, round-trip clean on all 72 090
      entries, v1 migrated on read and deleted on save. DONE 2026-08-09.
- [ ] **Photo budget**: still the binding constraint, and the premise this
      item was written on turned out to be wrong. The n-online dedupe did *not*
      halve the input — measured across all three 2026-08-09/10 runs the photo
      phase was handed **101 853–101 992 listings, up from 90 341** (see the
      2026-08-10 section: the cross-town duplication is at property level, not
      ad-id level). What did change underneath it: empty results are now cached
      so photo-less ads stop being re-fetched every run, and hashing is per
      distinct origin instead of five renditions of one photo. **Re-timed on the two
      green runs (2026-08-11): 100 and 109 min, on inputs of 102 345 and
      100 338, starving 18 296 and 12 857 listings.** The phase is
      budget-bounded, so it does not grow with the input — it just starves a
      larger share of it. Choose between a larger budget, more workers, or
      hashing only listings that actually have a size-collision; the next item
      down (twins need no photos) is the cheapest of the three, and is now
      proven rather than estimated.
- [x] **Don't hash a listing whose twin already identifies it. DONE
      2026-08-12.** `link_twins` runs before the photo phase now; the morizon
      half carries `_identified_by` and `attach_hashes` skips it outright.
      ~8 700 detail fetches a run, measured off the published 2026-08-11 data
      (8 712 twins), not estimated. `_build` unions the gratka half's hashes
      onto the property so nothing downstream goes without.
- [ ] **Is OLX worth its slot?** Even with the empty-search bug fixed it is the
      second-most expensive portal for the least return: 2 044 searches in the
      2026-08-10 run to keep **1 730 listings**, because most of what it serves
      is syndicated from Otodom and dropped by design (that filtering is
      correct — the ads are collected at the source). **The fixed phase is now
      measured (2026-08-11): 146 searches, 31 min, 1 751 kept — and on the very
      next run OLX served nothing at all** (`__PRERENDERED_STATE__ not found`,
      probably a block). Decide between keeping it, dropping the per-town ×
      per-band product down to towns only, or restricting bands to towns that
      actually overflow. Whatever the answer, it is 16× on the whole-Poland
      matrix — and item 2 of the 2026-08-11 pick list has to land first, so the
      log can say whether OLX is blocked or re-skinned.
- [x] **Delist sweep: cut. DONE 2026-08-12.** All three of the fixes it wanted,
      because they are complementary: concurrent (8 workers), on
      `net.probe_session()` which does not retry at all, under
      `RENTGEN_DELIST_BUDGET_MIN`; and `is_gone`'s timeout 20 s → 8. Unasked
      records stay unasked rather than concluded.
- [ ] **Delist sweep, still open**: 300 checks against 13 449 stale records
      still never *converges*, however fast each one is. Prioritise
      (oldest-first is not the same as most-likely-gone), use HEAD where the
      portal allows it, and scale `RENTGEN_VERIFY_MAX` with the record count
      instead of pinning it at 300.
- [ ] **Geo**: measured **94.3–94.6% located** on the 2026-08-11 runs, and
      run 31422141701 needed only 183 of its 500 lookups — śląskie has
      essentially converged, so this is no longer a per-run cost here. Still
      hopeless for 16 regions from cold: scale the budget per region and let a
      region converge before the next one starts.

**Step 5 — region infrastructure (Krok 2, unchanged in substance).**
- [x] **Split the `data` branch per region (`data-<region>`). DONE
      2026-08-12** — before region #2 exists, as required. A job pulls
      `data-$REGION` and pushes back only its own region's data plus the caches
      it owns; `deploy.yml` overlays the pre-split `data` branch first and every
      `data-*` branch on top, so the migration needed no flag day.
- [ ] CI matrix over regions, `max-parallel: 1–2`, staggered crons, 1×/day per
      region, per-region concurrency group and `RENTGEN_VERIFY_MAX`.
- [ ] Region picker on the root page with per-region counts; per-region meta /
      OG / sitemap (static meta is still śląskie-only).
- [ ] **Pilot ONE region end-to-end** — małopolskie or dolnośląskie: mid-size,
      and it exercises the n-online town derivation and the bands on a region
      whose shape nobody has looked at. Measure it, then add in batches of 3–4,
      watching `meta.json` error rates and the Pages payload.

**Step 6 — the hosting ceiling (decide before region #4).**
- [ ] Pages' 1 GB will be reached by 16 full-coverage regions plus archive
      growth. Two ways out, and they are not exclusive:
      **(a)** shrink the payload — the index is ~700 B/listing of verbose JSON;
      an array-of-arrays encoding with a column header is ~3× smaller, and the
      archive wants the same shard treatment the listings got;
      **(b)** stop serving data from Pages — the `data` branch is already the
      store, so jsDelivr (`cdn.jsdelivr.net/gh/<user>/<repo>@data/…`, note the
      ~20 MB per-file limit → shards must stay small) or R2 serves it with CORS,
      and Pages goes back to hosting a few MB of code.
      Recommendation: do (a) anyway because it also cuts load time, and treat
      (b) as the escape hatch the moment the published total passes ~600 MB.
- [ ] **Sparkline price chart** on cards instead of the text price trail.
- [ ] **Rental listings dataset** -> estimated gross yield per sale listing
      from rental comps (town + size bucket); attracts the investor crowd.
- [ ] **Agency behaviour stats** (relist frequency per agency) — tread
      carefully, naming-and-shaming risk.

## Plan: licytacje komornicze — "deweloperuch dla licytacji" (notes, 2026-07-14)

All Polish bailiff real-estate auctions in one dashboard, each with a
**"cena wywołania vs transakcje RCN"** gap — the analytics layer no existing
aggregator has (licytor.pl / podkluczyk.pl / adradar.pl are paid alert
services without deed benchmarks). Nationwide from day one: only **~3.2k live
real-estate auctions** across Poland (vs ~18k listings in śląskie alone), so
one polite cron covers the country. Feasibility probed live from the Pi
(Polish residential IP) on 2026-07-14; probe details also in project memory
(`licytacje-komornik-scrapeability`).

### Source facts (verified 2026-07-14)
- **licytacje.komornik.pl** is the single central source (KRK portal;
  elicytacje.komornik.pl redirects there). Publication is mandated by
  art. 953/955 KPC; **robots.txt is `Allow: /`** (only user panels blocked).
- **Search page SSR** (`/wyszukiwarka-licytacji`): `__NUXT_DATA__`
  (devalue-encoded) carries `search-items` = the 20 newest items + total
  `count` (3,167 on 2026-07-14). **URL query params are ignored server-side**
  — no SSR pagination/filters, so poll it (~hourly) to catch new items
  (~100–250 new notices/day nationwide).
- **Item record fields** (from that payload): id, title, openingValue,
  **estimate** (suma oszacowania), startAuctionAt/endAuctionAt, marginDueDate,
  dateCreated, status, mainCategory, subCategory (APARTMENTS/HOUSES/LAND/
  GARAGES/COMMERCIAL_PREMISES/OTHER), address (city/street/buildingNo/
  **flatNo**/zipCode/province), eauction flag, noticeId, location{lat,lon}
  (schema present, always 0,0 — geocode via geo.py), base64 thumbnail.
- **Notice pages** (`/wyszukiwarka/obwieszczenia-o-licytacji/<id>/<any-slug>`)
  are **fully SSR'd and ID-enumerable**: missing ids genuinely 404; ids are
  dense from ≤30000 to ~44400 (July 2026) → full historical backfill is one
  weekend of polite crawling. Each page: complete obwieszczenie text +
  structured rows (Cena wywołania, Suma oszacowania, Najniższe postąpienie,
  rękojmia, sygnatura Km, **KW number**, działka numbers, **debtor name —
  STRIP IT, RODO**). Notice ids (~37–44k) and item ids (~70–75k) are separate
  sequences; items include movables.
- Item pages `/licytacje/<id>/<slug>` are CSR shells (always 200, no data) —
  useless for scraping. The JSON search API
  (`POST /services/item-back/rest/item/search/bailiff`) is WAF-blocked for
  curl + reCAPTCHA-gated — **not needed** (SSR poll + notice enumeration
  covers everything); headless Chromium is the fallback if that changes.

### Why our stack wins
- **RCN gap per auction** — `rcnstats.py` town/size-bucket benchmarks drop in
  as-is: "cena wywołania vs transakcje RCN: −45 %".
- **Auctions come with KW + exact address + działka** — rentgen's hardest
  problem (address discovery) doesn't exist here; `uldk.py`/`rcncheck`
  parcel-anchored matching gives the *exact property's* past sale prices.
- **Cross-ref with portal listings**: photo/address match against rentgen data
  → "this flat is/was on Otodom at 520k; auction opens at 333k".
- **Round tracking**: pierwsza (3/4 oszacowania) vs druga (2/3) licytacja —
  przetargimiejskie's round logic, applied nationally.
- Serverless model (Actions cron → data branch → Pages) transfers unchanged.

### MVP steps
- [ ] **`scraper/licytacje.py`**: backfill notices id 30000→now (polite rate,
      resumable, committed cache like phash), then incremental: poll search
      SSR for new items + forward-scan notice ids; parse notice HTML into the
      auction schema (openingValue, estimate, dates, address, KW, parcel,
      round, e-auction). Strip debtor names at ingest.
- [ ] **Dataset**: `site/data/aukcje/` (auctions are nationwide — not
      per-region like listings); slim index + detail shards via payload.py.
- [ ] **RCN integration**: gap vs rcnstats bucket per auction; parcel/KW/
      address-anchored deed history per property (rcncheck path).
- [ ] **Dashboard**: auction cards (round badge, countdown, wywołanie vs
      estimate vs RCN), map view (geo.py — addresses are exact), filters
      (province/category/price/round/e-auction).
- [ ] **Test from GH Actions early** — przetargimiejskie saw Polish hosts
      block Azure/GH runner IPs; if blocked, Pi-scrape + data-branch push is
      already a supported flow.
- [ ] **Verify RCN captures enforcement sales** (przysądzenie własności is a
      court decision, not a notarial deed): run rcncheck against a few known
      2025 auction outcomes. Determines whether "sold at auction for X" and
      post-auction outcome tracking are showable.

### Open decisions / risks
- **Packaging**: new card type inside rentgen-ofert vs standalone repo/domain
  reusing scraper libs (deweloperuch analogy + przetargimiejskie lead-gen GTM
  suggest standalone; sharing rcn/geo/uldk argues in-repo). Decide at MVP end.
- **RODO / legal**: never republish debtor names (the portal has a statutory
  basis we don't); review `/regulamin` before any public launch; link back to
  source notices, personal-scale etiquette as with portals.
- **Later phases to be truly "all auctions"**: syndyk/bankruptcy sales (KRZ),
  municipal auctions (przetargimiejskie already covers), AMW/KOWR/PKP,
  urzędy skarbowe. Komornik alone is a complete MVP.

## Done (property lifetime timeline + RCN — earlier round)
- [x] **RCN integration (`scraper/rcn.py`).** Pulls all Śląskie flat +
      residential-building transactions from GUGiK's free WFS
      (`mapy.geoportal.gov.pl/wss/service/rcn`, public since Feb 2026) into
      `cache/rcn_snapshot.json.gz` (weekly refresh; ~240k lokale). Matches deeds
      to tracked properties (town + area ±0.6 m², street match or rooms+floor),
      conservatively and with a confidence label. Deed before listing =
      "poprzednio sprzedane"; deed after delisting = "sprzedane wg RCN".
      Service quirks documented in the module docstring (LIKE-only filters,
      GML-only output, unreliable sortBy).
- [x] **Delisting detection (`scraper/delist.py`).** Absence from a scrape is
      weak evidence (pagination caps), so stale records' URLs are fetched
      (≤ `RENTGEN_VERIFY_MAX`/run) and only 404/410, archive redirects or
      "ogłoszenie nieaktualne" markers mark a property delisted. Coming back
      clears the flag (relist).
- [x] **n-online archived ads harvested** instead of skipped — direct
      "this ad ended" evidence, marks the record delisted immediately.
- [x] **Photo archive.** Gallery URLs (already fetched for hashing) are kept in
      the phash cache and history records; cards link the archived photos.
- [x] **Richer history records**: last_seen, display snapshot (locality/street/
      rooms/floor… — also what RCN matching keys on), sales, delisted.
- [x] **URL-fallback matching + `history.compact()`** — photo-less listings no
      longer spawn a fresh record every run; existing duplicates get merged on
      load (14 475 → 12 625 on current data).
- [x] **Dashboard**: expandable per-card *Historia nieruchomości* timeline
      (listed/price/relist/archived/delisted/sold events), "Archiwum /
      sprzedane" view fed by `site/data/archive.json`, sold/wycofane badges,
      RCN sale banners, meta counts.
- [x] Tests: `tests/test_history.py`, `tests/test_rcn.py` (39 total, offline).

## Done (developer new-builds + UI perf — earlier round)
- [x] **Developer new-builds detected and un-merged.** Detection: portal's
      `market: primary` (Otodom/OLX, now captured), title keywords
      (deweloper/inwestycja/etap/…), or >=3 same-gallery ads on one portal.
      A development photo-cluster becomes one card per asking price
      ("inwestycja" badge) instead of one fake "flat on 12 ofertach"; dev
      records skip relist flags, the delist sweep, RCN deed matching and the
      Archiwum (their history is marketing, not a property's life).
- [x] **Rynek filter** (Oba / Wtórny / Inwestycje) + **"Sprzedane wg RCN"**
      filter in the dashboard.
- [x] **Chunked grid rendering** — 60 cards + infinite scroll, debounced
      inputs, `content-visibility`; filter clicks went from ~seconds of
      freeze at ~19k cards to ~200 ms.

## Done (RCN matching v2 + validator — earlier round)
- [x] **Match-rate overhaul** (measured on real data: 29k records):
      declension-tolerant street matching (Gdańskiej == Gdańska — was the
      single biggest false-reject), district↔locality fallback, decimal-area
      uniqueness rule for flats (48.63 m² occurring once in a town is identity
      by itself), plot-area corroboration for houses (deed carries
      nier_pow_gruntu). Result: 1 494 properties with attached deeds
      (2 632 sale events; 2 520 wysoka / 112 średnia confidence).
- [x] **Match funnel in meta.json** (`rcn`): records / no_location_yet /
      no_deed_candidates / candidates_rejected / matched — visible on every run.
- [x] **`python -m scraper.rcncheck`** — validate a single property by hand:
      `rcncheck Gliwice 48.63 --ulica Asnyka --pokoje 2` lists all deeds for
      that size in town and marks which the matcher would accept.
- [x] Fixed the always-open miejscowość picker (a lost `[hidden]` CSS rule,
      not a JS bug).

## Done (address lookup + manual pinning — earlier round)
- [x] `rcncheck` searches by exact address (`--ulica`, `--nr`, area optional,
      flats+houses) — shows a building's full sale history back to ~2000.
- [x] **overrides.json + `--pin`**: hand-learned addresses attach to listing
      URLs; the pipeline applies them to history snapshots (`manual: true`)
      and the matcher treats street+number as decisive (wysoka), including
      against deeds that lack a usable-area field (kept in the snapshot now).

## Done (address -> parcel resolution — earlier round)
- [x] **`scraper/uldk.py`**: address -> canonical street + EPSG:2180 point
      (UUG geocoder) -> cadastral parcel id (ULDK GetParcelByXY). Free GUGiK
      services, no keys. Guarded: if the geocoder can't confirm the exact
      building number, no parcel is claimed.
- [x] `rcncheck` resolves automatically when --ulica + --nr are given, uses
      the canonical street for matching, and `--pin` stores dzialka_id + x/y.
- [x] RCN snapshot now carries the parcel (`dz`, from lok_id_lokalu /
      bud_id_budynku) and the scorer treats parcel equality as decisive both
      ways. Takes effect for matching after the next weekly snapshot re-pull
      (or RENTGEN_RCN=force).

## Pending — timeline / RCN
- [ ] House matching is street-anchored only (budynki records are noisy);
      consider dzialki-layer cross-checks for houses with plots.
- [ ] RCN registry lags deeds by weeks-months; re-match on every run keeps
      catching up — maybe surface "sprzedane, cena jeszcze nieznana" when
      delisted > 60 days with no deed yet.
- [ ] Otodom/OLX ship exact lat/lon — capturing them would make RCN matching
      near-certain (geometry is in the WFS response, currently discarded).
      Would also upgrade the map view: `geo.py` town/street geocoding is
      approximate, portal coordinates are the real thing.

## Done
- [x] Otodom scraper (houses + flats) — parses `__NEXT_DATA__` JSON
- [x] OLX scraper — parses `__PRERENDERED_STATE__`; skips Otodom-syndicated ads
- [x] gratka scraper — parses server-rendered `data-cy` cards (BeautifulSoup)
- [x] nieruchomości-online scraper — parses schema.org JSON-LD offers
- [x] Morizon scraper (reuses gratka's card frontend — same media group)
- [x] Cross-portal de-duplication, **matches the same property even at different prices**
- [x] Photo-matching: perceptual hash (dHash) of each ambiguous listing's gallery
      confirms it's the same property before merging — precise, no false merges
- [x] Each card shows every source's link + price + date added, and a price range
- [x] Static dashboard: filters, search, sort
- [x] Resilient scrapers — a page error keeps prior results instead of dropping the portal
- [x] GitHub Actions cron + Pages deploy (`.github/workflows/update.yml`)
- [x] Unit tests (parsers + dedupe) with offline fixtures — `python -m pytest -q`
- [x] Skip archived nieruchomości-online listings (`availability: OutOfStock`)
- [x] Relist + price history via photo fingerprint — persistent `history.json`

## Done (Śląskie-wide + caching + filtering — earlier round)
- [x] **Whole-voivodeship scope.** All five scrapers now search the entire Śląskie
      voivodeship: a region-level URL on Otodom/OLX/gratka/Morizon (no more Gliwice
      radius), and a generous per-city sub-domain list on nieruchomości-online.
      Region is configurable via `RENTGEN_REGION` (default `slaskie`).
- [x] **Photo-hash cache (`scraper/cache.py` → `cache/phash_cache.json`).** Gallery
      hashes are keyed by listing URL and reused across runs, so repeat runs skip the
      slow detail-page + image fetches. Committed each run (like `history.json`) so CI
      reuses it; self-prunes URLs not seen for 21 days.
- [x] **Faster pipeline.** `actions/setup-python` pip cache + the committed phash
      cache; the data-refresh commit now also commits `cache/phash_cache.json`
      (and `cache/**` is in `paths-ignore` so it never re-triggers the workflow).
- [x] **Town multi-select filter** — searchable, built dynamically from the data;
      the primary geographic control now that coverage is voivodeship-wide.
- [x] **Distance-from-Gliwice filter demoted** to an optional convenience (default
      off, relabelled "orientacyjnie") so it no longer silently hides the hundreds of
      towns it has no coordinates for.
- [x] **Filters are remembered** — saved to localStorage and encoded in the URL
      (`?f=…`) so a filtered view survives reloads and is shareable.
- [x] **Active-filter chips** with per-filter remove + one-click "Wyczyść wszystko".
- [x] **Fixed locality parsing (gratka + Morizon).** They took the *first* breadcrumb
      segment as the city, so streets like "Szafirowa"/"Tarnogórska" became fake towns
      (hundreds of listings). Now the city is the *last* segment; the street/district
      parts move to `district`.

## Pending — deploy
- [x] Deployed to GitHub Pages.
- [x] First voivodeship-wide data and caches landed; `data-slaskie` was created,
      refreshed and deployed successfully on 2026-08-12.

## Pending — coverage / completeness
- [ ] **Literal "every listing".** Price bands recover much more than a single
      region query, but the live 2026-08-12 run is still partial: Otodom's upper
      bands were refused, OLX returned 403, Gratka/Morizon retain parent-cap
      warnings and n-online hit a town cap. Treat P0.1–P0.4 in
      `POLAND_ROLLOUT.md` as the current coverage plan.
- [ ] **Precise distances.** Listings now carry `ll` (UUG-geocoded, town/street
      precision) — the distance filter could compute from it for *every* town
      instead of the ~90 hard-coded `TOWN_COORDS` in `app.js`. Portal-shipped
      lat/lon (Otodom/OLX) would be better still.

## Pending — features / ideas
- [ ] **adresowo.pl** — client-side rendered; needs a headless browser (Playwright)
      or its JSON API. Deferred to keep the no-browser model.
- [ ] More portals: domiporta.pl, sprzedajemy.pl, Facebook Marketplace
- [ ] Daily email digest of new / price-changed listings
- [ ] Optional rentals (wynajem) toggle

## Known issues / notes
- Śląskie region URLs are repeatedly production-validated. No non-Śląskie
  portal URL has completed an end-to-end run yet; validate all of them in the
  one-region pilot before adding a matrix.
- Locality `city = last breadcrumb segment` assumes gratka/Morizon order their
  breadcrumb specific→general (street, district, city). True on all observed samples.
- Scrapers depend on each portal's page structure; a redesign may need a parser tweak.
  Logic is isolated per portal and covered by tests, so fixes are small.
