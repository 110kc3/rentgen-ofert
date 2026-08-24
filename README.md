# rentgen-ofert

A Śląskie-first house and flat *sale* listing aggregator, designed to grow to
all 16 Polish voivodeships. It attempts **Otodom**, **OLX**, **gratka**,
**Morizon** and **nieruchomości-online**, de-duplicates what the portals serve,
and presents it on one searchable page. No application server: a GitHub Actions
job scrapes, writes static JSON, and GitHub Pages displays it.

Portal blocking and serving caps mean “all listings” is a target, not a current
guarantee. The published 2026-08-24 dataset has 31,196 current properties from
four contributing sources. OLX is blocked with HTTP 403; Otodom's 16.3k floor
has recovered, although its flat root remains partial at the 200-page cap.

```
GitHub Actions (cron) → python -m scraper.main → site/data/<region>/*.json
        → force-pushed to the orphan `data-<region>` branch → GitHub Pages (main site/ + data overlay)
```

Scraped data and caches live on single-commit **`data-<region>` branches**,
never in main's git history — main stays a few MB of code while a region's
branch is force-pushed fresh each run (the price history lives *inside*
`history.json.gz`, so old git versions of it carry no information). One branch
per region because a shared one is what a second region would break: Śląskie
alone is currently ~169 MB including caches and pipeline-only history, and
every job would fetch, and force-push over, all of everyone's. A deploy overlays
every `data-*` branch (plus the pre-split shared `data` branch, still read so
the split needed no flag day).

## Poland rollout status

As of 2026-08-24, **1 of 16 voivodeships is published**. Region-scoped output,
all 16 RCN/TERYT mappings and per-region data branches are implemented; the
`data-slaskie` branch has been created, refreshed and deployed successfully.

The next step is not a 16-region CI matrix. The latest two completed warm
Śląskie jobs completed in 153 and 168 minutes. Otodom recovered to 16,267 and
16,280 kept listings with all 263 unbanded searches succeeding, while an OLX
page-one 403 caused exactly one portal-wide probe in each run. P0.2 and P0.3
are therefore accepted from production evidence. The P0.4/P0.6 slice
now bounds n-online's current crawl separately from its weekly archive harvest,
adds town-level diagnostics and archive state, and puts 199 offline tests plus
a generated-data validator in front of publication. Live scheduled-run
validation remains. The audited status, evidence, decisions, acceptance
gates and P0–P5 task order are
in [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md). `TODO.md` remains the detailed
development diary.

## What it does

- Searches **domy** and **mieszkania** *na sprzedaż* across the **whole Śląskie
  voivodeship** (Katowice, Gliwice, Częstochowa, Bielsko-Biała, Rybnik, …) on up
  to five portals — a region-level search on Otodom/OLX/gratka/Morizon and
  per-city sub-domains on nieruchomości-online. Set `RENTGEN_REGION` to target a
  different voivodeship, but no second region is production-validated yet.
  Every listing keeps its **town (locality)**, and the dashboard has a searchable
  **town multi-select** filter.
- Keeps archived / sold listings (e.g. nieruchomości-online *Ogłoszenie archiwalne*)
  out of the dashboard. Nieruchomości-online's normal crawl stops after the
  active-results boundary; a separate weekly full harvest retains archived
  rows as history evidence without paying that cost on every run (see below).
- **Relist & price history.** Each run reuses known photo fingerprints and
  attempts new galleries within a time budget, recording price/date in
  `site/data/<region>/history.json.gz`. When an agent re-posts the same flat
  under a new URL, the card is flagged "↻ wystawiane ponownie" with the earlier
  price, and shows "na rynku od …" plus a price trail. History builds forward
  from the first run; budget-deferred fingerprints are retried later, and the
  tool cannot see listings deleted before it started.
- **Per-property lifetime timeline ("rentgen").** Every card has an expandable
  *Historia nieruchomości*: when it was listed on which portal and for how much,
  every price change and re-post, links to the archived gallery photos, when the
  ad disappeared — and, via RCN, when the flat actually changed hands.
