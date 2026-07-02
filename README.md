# rentgen-ofert

All **Śląskie voivodeship** house & flat *sale* listings from five portals — **Otodom**,
**OLX**, **gratka**, **Morizon** and **nieruchomości-online** — de-duplicated into one
searchable page. No server: a GitHub Actions cron job scrapes the portals,
writes a JSON file, and a static dashboard on GitHub Pages displays it.

```
GitHub Actions (cron) → python -m scraper.main → site/data/listings.json → GitHub Pages (site/)
```

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
  and sort by newest, price, zł/m² or area. Active filters show as removable chips
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

### B) Run locally

```bash
pip install -r scraper/requirements.txt   # requests + beautifulsoup4 + Pillow
python -m scraper.main                     # scrape -> site/data/listings.json
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
| `RENTGEN_TYPES` | house,flat | which to scrape; e.g. `house` for houses only |
| `RENTGEN_VERIFY_MAX` | 300 | stale listings URL-verified per run (`0` disables) |
| `RENTGEN_RCN` | 1 | `0` skips RCN; `force` re-pulls the transaction snapshot now |

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
would accept, with confidence. Needs `cache/rcn_snapshot.json.gz` (created by
the scraper's weekly RCN pull).

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

- **City / scope** — edit the `SEARCH` URLs in each `scraper/<portal>.py`
  (swap `gliwice`, or add rentals).
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
  main.py        runs every source, photo-checks look-alikes, writes site/data/*.json
cache/
  phash_cache.json      committed gallery-hash cache, reused run-to-run (auto-pruned)
  rcn_snapshot.json.gz  committed RCN transaction snapshot (refreshed weekly)
site/
  index.html  app.js  styles.css      static dashboard (GitHub Pages)
  data/        listings.json, archive.json, meta.json  (generated)
tests/         parser + dedupe + history + RCN tests with offline fixtures
.github/workflows/update.yml           cron + Pages deploy
TODO.md        roadmap / pending work (kept in sync with this README)
```

## Notes on etiquette & law

A **personal** tool: it reads publicly listed ads, links back to the source
rather than rehosting them, throttles requests, and stores no buyer/seller
personal data. Portals' terms generally discourage automated access and Polish
database-protection law applies to large-scale re-use — keep it personal-scale.
If you ever make it public, review each portal's Terms of Service first.
