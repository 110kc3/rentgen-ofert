# Whole-Poland rollout: status and next tasks

> Audited: 2026-08-23 08:05 UTC; P0.2/P0.3 implementation update
> Scope: production is current through the successful 2026-08-22 evening run.
> P0.1 is live-validated. The local P0.2/P0.3 request-policy changes pass the
> offline suite but have not yet run on a scheduled GitHub runner.
> This is the current source of truth for the nationwide rollout. `TODO.md`
> retains the detailed development diary and older measurements.

## Executive status

**The regional foundation works, but the project is not ready to start a
16-voivodeship rollout.** Śląskie is the only published region. Per-region data
branches have been proven in production, but source completeness, run capacity,
the regional user experience, scheduling and nationwide hosting are not ready.

| Area | Status | Evidence / gap |
|---|---|---|
| Region-scoped scraper output and caches | Ready | `site/data/<region>`, `phash_<region>` and `rcn_<region>` are implemented. |
| All 16 RCN/TERYT mappings | Ready in code | `scraper/main.py` contains all 16 voivodeships; only Śląskie has run end to end. |
| One data branch per region | Proven | `data-slaskie` was created and has been refreshed successfully. |
| Deploy overlay for multiple region branches | Proven for one branch | The live deploy overlays `data-slaskie`; a second branch has not been exercised. |
| Portal coverage | Blocked; recovery local | Published Otodom remains at ~8.5k, OLX is blocked and n-online caps Katowice flats. The local fix restores Otodom's full baseline and makes OLX fail fast; live validation is pending. |
| Coverage KPI | Proven in production | Schema v2 has published repeatedly: bounded percentages, explicit missing partitions and healthy/partial/blocked source states all survive real runs. |
| Per-region runtime | Provisional gate met | The latest two completed warm jobs took 167 and 162 minutes, under the 180-minute gate but above the preferred 150; the request-policy change still needs remeasurement. |
| Region picker and durable regional URLs | Not ready | There is no picker; changing filters removes `?region=`, and saved filters are shared across regions. |
| Per-region metadata / OG / sitemap / llms.txt | Not ready | The generator and committed HTML are Śląskie-only. |
| CI region matrix / cadence | Not implemented | The workflow still schedules Śląskie twice daily and accepts other regions only by manual input. |
| Nationwide data hosting | Not decided | One incomplete region already serves about 106 MB; GitHub Pages has a published-site limit of 1 GB. |

**Rollout decision:** do not add a scheduled second region yet. First complete
the P0 stability gate below. A manual, disposable pilot is the next region
action after that gate—not a 16-region matrix.

## Production snapshot

### Repository and deployment

- Main HEAD is `d9a0c67` (`feat: make coverage accounting truthful and expose
  source health`). This worktree also contains the local P0.2/P0.3 request
  policy, regression tests and documentation update described below.