- **Real sale prices from notarial deeds (RCN).** Since Feb 2026 GUGiK publishes
  the nationwide Rejestr Cen Nieruchomości for free (WFS at
  `mapy.geoportal.gov.pl/wss/service/rcn`). `scraper/rcn.py` pulls all flat +
  residential-building transactions for the voivodeship into
  `cache/rcn_<region>.json.gz` (refreshed weekly) and matches them to tracked
  properties by town + area ± street / rooms / floor. A deed *before* a listing
  shows as "🔑 poprzednio sprzedane … za …"; a deed *after* a listing vanished
  confirms "✓ sprzedane wg RCN". Matches are conservative and carry a
  confidence label (wysoka = street-anchored, średnia = attribute-anchored).
- **Cena vs transakcje RCN (negotiation leverage).** `scraper/rcnstats.py`
  aggregates the RCN snapshot into `site/data/<region>/rcnstats.json`: median /
  p25 / p75 deed zł/m² per town + flat-size bucket + market (last 24 months,
  ≥ 5 deeds). Every flat card with a benchmark shows **"vs transakcje RCN:
  +18 %"** and an expandable **"💬 Argumenty do negocjacji"** block — what
  similar flats actually sold for, how sales end locally (median % below the
  last asking price and days on market, from properties we watched vanish and
  matched to deeds; accumulates as the tool runs), plus this listing's time on
  market / relists / price cuts. New sort: *Cena vs transakcje RCN ↑*. House
  zł/m² benchmarks are deliberately not published (the RCN budynki layer
  usually carries building-value fragments, not house sale prices).
