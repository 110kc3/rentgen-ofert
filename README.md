# rentgen-ofert

A regional house and flat *sale* listing aggregator, Śląskie-first and designed
to grow deliberately to all 16 Polish voivodeships. It attempts **Otodom**,
**OLX**, **gratka**, **Morizon** and **nieruchomości-online**, de-duplicates
what the portals serve, and presents it on a searchable static site.

**2026-10-17 status:** Śląskie and Opolskie are published, with serial portal
access. Śląskie runs twice daily; Opolskie uses the implemented 72-hour cadence.
Małopolskie is a completed, disabled pilot with its data branch retained.
The KW viewer/filter deployments are verified, and both regional archive
checkpoints are complete. Coverage remains partial; OLX's bounded probe is blocked.

**RCN recovery is verified on Śląskie:** commit `6fbb266` passed its scrape and
Pages deploy, publishing healthy export-backed evidence with 3,850 matched
properties and 112 confirmed archive sales in 78.2 minutes. Opolskie still
retains its older snapshot until its next automatic eligible refresh (October
19, subject to scheduling delays). Strict WFS checks remain; rejected pulls use
both official GUGiK provincial GeoParquet exports, validated before atomic cache
replacement. Source URLs, file hashes and raw counts are retained. PyArrow reads
only matching fields in batches; raw exports stay temporary. Retrieval date does
not assert that every county's underlying register is current.

**P4 storage slice implemented:** the next publications use column-table current
and archive indexes, with archive timelines/photos loaded from separate shards
only when expanded. Older regional datasets remain readable. Frozen-data bytes,
Chromium timings, compatibility and retry checks are in the
[payload guide](docs/PAYLOAD.md). Production verification of this storage push
is pending. Nationwide storage/rollback acceptance remains open.

The seven-healthy-day / three-Opolskie-cycle gate remains open because the
last three automatic Opolskie refreshes all retained degraded RCN evidence.
The repaired two-region observation has not started.
[TODO.md](TODO.md) owns the next checks; the
[October 17 audit](docs/audits/2026-10-17-rcn-exports.md) records frozen evidence
and local verification. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns future
expansion gates. No further region or concurrent matrix is selected.

Regional listings include **Tylko z KW**. Import the separate private evidence
file with **Wczytaj KW**, then explicitly **Powiąż KW** after checking the
property's full address. Flats need a unit KW; houses can link their land KW.
Data and links stay in tab memory and disappear on refresh; imported records
alone infer no associations. See [the KW guide](docs/KW_VIEWER.md).

```
GitHub Actions → python -m scraper.main → site/data/<region>/*.json
        → isolated orphan data-<region> branch → GitHub Pages
```

Each region owns its history/cache branch. Scrapes stage only that region;
Pages overlays the branches and publishes only enabled regions. Failed source
or RCN continuity checks preserve the previous publication. Opolskie hourly
eligibility checks do no portal work until due; failed attempts also wait
72 hours, no-op checks do not deploy, and the global lock queues work. Actual
starts can be delayed by the hourly tick, serialization and GitHub scheduling.

The [development history](docs/HISTORY.md) preserves dated implementation and
production investigations. It is historical evidence, not the accepted queue.

## What it does

- Searches **domy** and **mieszkania** *na sprzedaż* across the selected whole
  voivodeship (currently published: scheduled Śląskie and
  Opolskie) on up to
  five portals — a region-level search on
  Otodom/OLX/gratka/Morizon and per-city sub-domains on
  nieruchomości-online. `RENTGEN_REGION` must name an entry in
  `site/regions.json` whose `enabled` flag is true. Opolskie has an isolated
  data branch and a serial 72-hour cadence, checked hourly and observed in
  production; the seven-healthy-day observation remains open.
  Małopolskie passed its cold and corrective warm gates, then was disabled as a
  completed disposable pilot; its branch remains recoverable.
  Every listing keeps its **town (locality)**, and the dashboard has a searchable
  **town multi-select** filter.
