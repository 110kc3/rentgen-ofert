# Whole-Poland rollout: status and next tasks

> Audited: 2026-08-13 11:06 UTC; P0.1 implementation update: 11:56 UTC
> Scope: the production snapshot remains the audit baseline. P0.1 is now
> implemented in the local worktree; it has not generated or published a live
> schema-v2 dataset yet.
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
| Portal coverage | Blocked | Otodom regressed by about half after the scout change; OLX is blocked; n-online is capped. |
| Coverage KPI | Implemented locally; live validation pending | Schema v2 owns the denominator at the parent and unions listing IDs across overlapping searches. The published dataset still uses the old schema until the next run. |
| Per-region runtime | Blocked for 16 daily regions | The latest two jobs took 250 and 263 minutes. |
| Region picker and durable regional URLs | Not ready | There is no picker; changing filters removes `?region=`, and saved filters are shared across regions. |
| Per-region metadata / OG / sitemap / llms.txt | Not ready | The generator and committed HTML are Śląskie-only. |
| CI region matrix / cadence | Not implemented | The workflow still schedules Śląskie twice daily and accepts other regions only by manual input. |
| Nationwide data hosting | Not decided | One incomplete region already serves about 102 MB; GitHub Pages has a published-site limit of 1 GB. |

**Rollout decision:** do not add a scheduled second region yet. First complete
the P0 stability gate below. A manual, disposable pilot is the next region
action after that gate—not a 16-region matrix.

## Production snapshot

### Repository and deployment

- HEAD is `5c48745` (`fix: spend otodom's page budget on the bands, cut the
  sweep, and one branch per region`). The local worktree now also contains the
  uncommitted P0.1 slice and rollout documentation.