- **Register freshness — which powiats stopped reporting.** RCN is fed by each
  powiat's own office and they do not keep pace: in 2026-08 Gliwice's newest
  deed was **2026-02-25** while Katowice, Częstochowa and neighbouring Knurów
  were current to mid-July. A stale town silently ages every RCN number and
  makes *Sprzedane wg RCN* permanently empty there, so `rcnstats.py` publishes
  each town's newest deed date (`towns.<town>.deeds`) plus a `stale[]` list of
  the laggards. It surfaces in three places: the negotiation block warns that
  the benchmark is older than it looks, the Statystyki note names the worst
  offenders (or explains why the selected town's RCN line just stops), and the
  empty *Sprzedane wg RCN* view says so outright instead of looking broken.
- **Coverage and source health — knowing when a search was truncated, and by
  how much.** A capped search returns a plausible pile of listings and no hint
  that more exist. Each
  scraper records why each search ended — the portal ran out (`end`), we cut it
  off (`cap`), the portal refused to serve the rest (`portal_cap`) — into
  `meta.json`'s `coverage` block, with a warning per truncated search in the run
  log. **The stop reason alone is not enough**, because the two look identical
  from the page loop: gratka 404s past page 200 exactly like it 404s past a real
  last page. So every portal's own count is read and compared —
  otodom's `pagination.totalItems` (18 505 śląskie flats), gratka's "9856
  ogłoszeń", morizon's "ponad 9000" (a lower bound — it rounds to thousands),
  OLX's `visibleElements` vs the `totalElements` it will actually serve — and a
  search that ends short of it is reported as truncated whatever the stop reason
  said. Coverage **schema v2** assigns every search a role: the region parent
  owns `portal_total` once, disjoint price partitions replace an overflowing
  parent, and overlapping supplements (OLX town searches) never create another
  denominator. Type-scoped portal IDs are unioned across parents, bands, towns
  and retries, producing `served_unique`, `kept_unique`, `current` and
  `archived`; the internal ID sets are stripped before `meta.json` is written.
  Failed/capped/missing partitions remain explicit, `pct` is bounded to 0–100,
  and losing a band cannot improve it. Intentional partitioned-parent/intermediate
  rows no longer emit “raise the cap” warnings—the terminal leaf does.
  `coverage.status`, each source, and each source/type report `healthy`,
  `partial`, `blocked` or `unknown`, independently of process success. The
  dashboard therefore keeps a source that returned no listings visible and
  distinguishes a clean `0` from `blokada` or `brak danych`. Schema v2 has run
  successfully in production through 2026-08-24; the latest output reports
  Gratka healthy, Morizon/Otodom/n-online partial and OLX blocked. The
  served/kept split remains important: each scraper filters
  while parsing (otodom drops INVESTMENT
  bundles, OLX drops ads syndicated from Otodom), and comparing kept-against-
  stated declared all ~60 OLX town searches truncated — 126 warnings in one run,
  nearly all false. Schema v2 reports that distinction directly as
  `served_unique` and `kept_unique`, with `listings` retained as the current
  kept-count compatibility field. All four paginated portals record it: gratka
  and morizon were left out of the first cut, and because a price band's *new*
  count is legitimately a fraction of the band's stated total, every one of
  their bands read as truncated (20 more false warnings per run) until they
  reported what they were served too.
- **Price bands — seeing past the window a portal will serve** (`scraper/bands.py`).
  Every portal hands over far less than it admits to holding: otodom states
  18 505 śląskie flats but deep pages go thin and erratic past ~150,
  gratka/morizon 404 past page 200 (7 000 ads, ever), OLX serves 1 000 of a
  stated 5 503. Their location taxonomies will never agree — otodom nests
  region/powiat/gmina/city, the others take one slug — but all four filter on
  price, so that is the axis subdivision uses. The unbanded search runs first
  and is kept (priceless ads live only there), then while a search's stated
  total exceeds its portal's window the price range is bisected and the halves
  are walked, merging by URL. Bands are half-open `[lo, hi)` so a boundary price
  lands in exactly one band, and the seed bands' totals are asserted to sum to
  at least the unbanded total — that arithmetic is how a portal's price filter
  silently dropping ads gets caught. Additive throughout: a bad band costs one
  request and can never lose a listing already held. `RENTGEN_BANDS=0` disables
  it. OLX also keeps its per-town subdivision, and bands stack on top of it —
  which is why an *empty* search must never look like a refusal: a village with
  no flats states no total and serves no ads, and reading that as overflow made
  every empty band bisect into two more (see the 2026-08-10 entry in `TODO.md`).
  A portal can also simply refuse the bands. Otodom did so on the same seven
  upper flat bands throughout the affected runs, cutting its stable ~16.6k
  baseline to ~8.5k. Otodom therefore now runs the
  full unbanded crawl by default. `RENTGEN_OTODOM_BANDS=1` enables a separate
  experiment only *after* that baseline is already collected, so a failed band
  cannot halve the published source again. Each Otodom run logs elapsed time,
  successful page requests and the first refusal. Two scheduled runs on
  2026-08-23 and 2026-08-24 restored 16.3k listings with 263/263 successful
  unbanded searches, satisfying P0.2; see `POLAND_ROLLOUT.md`.
- **Empty views explain themselves.** When a filter combination returns
  nothing, the dashboard re-runs the filter with each dimension relaxed and
  offers the ones that would bring results back ("Miejscowość: Gliwice — 43"),
  rather than the old dead-end "Brak ofert dla wybranych filtrów". The two
  archive segments carry live counts (*Archiwum · 1 534*, *Sprzedane wg RCN ·
  43*) so a thin slice is visibly thin before you click it.
- **Map view.** The dashboard's **🗺 Mapa** toggle plots the currently
  filtered listings on an OpenStreetMap map (Leaflet + clustering, loaded
  on demand), with markers colored by the listing's price vs local RCN
  transactions (green = below, red = above). Coordinates come from GUGiK's
  free UUG geocoder via `scraper/geo.py` — unique town/street names are
  resolved once into a committed cache (`cache/geo_cache.json`), towns first,
  streets improving over runs (`RENTGEN_GEO_MAX` lookups per run,
  `RENTGEN_GEO=0` to skip). Street-precise pins are exact; town-precise ones
  are scattered ≤400 m around the centroid and marked "≈" in the popup.
- **Statystyki page (`stats.html`).** A separate market dashboard fed by
  `scraper/marketstats.py` -> `site/data/stats.json` (~32 KB): median asking
  zł/m² (weekly, from the tool's own observations) charted against **median
  transacted zł/m² from notarial deeds** (monthly since 2018, wtórny +
  pierwotny) — per town or voivodeship-wide; active supply per week; new /
  withdrawn / price-cut counts; days-on-market histogram; stat tiles. Charts
  are dependency-free responsive SVG with tooltips, a data table under each
  chart, and a validated color palette (light + dark). Deed series lag a few
  months (registry delay); ask series build forward from the first run.
- **Delisting detection.** Listings that stop appearing are not assumed dead
  (region searches are pagination-capped) — up to `RENTGEN_VERIFY_MAX` stale
  URLs per run are fetched and only 404s / "ogłoszenie nieaktualne" pages /
  archive redirects mark a property *wycofane*. n-online's own "Ogłoszenie
  archiwalne" flags are harvested as immediate evidence. The checks run
  concurrently, on a session that does not retry, under
  `RENTGEN_DELIST_BUDGET_MIN`: a liveness probe's honest answer can be "could
  not tell" — the record comes round next run — and inheriting the scraper's
  retry ladder for it cost 27–44 min of three separate runs.
- **Developer new-builds handled separately.** Ads flagged as *rynek
  pierwotny* (or detected by keywords / many same-gallery ads on one portal)
  get an "inwestycja" badge, one card per asking price instead of a bogus
  merged "flat", no relist/sold history, and their own **Rynek** filter —
  hide them entirely with *Rynek: Wtórny* when hunting resale flats.
- **Archiwum view.** The dashboard's "Archiwum / sprzedane" filter shows
  properties that left the market, with their last asking price, the RCN sale
  price when matched, and the full timeline (`site/data/<region>/archive.json`).
- **De-duplicates the same property across portals, including at different prices.**
  Candidates must share an exact size (type + area, + rooms for flats); then a
  perceptual hash (dHash) of each listing's **photo gallery** confirms they are
  the same property before merging — so two different same-size flats, even at
  the same price, are kept apart. Each card lists every portal with its price and
  date and **highlights the cheapest**. (Photo checks fetch each ambiguous
  listing's page, so the scrape does extra requests; set `RENTGEN_PHOTOS=0` to
  skip them and fall back to a size+price heuristic.)
- **gratka ↔ morizon merge by portal id, for free.** The two portals are one
  database behind two frontends, and their CDN proves it: a morizon card's
  thumbnail is a base64-wrapped origin on *gratka's* CDN carrying gratka's own ad
  id. That id is identity, not resemblance, so the pair merges with no detail
  fetch, no image fetch and no threshold — off the search page. It matters
  because morizon had been serving its galleries from a host the extractor
  didn't match: 0 of its 9 505 listings carried a single hash, so it merged with
  nothing and shipped ~7 089 duplicate cards (21% of everything published).
  Confirmed in production on 2026-08-11: **8 712** published properties now
  carry both sources, and morizon-only is down from ~9 500 to 1 344.
  The same decoding fixes the galleries themselves — the first five URLs are the
  xs/s/m/l/og renditions of *one* photo, so hashing is now per distinct origin,
  and blog teasers riding the same CDN path are excluded. The linking runs
  *before* the photo phase, so a twinned morizon ad costs no detail fetch at
  all — its identity is already settled and its twin's hashes carry onto the
  merged property. ~8 700 fetches a run, handed back to a budget that was
  starving 9 177–18 296 listings.
- Dashboard: filter by **town** (searchable multi-select), type / source / private
  vs agency / price / area / rooms, optional distance-from-Gliwice, full-text search,
  and sort by newest, biggest discount, **price vs RCN transactions**, price, zł/m²
  or area — as a card grid or on the **map**. Active filters show as removable chips
  with one-click reset, and your selection is remembered (saved locally and encoded
  in the URL, so a filtered view is shareable). Every link opens the original ad. No
  seller contact data is stored.

## How to run

### A) Deploy it (the intended way — runs itself, free)

1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Settings → Actions → General → Workflow permissions: Read and write.**
4. **Actions tab → "Update listings" → Run workflow** to do the first full scrape.
   It then re-runs automatically twice a day (06:00 & 18:00 UTC).

The **first** voivodeship-wide run is heavy (it fetches photo galleries for every
look-alike listing to de-duplicate them). After that a committed photo-hash cache
(`cache/phash_<region>.json.gz`) makes repeat runs much faster — each listing's
photos are hashed once and then reused by URL — and pip downloads are cached in
CI too. The cache stores its 256-bit hashes base64-packed inside a gzip (v1 wrote
78-character decimal strings in plain JSON and reached 62.9 MB for one region,
past GitHub's 50 MB warning; a v1 file is migrated on read).

Dashboard URL: `https://<your-username>.github.io/rentgen-ofert/`.

> First push blocked by a `.git/index.lock`? Delete that file and commit again
> (a stale lock was left behind — see TODO.md).

### B) Scrape locally, let CI only publish (fastest loop)

All scraper output is committed files (on the region's data branch), so a local
scrape IS the cache — CI never needs to repeat it. Pull the current data,
scrape, push it back as a fresh single commit:

```bash
REGION=slaskie
git fetch origin data-$REGION && git checkout FETCH_HEAD -- site/data cache && git reset -q
python -m scraper.main                                   # ~minutes with warm caches
git checkout --orphan data-local && git rm -r --cached -q . \
  && git add -f site/data/$REGION cache/geo_cache.json cache/nol_towns.json \
       cache/nol_archive_$REGION.json \
       cache/phash_$REGION.json.gz cache/rcn_$REGION.json.gz \
  && git commit -m "data: local scrape" \
  && git push --force origin HEAD:data-$REGION && git checkout -
```

Then publish via **Actions tab → "Deploy site" → Run workflow** (pushes to a
`data-*` branch can't trigger workflows themselves). The heavy **Update
listings** workflow runs on its cron, on `scraper/**` changes, or manually
(inputs: `rcn` — set `force` to re-pull the RCN transaction snapshot;
`nol_archive` — `auto` uses the weekly cadence, `force` harvests now and `skip`
does only the bounded current crawl; `region` — voivodeship slug, default
`slaskie`). Before contacting a portal it runs the offline tests; after scraping
it validates every generated JSON/gzip file, manifest count, detail shard,
coverage block and runtime summary before anything is pushed.

### C) Run locally (dashboard preview)

```bash
pip install -r scraper/requirements.txt   # requests + beautifulsoup4 + Pillow
python -m scraper.main                     # scrape -> site/data/slaskie/{manifest,index,d/*,...}.json
python -m http.server 8000 -d site         # then open http://localhost:8000
```

Open it through that local server, **not** by double-clicking `index.html` —
browsers block the data `fetch()` over `file://`.

Scrape less while testing (otherwise it pulls every page of every portal):

```bash
RENTGEN_MAX_PAGES=3 RENTGEN_DELAY=0.3 python -m scraper.main
```

| Env var | Default | Meaning |
|---|---|---|
| `RENTGEN_REGION` | slaskie | voivodeship slug to scrape (e.g. `malopolskie`) |
| `RENTGEN_MAX_PAGES` | 200 | max result pages per portal per search (was 50, which silently truncated every portal — see *Coverage*) |
| `RENTGEN_DELAY` | 0.7 | seconds between requests (be polite) |
| `RENTGEN_PHOTOS` | 1 | photo-match ambiguous listings; `0` skips the detail fetches |
| `RENTGEN_PHOTO_BUDGET_MIN` | 90 | max minutes of photo fetching per run (`0` = unlimited); skipped listings retry next run |
| `RENTGEN_TYPES` | house,flat | which to scrape; e.g. `house` for houses only |
| `RENTGEN_BANDS` | 1 | price-band subdivision for supported portals; `0` disables all of it (see *Price bands*) |
| `RENTGEN_OTODOM_BANDS` | 0 | `1` explicitly tests Otodom bands after its full unbanded baseline; never enabled by default |
| `RENTGEN_VERIFY_MAX` | 300 | stale listings URL-verified per run (`0` disables) |
| `RENTGEN_DELIST_BUDGET_MIN` | 10 | max minutes the delist sweep may spend (`0` = unlimited); unasked records retry next run |
| `RENTGEN_RCN` | 1 | `0` skips RCN; `force` re-pulls the transaction snapshot now |
| `RENTGEN_GEO` | 1 | `0` skips geocoding listings for the map view |
| `RENTGEN_GEO_MAX` | 500 | max new UUG geocoder lookups per run (cache does the rest) |
| `RENTGEN_NOL_TOWNS` | 60 | max nieruchomości-online town sub-domains per region |
| `RENTGEN_NOL_ARCHIVE` | auto | n-online archive harvest mode: `auto`, `force` or `skip` |
| `RENTGEN_NOL_ARCHIVE_DAYS` | 7 | minimum days between automatic full n-online archive harvests |

**Rate limiting (HTTP 429/405):** the scraper backs off and retries automatically —
Otodom phrases its refusals as `405 Not Allowed`, so that counts as one too.
`RENTGEN_DELAY` paces more than the pages inside a search: searches are spaced
`4 x` that delay apart, and a transiently refused search is walked once more
after `40 x` it, at most 10 times per portal per run (`bands.SEARCH_PAUSE` /
`bands.ERROR_COOLDOWN` / `bands.MAX_COOLDOWNS`, all on `bands.Pacer`). A 403 on
OLX's first root request is different: it stops that portal immediately, with
no cooldown, second type, towns or bands, while coverage remains explicitly
`blocked: 403`. If a portal
still rate-limits you (nieruchomości-online is strict, especially on repeat runs),
slow down with `RENTGEN_DELAY=2`, scrape less with `RENTGEN_TYPES=house`, skip the
heavy photo step with `RENTGEN_PHOTOS=0`, and avoid back-to-back runs.

## Check one property against RCN by hand

```bash
python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --pokoje 2
python -m scraper.rcncheck Pyskowice 141.5 --typ house --dzialka 800
```

Lists every notarial deed for that size in that town (the register reaches
back to ~2000 in many powiats) and marks which ones the automatic matcher
would accept, with confidence. Needs `cache/rcn_<region>.json.gz` (created by
the scraper's weekly RCN pull; fetch it with the data-branch checkout from
section B if you scraped in CI only).

**Know the exact address?** Search by it directly (no area needed) — this
shows the building's complete sale history:

```bash
python -m scraper.rcncheck Gliwice --ulica "Adama Asnyka" --nr 11
```

**Listings rarely reveal the address — pin it when you learn it.** Add
`--pin <listing-url>` (or edit `overrides.json` by hand) and every future
pipeline run treats the pinned street/number as ground truth for that
listing, upgrading its RCN match to street+number certainty:

```bash
python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --nr 11 \
    --pin https://www.otodom.pl/pl/oferta/mieszkanie-xyz
```

Commit `overrides.json` so CI picks it up.

When you give a street + building number, `rcncheck` automatically asks
GUGiK's free services (UUG geocoder + ULDK) for the **canonical street name
and the cadastral parcel id** (e.g. `246601_1.0041.1506`) and pins those too.
The parcel id is the strongest anchor there is — RCN deed identifiers embed
the same parcel, so a parcel match is decisive in both directions (`--no-uldk`
to skip the lookup offline).

## Tests

```bash
python -m pip install -r scraper/requirements-test.txt
python -m pytest -q
python -m scripts.validate_data site/data/slaskie  # after a scrape
```

The test suite is entirely offline. The data validator checks the emitted
payload as a consumer would and exits non-zero on malformed JSON/gzip, count or
shard mismatches, missing coverage health, or missing runtime diagnostics.

## Customise

- **Region** — set `RENTGEN_REGION` (a voivodeship slug). The scrapers, caches,
  data dir and RCN pull are all region-driven; nieruchomości-online (which has
  no region-wide search) derives its town list from the other portals' results
  and caches it in `cache/nol_towns.json`. For the dashboard, add an entry to
  `REGION_CONFIG` in `site/app.js` — the label and the optional
  distance-from-anchor filter; a region without an anchor city simply hides that
  control. **Read [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md) first**: source
  coverage, runtime, regional URLs/navigation and hosting all have gates before
  a second region is scheduled. For rentals or other scopes, edit the `SEARCH`
  URLs in each `scraper/<portal>.py`.
- **Add a portal** — write a module exposing `scrape(max_pages, delay, ...)`
  that returns the shared listing dict (see the docstring in
  `scraper/normalize.py`) and add it to `SOURCES` in `scraper/main.py`.
- **Schedule** — the `cron` line in `.github/workflows/update.yml`.

## Project layout

```
scraper/
  otodom.py  olx.py  gratka.py  morizon.py  nieruchomosci_online.py   per-portal scrapers
  net.py         shared HTTP session with 429/405 back-off; history.py  property lifecycle store
  coverage.py    non-overlapping completeness accounting + source/region health
  bands.py       price-band subdivision — see past each portal's serving window
  normalize.py   shared schema, value helpers, cross-portal dedupe
  photomatch.py  perceptual hashing of galleries to confirm same-property merges
  cache.py       photo-hash cache (URL -> hashes + gallery URLs), reused run-to-run
  delist.py      URL-verifies vanished listings before marking them "wycofane"
  rcn.py         RCN (notarial-deed prices) WFS pull + probabilistic sale matching
  rcnstats.py    deed zł/m² benchmarks + ask-vs-sold gap + per-town register
                 freshness (stale powiats) -> rcnstats.json
  marketstats.py weekly/monthly market time series -> stats.json (Statystyki page)
  geo.py         UUG geocoding of towns/streets + EPSG:2180 -> WGS84 (map view)
  uldk.py        address -> canonical street + cadastral parcel (UUG + ULDK)
  rcncheck.py    manual RCN lookup / --pin; overrides.py  hand-pinned addresses
  main.py        runs every source, photo-checks look-alikes, writes site/data/*.json
  requirements-test.txt  runtime dependencies plus the pinned pytest range
cache/                 (on the `data-<region>` branch, gitignored on main)
  phash_<region>.json.gz  gallery-hash cache, reused run-to-run (auto-pruned)
  rcn_<region>.json.gz  RCN transaction snapshot (refreshed weekly)
  geo_cache.json        geocode cache (town/street -> lat,lon). One of the two
                        cache files copied onto every region's branch, so it
                        forks per region: a town on a border is looked up once
                        by each neighbour, which is cheaper than sharing state
                        between jobs that force-push
  nol_towns.json        per-region town lists for n-online (slug -> display name)
  nol_archive_<region>.json  last full n-online archive harvest and town bounds
scripts/
  validate_data.py      publication gate for generated regional payloads
site/
  index.html  app.js  styles.css        listings dashboard + map view (GitHub Pages)
  stats.html  stats.js  stats.css       Statystyki market dashboard (SVG charts)
  data/<region>/  manifest.json (content version) + index.json (slim grid) +
                  d/NN.json (lazy detail shards, see scraper/payload.py),
                  history.json.gz, archive.json, meta.json, rcnstats.json,
                  stats.json   (generated each run; on the `data-<region>` branch —
                  one directory per voivodeship, ?region= to view)
tests/         parser, crawl-boundary, payload, history, RCN, stats and geo tests
.github/workflows/   update.yml (cron scrape) + deploy.yml (Pages publish)
POLAND_ROLLOUT.md  current nationwide status, gates and ordered task plan
TODO.md        detailed development diary + other pending work
```

## Notes on etiquette & law

A **personal** tool: it reads publicly listed ads, links back to the source
rather than rehosting them, throttles requests, and stores no buyer/seller
personal data. Portals' terms generally discourage automated access and Polish
database-protection law applies to large-scale re-use — keep it personal-scale.
If you ever make it public, review each portal's Terms of Service first.