- Keeps archived / sold listings (e.g. nieruchomości-online *Ogłoszenie archiwalne*)
  out of the dashboard. Nieruchomości-online's normal crawl stops after the
  active-results boundary. When due, archive maintenance runs afterward for up
  to 15 minutes per run and resumes its checkpoint on subsequent runs until
  finished. Archived rows feed history without becoming current offers.
- **Relist & price history.** Each run reuses known photo fingerprints, hashes
  covers needed for current dedupe first and attempts new history galleries
  within a time budget, recording price/date in
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
  successfully in production through 2026-09-01. Małopolskie's retained pilot
  output reports Gratka healthy, Morizon/Otodom/n-online partial and OLX blocked.
  Śląskie's transient Otodom block recorded the failure shape that motivated
  the previous-publication gate; seven guarded runs then recovered and retained
  the approved positive source floor. The
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
  every empty band bisect into two more (see the 2026-08-10 entry in `docs/HISTORY.md`).
  A portal can also simply refuse the bands. Otodom did so on the same seven
  upper flat bands throughout the affected runs, cutting its stable ~16.6k
  baseline to ~8.5k. Otodom therefore now runs the
  full unbanded crawl by default. `RENTGEN_OTODOM_BANDS=1` enables a separate
  experiment only *after* that baseline is already collected, so a failed band
  cannot halve the published source again. Each Otodom run logs elapsed time,
  successful page requests and the first refusal. Two scheduled runs on
  2026-08-23 and 2026-08-24 restored 16.3k rows with 263/263 successful
  unbanded searches. Later correctness fixes showed that count included
  cross-category clones, repeated portal cards and promoted cards outside the
  region; three corrected runs on 2026-08-26 kept 15.8–15.9k valid Śląskie
  rows with the same 263/263 request shape, establishing the approved P0.2
  floor. See `POLAND_ROLLOUT.md`.
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
  resolved into a committed cache (`cache/geo_cache.json`), towns first,
  streets improving over runs (`RENTGEN_GEO_MAX` lookups per run,
  `RENTGEN_GEO=0` to skip). Street-precise pins are exact; town-precise ones
  are scattered ≤400 m around the centroid and marked "≈" in the popup. UUG
  can return several same-named places; the scraper selects the result whose
  TERYT starts with the selected region's prefix and includes that prefix in
  the cache key, so one region's centroid cannot leak into another.
- **Regional Statystyki page (`region/<slug>/stats/`).** A separate market dashboard fed by
  `scraper/marketstats.py` -> `site/data/<region>/stats.json`: median asking
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
  price when matched, and the full timeline. Schema 3 reads archive faces from
  `site/data/<region>/archive.json` and expands timeline/photo details from `a/`
  shards; legacy full archive arrays remain supported.
- **De-duplicates the same property across portals, including at different
  prices.** Candidates must share an exact size (type + area, + rooms for
  flats); then perceptual photo hashes (dHash) confirm identity before merging.
  An uncached current collision starts with its search-card cover: a match is
  positive evidence, while a non-match conservatively keeps the ads apart.
  A failed/deferred photo attempt also keeps the whole unresolved size group
  separate; it never silently downgrades into weaker merge evidence.
  Full galleries remain the richer history/relist path. This avoids depending
  on blocked detail pages during cold onboarding without reviving the risky
  size+price fallback. Each card lists every portal with its price and date and
  **highlights the cheapest**. Set `RENTGEN_PHOTOS=0` to skip photo checks and
  deliberately fall back to the size+price heuristic.
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
  vs agency / price / area / rooms, optional distance from the catalog anchor
  (Gliwice in Śląskie), full-text search,
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
   Śląskie then re-runs twice daily (06:00 & 18:00 UTC). Opolskie is checked
   hourly and refreshed only after its 72-hour publication/attempt cooldown.

