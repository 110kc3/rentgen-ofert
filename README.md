# rentgen-ofert

All **Śląskie voivodeship** house & flat *sale* listings from five portals — **Otodom**,
**OLX**, **gratka**, **Morizon** and **nieruchomości-online** — de-duplicated into one
searchable page. No server: a GitHub Actions cron job scrapes the portals,
writes a JSON file, and a static dashboard on GitHub Pages displays it.

```
GitHub Actions (cron) → python -m scraper.main → site/data/<region>/*.json
        → force-pushed to the orphan `data` branch → GitHub Pages (main site/ + data overlay)
```

Scraped data and caches live on a single-commit **`data` branch**, never in
main's git history — main stays a few MB of code while the data branch is
force-pushed fresh each run (the price history lives *inside*
`history.json.gz`, so old git versions of it carry no information).

## What it does

- Pulls **domy** and **mieszkania** *na sprzedaż* across the **whole Śląskie
  voivodeship** (Katowice, Gliwice, Częstochowa, Bielsko-Biała, Rybnik, …) from all
  five portals — a region-level search on Otodom/OLX/gratka/Morizon and per-city
  sub-domains on nieruchomości-online. Set `RENTGEN_REGION` to scrape a different
  voivodeship. Every listing keeps its **town (locality)**, and the dashboard has a
  searchable **town multi-select** filter.
- Keeps archived / sold listings (e.g. nieruchomości-online *Ogłoszenie archiwalne*)
  out of the dashboard, but harvests them as history evidence (see below).