- The [live site](https://110kc3.github.io/rentgen-ofert/) and
  [live `data/slaskie/meta.json`](https://110kc3.github.io/rentgen-ofert/data/slaskie/meta.json)
  both return HTTP 200.
- [Deploy run 31651087974](https://github.com/110kc3/rentgen-ofert/actions/runs/31651087974)
  logged `overlaid slaskie from data-slaskie` and published on its first attempt.
- Latest published data: **2026-08-12 23:29 UTC**, **26,136** current unique
  properties from **44,399** current raw listings.
- Published data comes from four sources in that run, not five: Otodom, Gratka,
  Morizon and nieruchomości-online. OLX contributed zero.
- The suite now contains **189** offline tests; all **189 passed locally** in an
  isolated temporary environment after P0.1. The Actions scrape workflow still
  has no test step, so a green production scrape is not yet a unit-test gate.

### Validation runs for the latest commit

The 2026-08-12 TODO was waiting for the run triggered by `5c48745`. Two runs on
that commit have now completed and published successfully:

| Run | Trigger | Actual job time | Result | Published properties |
|---|---|---:|---|---:|
| [31576707243](https://github.com/110kc3/rentgen-ofert/actions/runs/31576707243) | push | 250 min | success; created `data-slaskie` | 26,008 |
| [31631007171](https://github.com/110kc3/rentgen-ofert/actions/runs/31631007171) | schedule | 263 min | success; refreshed `data-slaskie` | 26,136 |

[Run 31678762271](https://github.com/110kc3/rentgen-ofert/actions/runs/31678762271)
was still in progress at the audit timestamp and is deliberately not used as
evidence below.

### Latest source health

These are the published `meta.json` values from run `31631007171`:

| Source | Current kept listings | Reported search state | Assessment |
|---|---:|---|---|
| Otodom | 8,541 | 8 truncated rows; displayed `pct` 29.8 | Regression and blocker. Seven upper flat bands were refused. |
| OLX | 0 | Both first pages returned 403 | Blocked on the GitHub runner. |
| Gratka | 12,379 | displayed `pct` 87.4; one parent search capped | Useful but the parent/band warning and percentage need clearer semantics. |
| Morizon | 12,380 | displayed `pct` 103.3 against a lower-bound total | Useful and mostly twinned with Gratka; percentage is not a bounded completeness KPI. |
| nieruchomości-online | 11,099 current | 58,550 rows including archived evidence; flat search capped | Valuable, but expensive and not complete. |

The published unique count is lower than the source sum because Gratka and
Morizon substantially overlap and are merged.

### What the latest change actually proved

- **Per-region branches succeeded.** The first validation run seeded from the
  old shared `data` branch, created `data-slaskie`, and the next run fetched and
  force-refreshed it. The site deployed the new data successfully.
- **The delist change succeeded.** The phase fell from 27–44 minutes in bad
  runs to **37 seconds** and **42 seconds** for 300 checks.
- **Skipping known Gratka/Morizon twins helped but did not clear the photo
  backlog.** The two runs skipped about 8,100 known twins, yet the photo phase
  still took 94–98 minutes and left 5,872 then 4,420 listings unprocessed when
  its budget expired.
- **The Otodom scout hypothesis failed.** The unbanded flat search correctly
  stopped after 12 pages, but Otodom started returning 405 after only about
  5–6 minutes: at `200k-300k` page 35 in the first run and `300k-400k` page 2
  in the second. Kept Otodom listings fell from the long-running **16.6k**
  baseline to **8,461 / 8,541**. This is not evidence of a stable 320-page
  allowance; the current scout is a production coverage regression.
- **OLX remains a runner block, not a parser mystery.** Both types returned 403
  on page one in both validation runs, after the two earlier consecutive 403
  runs documented in `TODO.md`.

### Runtime and scheduling capacity

Approximate phase times from the same two validation logs:

| Phase | Run 315767 | Run 316310 |
|---|---:|---:|
| Otodom | 24.5 min | 22.6 min |
| OLX (blocked) | 1.0 min | 1.0 min |
| Gratka | 14.6 min | 17.9 min |
| Morizon | 20.6 min | 23.3 min |
| nieruchomości-online | 70.6 min | 76.1 min |
| Photo hashing | 94.4 min | 97.6 min |
| Remaining history, RCN, geo and write work | about 24 min | about 24 min |
| **Whole job** | **250 min** | **263 min** |

At the 256.5-minute average, one daily sweep of 16 regions needs about **68.4
runner-hours per day**. `max-parallel: 2` would still need about **34.2 hours**
of wall time. Fitting a daily sweep into 24 hours needs average parallelism of
three, which conflicts with the runner-IP blocking already visible on Otodom
and OLX. The old “16 regions, max-parallel 1–2, once daily” plan therefore does
not fit current measurements.

The capacity gate should be **at most 180 minutes per warm region**, with a
preferred target of **150 minutes** for headroom, before a two-wide daily
schedule is considered. Otherwise the product must explicitly accept a slower
cadence.

### Storage and Pages capacity

Current `data-slaskie` branch contents:

| Part | Size |
|---|---:|
| Whole per-region branch | 159.0 MB |
| `site/data/slaskie` including pipeline-only history | 128.9 MB |
| Pipeline-only `history.json.gz` removed before deploy | 26.5 MB |
| **Approximate data actually served for Śląskie** | **102.4 MB** |
| Caches on the branch | 30.1 MB |
| `index.json` alone | 19.5 MB |
| `archive.json` alone | 7.9 MB |

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
5. **The published coverage percentages cannot gate rollout.** Its schema-v1
   summary combines an unbanded parent with overlapping child bands; failed
   bands can disappear from the denominator and lower-bound totals can exceed
   100%. P0.1 fixes this locally with parent-owned totals, unique-ID unions and
   bounded percentages; production validation is still pending.
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

**Current pick-up point:** P0.2. P0.1 is implemented and fully covered by the
offline suite, but its first live schema-v2 output should be inspected alongside
the Otodom re-measurement.

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
  - **Verification:** Python compilation, JavaScript syntax and whitespace
    checks pass; **189/189** offline tests pass. A production run is deliberately
    still required before treating the new numbers as a live baseline.

- [ ] **P0.2 Restore and re-measure Otodom.**
  - Remove the unproven “~320-page budget” assumption from behavior and docs.
  - First restore at least the pre-scout coverage floor, then test subdivision
    separately and additively.
  - Log elapsed time, successful requests and first refusal for every run.
  - **Accept when:** two consecutive scheduled runs keep at least 16k Otodom
    listings or a new evidence-backed floor is explicitly approved; no tested
    strategy can cut the published baseline in half silently.

- [ ] **P0.3 Settle the OLX runner policy.**
  - On a first-request 403, stop the whole portal for that run without cooldown,
    town expansion or bands.
  - Retain a low-frequency reachability probe or a local/residential execution
    path so the scraper is not discarded.
  - Make source-count claims dynamic; never say “five portals” for a four-source
    dataset.
  - **Accept when:** a blocked CI run uses at most one probe per type (preferably
    one for the portal), finishes in seconds and publishes `blocked: 403`.

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