- The [live site](https://110kc3.github.io/rentgen-ofert/) and
  [live `data/slaskie/meta.json`](https://110kc3.github.io/rentgen-ofert/data/slaskie/meta.json)
  both return HTTP 200.
- [Deploy run 32599191378](https://github.com/110kc3/rentgen-ofert/actions/runs/32599191378)
  published the latest successful scrape; the site and `meta.json` both return
  HTTP 200 as of this audit.
- Latest published data: **2026-08-22 21:17 UTC**, **25,412** current unique
  properties from **44,052** current raw listings.
- Published data comes from four sources in that run, not five: Otodom, Gratka,
  Morizon and nieruchomości-online. OLX contributed zero.
- The suite now contains **192** offline tests; all **192 passed locally** in an
  isolated temporary environment after P0.2/P0.3. The Actions scrape workflow still
  has no test step, so a green production scrape is not yet a unit-test gate.

### Latest completed validation runs

Schema v2 has now published repeatedly. The two latest completed warm runs are:

| Run | Trigger | Actual job time | Result | Published properties |
|---|---|---:|---|---:|
| [32557869486](https://github.com/110kc3/rentgen-ofert/actions/runs/32557869486) | schedule | 167 min | success; schema v2 | 25,491 |
| [32591212134](https://github.com/110kc3/rentgen-ofert/actions/runs/32591212134) | schedule | 162 min | success; schema v2 | 25,412 |

[Run 32623879451](https://github.com/110kc3/rentgen-ofert/actions/runs/32623879451)
was cancelled after exactly 60 minutes while walking Morizon. It did not push
data and is deliberately not treated as source-coverage evidence.

### Latest source health

These are the published schema-v2 `meta.json` values from run `32591212134`:

| Source | Current kept listings | Reported search state | Assessment |
|---|---:|---|---|
| Otodom | 8,427 | `partial`, 37.7%; seven missing flat partitions, HTTP 405 | Regression and blocker; schema v2 keeps every failed band in the denominator. |
| OLX | 0 | `blocked`, two root rows, HTTP 403 | Runner/IP block. The local P0.3 fix reduces four real requests to one probe. |
| Gratka | 12,481 | `healthy`, 99.9% | Full useful coverage in the current accounting model. |
| Morizon | 12,481 | `partial`, bounded 100% against a lower-bound total | Useful and mostly twinned with Gratka; partial because seed-band totals are short of the parent floor. |
| nieruchomości-online | 10,663 current | `partial`; 58,609 served including 47,946 archived; Katowice flats capped | Valuable, but expensive and not complete. |

The published unique count is lower than the source sum because Gratka and
Morizon substantially overlap and are merged.

### What production now proves

- **Per-region branches succeeded.** The first validation run seeded from the
  old shared `data` branch, created `data-slaskie`, and the next run fetched and
  force-refreshed it. The site deployed the new data successfully.
- **The delist change succeeded.** The phase fell from 27–44 minutes in bad
  runs to **37 seconds** and **42 seconds** for 300 checks.
- **Schema v2 works live.** Percentages stay bounded, the seven failed Otodom
  leaves remain named and counted, OLX is blocked rather than a clean zero, and
  Gratka is independently healthy.
- **The warm photo backlog has converged.** The latest two runs completed the
  phase in 74 and 50 seconds; the latest reused 83,684 cache entries, skipped
  8,130 known twins and reported no budget-exhausted records. P0.5's priority
  should be reassessed, though its correctness/history scheduling split is not
  implemented.
- **The Otodom scout hypothesis failed.** The unbanded flat search correctly
  stopped after 12 pages, but Otodom started returning 405 after only about
  5–6 minutes: at `200k-300k` page 35 in the first run and `300k-400k` page 2
  in the second. Kept Otodom listings fell from the long-running **16.6k**
  baseline to **8,461 / 8,541**. This is not evidence of a stable 320-page
  allowance; the currently published scout is a production coverage regression.
- **The failures are persistent.** Every one of the eight most recent completed
  logs inspected (2026-08-19 through 2026-08-22) refused the same seven Otodom
  bands and returned OLX 403 on all four root attempts.

### Runtime and scheduling capacity

Approximate phase times from the latest two completed validation logs:

| Phase | Run 325578 | Run 325912 |
|---|---:|---:|
| Otodom | 23.6 min | 23.4 min |
| OLX (blocked) | 1.0 min | 1.0 min |
| Gratka | 19.5 min | 17.9 min |
| Morizon | 20.7 min | 19.2 min |
| nieruchomości-online | 72.3 min | 77.4 min |
| Photo hashing | 1.2 min | 0.8 min |
| Remaining history, delist, RCN, geo and write work | about 28 min | about 22 min |
| **Whole job** | **167 min** | **162 min** |

At the latest 164.5-minute average, one daily sweep of 16 Śląskie-sized regions
would need about **43.9 runner-hours per day**, or **21.9 hours** at
`max-parallel: 2`. That fits arithmetically but has almost no operational
headroom, assumes every cold region converges like Śląskie, and conflicts with
the runner-IP blocking already visible on Otodom and OLX. A matrix is still not
justified before the P0 source and cold-region gates.

The capacity gate should be **at most 180 minutes per warm region**, with a
preferred target of **150 minutes** for headroom, before a two-wide daily
schedule is considered. Otherwise the product must explicitly accept a slower
cadence.

### Storage and Pages capacity

Current `data-slaskie` branch contents:

| Part | Size |
|---|---:|
| Whole per-region branch | 168.6 MB |
| `site/data/slaskie` including pipeline-only history | 137.0 MB |
| Pipeline-only `history.json.gz` removed before deploy | 30.6 MB |
| **Approximate data actually served for Śląskie** | **106.4 MB** |
| Caches on the branch | 31.5 MB |
| `index.json` alone | 19.2 MB |
| `archive.json` alone | 11.2 MB |

GitHub currently documents a **1 GB published-site limit**, a 10-minute deploy
timeout and a soft 100 GB/month bandwidth limit: [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
The custom Pages artifact may be larger at upload time, but that is not a safe
reason to design beyond the published-site limit: [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

At today's incomplete Śląskie shape, 1 GB is fewer than ten Śląskie-sized
payloads. Poland was previously estimated at roughly eight Śląskie inventories
before full coverage and archive growth, leaving too little safety margin for
the final architecture. A hosting decision and migration rehearsal belongs
before region four, not after the artifact approaches the limit.

## Audit findings that were missing from the old plan

1. **`?region=` is not durable.** `app.js` reads it on boot, but every filter
   persistence call rebuilds the URL from `location.pathname` plus `?f=` and
   drops the region. Reloading or sharing then returns to Śląskie.
2. **Saved filters leak between regions.** The localStorage key is global, so a
   Śląskie town selection can produce an empty view when another region opens.
3. **The regional UI is only a partial fallback.** Only Śląskie exists in
   `REGION_CONFIG` and `REGION_LABEL`; unknown regions show a raw slug, lose
   the anchor control, and retain multiple Śląskie-only static strings.
4. **Discovery metadata is single-region.** `scripts/update-summary.mjs`
   deliberately picks Śląskie and hardcodes its titles/descriptions. The root
   page, stats page, OG card, JSON-LD, canonical links, sitemap, footer and
   `llms.txt` do not represent multiple regions.
5. **The old published coverage percentages could not gate rollout.** Schema v1
   combined an unbanded parent with overlapping child bands; failed bands could
   disappear from the denominator and lower-bound totals could exceed 100%.
   P0.1 is now proven live: parent-owned totals, unique-ID unions, bounded
   percentages and explicit failed leaves all appear in the published output.
6. **n-online is no longer “the portal that is never truncated.”** Its latest
   flat crawl hit the per-town page cap. P0.1 now separates current and archived
   coverage counts and names failed/capped town partitions, but P0.4 still has
   to reduce the work and validate the live cap.
7. **No automated test gate protects the expensive scrape.** The repository
   has a strong offline test suite, but the production workflow installs only
   runtime dependencies and starts scraping immediately.
8. **A green workflow currently means “some data published,” not “the region
   is healthy.”** P0.1 now emits `healthy`, `partial`, `blocked` and `unknown`
   separately from process success and exposes them in the dashboard. P0.6 must
   still turn that result into an enforced CI quality gate.

## Decisions for the next implementation round

- Keep **voivodeship = build, history, cache and branch unit**. That part of the
  architecture is sound.
- Keep OLX code, but treat it as an **optional source on GitHub-hosted runners**.
  A first-request 403 should end the portal immediately and publish an explicit
  blocked status. Full OLX collection should run only from an environment that
  can actually reach it.
- Restore a safe Otodom coverage floor before pursuing a clever subdivision
  strategy. The 16.6k baseline is more valuable than a scout that theoretically
  enables bands but publishes only 8.5k.
- Build one canonical region catalog and generate the Python, frontend and
  discovery views from it; do not maintain separate handwritten label maps.
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

**Current pick-up point:** publish and validate the local P0.2/P0.3 slice on two
scheduled runs, then begin P0.4. P0.1 is complete and live-validated.

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
  - **Verification:** repeated production runs through 2026-08-22 publish
    bounded percentages and the expected source/type health. The local suite is
    now **192/192** after the P0.2/P0.3 regression cases.

- [ ] **P0.2 Restore and re-measure Otodom.**
  - Remove the unproven “~320-page budget” assumption from behavior and docs.
  - First restore at least the pre-scout coverage floor, then test subdivision
    separately and additively.
  - Log elapsed time, successful requests and first refusal for every run.
  - **Accept when:** two consecutive scheduled runs keep at least 16k Otodom
    listings or a new evidence-backed floor is explicitly approved; no tested
    strategy can cut the published baseline in half silently.
  - **Implemented locally 2026-08-23:** removed the 12-page scout; the default
    is the full 200-page unbanded baseline. Otodom bands require
    `RENTGEN_OTODOM_BANDS=1` and run only after that baseline. Each run logs
    elapsed time, application-level successful/attempted pages and first
    refusal evidence. Acceptance remains open until two scheduled runs land.

- [ ] **P0.3 Settle the OLX runner policy.**
  - On a first-request 403, stop the whole portal for that run without cooldown,
    town expansion or bands.
  - Retain a low-frequency reachability probe or a local/residential execution
    path so the scraper is not discarded.
  - Make source-count claims dynamic; never say “five portals” for a four-source
    dataset.
  - **Accept when:** a blocked CI run uses at most one probe per type (preferably
    one for the portal), finishes in seconds and publishes `blocked: 403`.
  - **Implemented locally 2026-08-23:** the first root 403 performs no cooldown
    or follow-up requests and stops the portal. The unrequested type receives a
    synthetic blocked row that counts as zero searches/pages/issues; generated
    source-count copy uses positive contributors and names blocked sources.
    Acceptance remains open until a scheduled runner confirms the one-probe log.

- [ ] **P0.4 Bound n-online and separate archive harvesting.**
  - Identify which towns hit 200 pages instead of hiding them in a two-row
    aggregate.
  - Avoid walking tens of thousands of archive records twice daily merely to
    recover a small active set; give archive refresh its own cadence/cache.
  - Define town coverage and a stable priority order for cold regions.
  - **Accept when:** the phase is at most 40 minutes on warm Śląskie, every
    capped town is named, and active-vs-archive coverage is explicit.

- [ ] **P0.5 Split photo work into correctness-critical and history backlog.**
  - Process current cross-source size collisions first because they determine
    today’s dedupe result.
  - Use remaining budget for unique-listing fingerprints needed only for future
    relist history.
  - Persist backlog age/count so “budget exhausted” is measurable per region.
  - **Accept when:** all correctness-critical candidates are processed, the
    phase is at most 60 minutes on a warm region, and history-only backlog never
    blocks publishing.
  - **Reassess before coding:** the two latest warm runs completed all photo
    work in 74/50 seconds with no budget exhaustion because the cache converged.
    The requested priority split is still architecturally useful for cold
    regions, but it is no longer the current Śląskie runtime blocker.

- [ ] **P0.6 Add a cheap CI quality gate and run summary.**
  - Run all offline tests before any network work.
  - Validate every generated JSON file and manifest/shard count.
  - Publish one concise per-phase/per-source summary, including output bytes.
  - **Accept when:** a parser/unit failure spends no portal requests and a green
    job exposes health, runtime, counts, coverage and size without log mining.

**P0 exit gate:** two consecutive warm Śląskie runs publish without a silent
source regression, finish within 180 minutes (150 preferred), expose truthful
health/coverage, and retain the expected data branch/deploy behavior.

### P1 — make the product genuinely region-aware

- [ ] **P1.1 Add one canonical 16-region catalog.** Include slug, Polish label,
  TERYT prefix, enabled state, cadence and optional anchor. Validate portal
  slugs rather than assuming all four portals share them.
- [ ] **P1.2 Fix regional navigation and state.** Preserve `region` when filters
  update the URL, scope localStorage by region, keep all app/stats links in the
  selected region, and give invalid/unpublished slugs a useful response.
- [ ] **P1.3 Build a national root picker from deployed data.** Generate a small
  catalog containing count, updated time, health and data size for every
  published region. Do not hardcode counts in the UI.
- [ ] **P1.4 Generate real regional pages/discovery.** Prefer stable paths such
  as `region/<slug>/` and `region/<slug>/stats/` over query-only SEO. Generate
  canonical, title, description, OG, Dataset JSON-LD, sitemap and `llms.txt`
  entries for each published region; make `/` the Poland picker.
- [ ] **P1.5 Verify branch/cache isolation with two fixture regions.** A region
  refresh must not carry another region’s phash/RCN cache or remove its
  deployed data. Shared cache files may intentionally fork, but this should be
  documented and tested.

### P2 — pilot one new region manually

- [ ] Run a cold `malopolskie` workflow manually, not on cron.
- [ ] Validate all portal region URLs, locality normalization, n-online’s
  derived town list, RCN prefix `12*`, geo convergence, output sizes and every
  health/coverage state.
- [ ] Run a second warm pass to measure cache benefit and convergence.
- [ ] Verify the deploy contains both regions, the picker/counts work, regional
  filters survive reload/share, and no Śląskie text leaks into Małopolskie.
- [ ] Record the pilot in this document with run IDs, timings, request counts,
  source yields, archive size and branch/served bytes.

**Pilot exit gate:** two successful runs, no unexplained count collapse, warm
runtime within the P0 budget, truthful regional metadata and an easy way to
disable the pilot from the catalog without affecting Śląskie.

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