- **Relist & price history.** Each run fingerprints every property by its photos and
  records price/date in `site/data/history.json`. When an agent re-posts the same flat
  under a new URL, the card is flagged "↻ wystawiane ponownie" with the earlier price,
  and shows "na rynku od …" plus a price trail. History builds forward from the first
  run (needs photos on; can't see listings deleted before the tool started).
- **Per-property lifetime timeline ("rentgen").** Every card has an expandable
  *Historia nieruchomości*: when it was listed on which portal and for how much,
  every price change and re-post, links to the archived gallery photos, when the
  ad disappeared — and, via RCN, when the flat actually changed hands.
- **Real sale prices from notarial deeds (RCN).** Since Feb 2026 GUGiK publishes
  the nationwide Rejestr Cen Nieruchomości for free (WFS at
  `mapy.geoportal.gov.pl/wss/service/rcn`). `scraper/rcn.py` pulls all flat +
  residential-building transactions for the voivodeship into
  `cache/rcn_snapshot.json.gz` (refreshed weekly) and matches them to tracked
  properties by town + area ± street / rooms / floor. A deed *before* a listing
  shows as "🔑 poprzednio sprzedane … za …"; a deed *after* a listing vanished
  confirms "✓ sprzedane wg RCN". Matches are conservative and carry a
  confidence label (wysoka = street-anchored, średnia = attribute-anchored).
- **Cena vs transakcje RCN (negotiation leverage).** `scraper/rcnstats.py`
  aggregates the RCN snapshot into `site/data/rcnstats.json` (~21 KB): median /
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
  archiwalne" flags are harvested as immediate evidence.
- **Developer new-builds handled separately.** Ads flagged as *rynek
  pierwotny* (or detected by keywords / many same-gallery ads on one portal)
  get an "inwestycja" badge, one card per asking price instead of a bogus
  merged "flat", no relist/sold history, and their own **Rynek** filter —
  hide them entirely with *Rynek: Wtórny* when hunting resale flats.
- **Archiwum view.** The dashboard's "Archiwum / sprzedane" filter shows
  properties that left the market, with their last asking price, the RCN sale
  price when matched, and the full timeline (`site/data/archive.json`).
- **De-duplicates the same property across portals, including at different prices.**
  Candidates must share an exact size (type + area, + rooms for flats); then a
  perceptual hash (dHash) of each listing's **photo gallery** confirms they are
  the same property before merging — so two different same-size flats, even at
  the same price, are kept apart. Each card lists every portal with its price and
  date and **highlights the cheapest**. (Photo checks fetch each ambiguous
  listing's page, so the scrape does extra requests; set `RENTGEN_PHOTOS=0` to
  skip them and fall back to a size+price heuristic.)
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
(`cache/phash_cache.json`) makes repeat runs much faster — each listing's photos are
hashed once and then reused by URL — and pip downloads are cached in CI too.

Dashboard URL: `https://<your-username>.github.io/rentgen-ofert/`.

> First push blocked by a `.git/index.lock`? Delete that file and commit again
> (a stale lock was left behind — see TODO.md).

### B) Scrape locally, let CI only publish (fastest loop)

All scraper output is committed files (on the `data` branch), so a local
scrape IS the cache — CI never needs to repeat it. Pull the current data,
scrape, push it back as a fresh single commit:

```bash
git fetch origin data && git checkout origin/data -- site/data cache && git reset -q
python -m scraper.main                                   # ~minutes with warm caches
git checkout --orphan data-local && git rm -r --cached -q . \
  && git add -f site/data cache && git commit -m "data: local scrape" \
  && git push --force origin HEAD:data && git checkout -
```

Then publish via **Actions tab → "Deploy site" → Run workflow** (pushes to the
`data` branch can't trigger workflows themselves). The heavy **Update
listings** workflow runs on its cron, on `scraper/**` changes, or manually
(inputs: `rcn` — set `force` to re-pull the RCN transaction snapshot;
`region` — voivodeship slug, default `slaskie`).

### C) Run locally (dashboard preview)

```bash
pip install -r scraper/requirements.txt   # requests + beautifulsoup4 + Pillow
python -m scraper.main                     # scrape -> site/data/slaskie/listings.json
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
| `RENTGEN_MAX_PAGES` | 50 | max result pages per portal per type |
| `RENTGEN_DELAY` | 0.7 | seconds between requests (be polite) |
| `RENTGEN_PHOTOS` | 1 | photo-match ambiguous listings; `0` skips the detail fetches |
| `RENTGEN_PHOTO_BUDGET_MIN` | 90 | max minutes of photo fetching per run (`0` = unlimited); skipped listings retry next run |
| `RENTGEN_TYPES` | house,flat | which to scrape; e.g. `house` for houses only |
| `RENTGEN_VERIFY_MAX` | 300 | stale listings URL-verified per run (`0` disables) |
| `RENTGEN_RCN` | 1 | `0` skips RCN; `force` re-pulls the transaction snapshot now |
| `RENTGEN_GEO` | 1 | `0` skips geocoding listings for the map view |
| `RENTGEN_GEO_MAX` | 500 | max new UUG geocoder lookups per run (cache does the rest) |
| `RENTGEN_NOL_TOWNS` | 60 | max nieruchomości-online town sub-domains per region |

**Rate limiting (HTTP 429):** the scraper backs off and retries automatically. If a
portal still rate-limits you (nieruchomości-online is strict, especially on repeat
runs), slow down with `RENTGEN_DELAY=2`, scrape less with `RENTGEN_TYPES=house`,
skip the heavy photo step with `RENTGEN_PHOTOS=0`, and avoid back-to-back runs.

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
python -m pytest -q          # parser + dedupe unit tests (offline, use fixtures)
```

## Customise

- **Region** — set `RENTGEN_REGION` (a voivodeship slug). The scrapers, caches,
  data dir and RCN pull are all region-driven; nieruchomości-online (which has
  no region-wide search) derives its town list from the other portals' results
  and caches it in `cache/nol_towns.json`. For the dashboard, add an entry to
  `REGION_CONFIG` in `site/app.js` — the label and the optional
  distance-from-anchor filter; a region without an anchor city simply hides that
  control. **Read the whole-Poland plan in `TODO.md` first**: every portal's
  pagination cap already truncates śląskie, so a second region would add a
  second partially-scraped dataset until that is fixed. For rentals or other
  scopes, edit the `SEARCH` URLs in each `scraper/<portal>.py`.
- **Add a portal** — write a module exposing `scrape(max_pages, delay, ...)`
  that returns the shared listing dict (see the docstring in
  `scraper/normalize.py`) and add it to `SOURCES` in `scraper/main.py`.
- **Schedule** — the `cron` line in `.github/workflows/update.yml`.

## Project layout

```
scraper/
  otodom.py  olx.py  gratka.py  morizon.py  nieruchomosci_online.py   per-portal scrapers
  net.py         shared HTTP session with 429 back-off; history.py  property lifecycle store
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
cache/                 (on the `data` branch, gitignored on main)
  phash_<region>.json   gallery-hash cache, reused run-to-run (auto-pruned)
  rcn_<region>.json.gz  RCN transaction snapshot (refreshed weekly)
  geo_cache.json        geocode cache, shared across regions (town/street -> lat,lon)
  nol_towns.json        per-region town lists for n-online (slug -> display name)
site/
  index.html  app.js  styles.css        listings dashboard + map view (GitHub Pages)
  stats.html  stats.js  stats.css       Statystyki market dashboard (SVG charts)
  data/<region>/  manifest.json (content version) + index.json (slim grid) +
                  d/NN.json (lazy detail shards, see scraper/payload.py),
                  history.json.gz, archive.json, meta.json, rcnstats.json,
                  stats.json   (generated each run; on the `data` branch —
                  one directory per voivodeship, ?region= to view)
tests/         parser + dedupe + history + RCN + stats + geo tests, offline fixtures
.github/workflows/   update.yml (cron scrape) + deploy.yml (Pages publish)
TODO.md        roadmap / pending work (kept in sync with this README)
```

## Notes on etiquette & law

A **personal** tool: it reads publicly listed ads, links back to the source
rather than rehosting them, throttles requests, and stores no buyer/seller
personal data. Portals' terms generally discourage automated access and Polish
database-protection law applies to large-scale re-use — keep it personal-scale.
If you ever make it public, review each portal's Terms of Service first.