The **first** voivodeship-wide run is heavy. Current look-alikes hash their card
covers first; remaining time builds the fuller history-gallery cache. After
that, the committed photo-hash cache (`cache/phash_<region>.json.gz`) makes
repeat runs much faster—each result is reused by URL—and pip downloads are
cached in CI too. Positive and negative cover results are scoped, so an old
blocked-gallery verdict cannot suppress a reachable card image and a genuine
cover failure still receives bounded retries. The cache stores its 256-bit
hashes base64-packed inside a gzip (v1 wrote
78-character decimal strings in plain JSON and reached 62.9 MB for one region,
past GitHub's 50 MB warning; a v1 file is migrated on read).

Picker URL: `https://<your-username>.github.io/rentgen-ofert/`; a published
dashboard lives at `.../rentgen-ofert/region/<slug>/`.

> First push blocked by a `.git/index.lock`? Delete that file and commit again
> (a stale lock was left behind — see docs/HISTORY.md).

### B) Scrape locally, let CI only publish (fastest loop)

All scraper output is committed files (on the region's data branch), so a local
scrape IS the cache — CI never needs to repeat it. Pull the current data,
scrape, push it back as a fresh single commit:

```bash
REGION=slaskie
git fetch origin data-$REGION
git checkout FETCH_HEAD -- "site/data/$REGION"
git checkout FETCH_HEAD -- cache || true
git reset -q
RENTGEN_REGION="$REGION" python -m scraper.main          # ~minutes with warm caches
git checkout --orphan data-local && git rm -r --cached -q . \
  && python -m scripts.region_storage stage "$REGION" \
  && git commit -m "data: local scrape" \
  && git push --force origin HEAD:data-$REGION && git checkout -
```

Then publish via **Actions tab → "Deploy site" → Run workflow** (pushes to a
`data-*` branch can't trigger workflows themselves). The heavy **Update
listings** workflow runs on its cron, on `scraper/**` changes, or manually
(inputs: `rcn` — set `force` to re-pull the RCN transaction snapshot;
`nol_archive` — `auto` starts a weekly archive cycle or resumes pending work,
`force` starts/resumes a bounded slice now and `skip` pauses maintenance; `region` — voivodeship slug, default
`slaskie`; `allow_source_regression` — a logged manual-only escape hatch for an
intentional source removal/reset). Before contacting a portal it runs the
offline tests. After scraping it validates every generated JSON/gzip file,
manifest count, detail shard, coverage block and runtime summary, then compares
each previously positive/non-blocked source with the preserved publication
metadata before anything is staged or pushed.

### C) Run locally (dashboard preview)

```bash
pip install -r scraper/requirements.txt   # requests + beautifulsoup4 + Pillow + PyArrow
python -m scraper.main                     # scrape -> site/data/slaskie/{manifest,index,d/*,...}.json
node scripts/update-summary.mjs            # build the picker + stable regional pages
python -m http.server 8000 -d site         # then open http://localhost:8000
```

Open the picker at `http://localhost:8000/` or Śląskie directly at
`http://localhost:8000/region/slaskie/`. Use the local server, **not** a
double-clicked HTML file — browsers block data `fetch()` over `file://`.

Scrape less while testing (otherwise it pulls every page of every portal):

```bash
RENTGEN_MAX_PAGES=3 RENTGEN_DELAY=0.3 python -m scraper.main
```

| Env var | Default | Meaning |
|---|---|---|
| `RENTGEN_REGION` | slaskie | enabled voivodeship slug to scrape; disabled pilot entries are rejected by CI |
| `RENTGEN_MAX_PAGES` | 200 | max result pages per portal per search (was 50, which silently truncated every portal — see *Coverage*) |
| `RENTGEN_DELAY` | 0.7 | seconds between requests (be polite) |
| `RENTGEN_PHOTOS` | 1 | photo-match ambiguous listings and conservatively separate unresolved groups; `0` skips cover/gallery fetches and explicitly enables size/price fallback |
| `RENTGEN_PHOTO_BUDGET_MIN` | 90 | max minutes of uncached photo fetching (`0` = unlimited); current collisions hash one card cover first, while skipped full-gallery history work persists oldest-first |
| `RENTGEN_TYPES` | house,flat | which to scrape; e.g. `house` for houses only |
| `RENTGEN_BANDS` | 1 | price-band subdivision for supported portals; `0` disables all of it (see *Price bands*) |
| `RENTGEN_OTODOM_BANDS` | 0 | `1` explicitly tests Otodom bands after its full unbanded baseline; never enabled by default |
| `RENTGEN_VERIFY_MAX` | 300 | stale listings URL-verified per run (`0` disables) |
| `RENTGEN_DELIST_BUDGET_MIN` | 10 | max minutes the delist sweep may spend (`0` = unlimited); unasked records retry next run |
| `RENTGEN_RCN` | 1 | `force` refreshes the snapshot; `0` skips RCN for local diagnostics, but publication refuses to discard previously positive RCN evidence |
| `RENTGEN_GEO` | 1 | `0` skips geocoding listings for the map view |
| `RENTGEN_GEO_MAX` | 500 | max new UUG geocoder lookups per run (cache does the rest) |
| `RENTGEN_NOL_TOWNS` | 60 | max nieruchomości-online town sub-domains per region |
| `RENTGEN_NOL_ARCHIVE` | auto | n-online archive harvest mode: `auto`, `force` or `skip` |
| `RENTGEN_NOL_ARCHIVE_DAYS` | 7 | days from a completed archive cycle before starting another; pending work resumes each run |
| `RENTGEN_NOL_ARCHIVE_BUDGET_MIN` | 15 | positive finite maintenance budget after the current-offer pass, including forced archive runs |

Archive progress lives in `cache/nol_archive_<region>.json` beside the regional
history. Each slice persists seen portal IDs and the next page per town/type;
failed pages retain their cursor. HTTP 429 stops the whole maintenance slice
without probing remaining towns/types; the next scheduled attempt retries that
page. Other request errors still allow other towns to proceed. The checkpoint is
saved only after history is saved and published through the existing isolated
data-branch transaction. Schema-1 completed states remain readable; corrupt or
foreign-region checkpoints fail closed. A partial slice reports `mode: partial`,
pending partitions, elapsed time, cycle records and a stop reason
(`rate_limited`, `errors`, `budget`, `complete`). Actions reports these separately
from current-source health, including failed-request counts. It preserves the last
completed refresh date. Only draining the queue advances that date. `skip`
preserves the checkpoint. Changing `RENTGEN_TYPES` during an active cycle must
include its pending types.

The maintenance session has no retries; each request timeout is at most 30
seconds and no greater than the remaining budget. The deadline is checked
between requests, so an in-flight response/parse can overrun it. This is not a
hard total-job deadline. Portal page numbers can shift between runs; the cycle
is a best-effort traversal, not a frozen archive snapshot. Current stock is
recollected fully on every run and existing history is retained.

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
shard mismatches, missing coverage health, missing runtime diagnostics, or a
previously contributing source becoming blocked/unknown/zero. Pass the prior
publication with `--previous-meta <path>`; use `--allow-source-regression` only
for an intentional reset because it emits an Actions warning and permits the
otherwise rejected transition.

## Customise

- **Region** — select an existing entry in `site/regions.json`, then set
  `RENTGEN_REGION` to its canonical slug. That one catalog owns the Polish
  labels, TERYT prefix, enabled/cadence state, optional distance anchor and each
  portal's explicit path slug. The scrapers, caches, data directory, RCN pull,
  generated picker/pages and browser state all consume it. A region without an
  anchor simply hides the distance control. Nieruchomości-online (which has no
  region-wide search) derives and caches a region-keyed town list in
  `cache/nol_towns.json`. **Read
  [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md) first**: source coverage, cold runtime
  and hosting still gate a second production region. For rentals or other
  scopes, change the product/search model separately; do not overload a region
  entry.
- **Add a portal** — write a module exposing `scrape(max_pages, delay, ...)`
  that returns the shared listing dict (see the docstring in
  `scraper/normalize.py`) and add it to `SOURCES` in `scraper/main.py`.
- **Schedule** — `.github/workflows/update.yml` and `scripts/schedule_region.py`.
  The catalog owns region enablement/cadence; only Śląskie and Opolskie have
  automatic trigger mappings. Missing or unreadable prior metadata stops the
  Opolskie check. Its attempt marker must upload before restoration or portal
  work; automatic retries respect the marker even when publication fails.

## Project layout

```
scraper/
  otodom.py  olx.py  gratka.py  morizon.py  nieruchomosci_online.py   per-portal scrapers
  net.py         shared HTTP session with 429/405 back-off; history.py  property lifecycle store
  coverage.py    non-overlapping completeness accounting + source/region health
  bands.py       price-band subdivision — see past each portal's serving window
  normalize.py   shared schema, value helpers, cross-portal dedupe
  photomatch.py  cover-first/gallery perceptual hashing for same-property evidence
  cache.py       photo-hash cache (URL -> hashes + image URLs/scope), reused run-to-run
  delist.py      URL-verifies vanished listings before marking them "wycofane"
  rcn.py         RCN WFS pull + export fallback + probabilistic sale matching
  rcn_exports.py validated official provincial GeoParquet ingestion
  rcnstats.py    deed zł/m² benchmarks + ask-vs-sold gap + per-town register
                 freshness (stale powiats) -> rcnstats.json
  marketstats.py weekly/monthly market time series -> stats.json (Statystyki page)
  geo.py         TERYT-selected UUG geocoding + EPSG:2180 -> WGS84 (map view)
  regions.py     validates/serves the canonical 16-region catalog
  uldk.py        address -> canonical street + cadastral parcel (UUG + ULDK)
  rcncheck.py    manual RCN lookup / --pin; overrides.py  hand-pinned addresses
  main.py        runs every source, photo-checks look-alikes, writes site/data/*.json
  requirements-test.txt  runtime dependencies plus the pinned pytest range
cache/                 (on the `data-<region>` branch, gitignored on main)
  phash_<region>.json.gz  gallery-hash cache, reused run-to-run (auto-pruned)
  rcn_<region>.json.gz  RCN transaction snapshot (refreshed weekly)
  geo_cache.json        shared-file geocode cache; active keys start with the
                        region's TERYT prefix (retained legacy keys are ignored)
  nol_towns.json        per-region town lists for n-online (slug -> display name)
  nol_archive_<region>.json  last full n-online archive harvest and town bounds
scripts/
  validate_data.py      payload + previous-source-continuity publication gate
  region_storage.py     exact per-region branch staging + sibling-safe overlay
  schedule_region.py    serial cadence decision + publication/attempt cooldown
  update-summary.mjs    national picker/catalog, regional page and discovery generator
  templates/            regional listing + statistics HTML templates
site/
  index.html                         national picker shell (filled at deploy)
  regions.json                       canonical 16-region catalog
  app.js  stats.js  region-context.js regional data/navigation/state clients
  styles.css  stats.css              dashboard, picker, map and SVG chart styles
  region/<slug>/                    generated stable listing/statistics pages
  data/<region>/  manifest.json (content version) + index.json (compact grid) +
                  archive.json (compact archive faces), d/NN.json + a/NN.json
                  (lazy current/archive details, see docs/PAYLOAD.md),
                  history.json.gz, meta.json, rcnstats.json,
                  stats.json   (generated each run; on the `data-<region>` branch —
                  one directory per voivodeship)
  data/regions.json                  deploy-derived counts/freshness/health/size
tests/         parser, crawl-boundary, payload, history, RCN, geo, site-generation
               and two-region storage-isolation tests
.github/workflows/   update.yml (cron scrape) + deploy.yml (Pages publish)
POLAND_ROLLOUT.md  current nationwide status, gates and ordered task plan
TODO.md        current accepted queue and verification handoff
docs/HISTORY.md dated development diary and unselected historical ideas
```

## Notes on etiquette & law

A **personal** tool: it reads publicly listed ads, links back to the source
rather than rehosting them, throttles requests, and stores no buyer/seller
personal data. Portals' terms generally discourage automated access and Polish
database-protection law applies to large-scale re-use — keep it personal-scale.
If you ever make it public, review each portal's Terms of Service first.
