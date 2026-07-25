# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-07-14

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
- [x] **Orphan `data` branch**, force-pushed as a SINGLE commit per run,
      holds `site/data/<region>/**` + `cache/**`. Main carries code only.
- [x] **Region = directory** from day one: `site/data/slaskie/{listings.json,
      history.json.gz, archive.json, meta.json, rcnstats.json, stats.json}`,
      caches `cache/phash_<region>.json` + `cache/rcn_<region>.json.gz`
      (`geo_cache.json` stays shared — a town geocoded once serves every
      region). Dashboard + Statystyki read `data/<region>/` (`?region=`,
      default slaskie). Adding a voivodeship = a matrix entry, no layout work.
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
- [ ] **Multi-voivodeship / whole Poland — NEXT.** Prerequisites all done;
      start with the pilot region (małopolskie or dolnośląskie) per the
      rollout order below ↓.
- [ ] **Licytacje komornicze — "deweloperuch dla licytacji"** (nationwide
      bailiff auctions + RCN gap per auction). Feasibility verified
      2026-07-14; full plan in its own section below ↓.

## Plan: scraping whole Poland (notes, 2026-07-07)

Region (voivodeship) stays the unit of everything: one scrape job, one data
dir, one dashboard, one RCN snapshot per region. "Poland" = 16 regions, not
one giant run. Rough scale: Śląskie is ~18k unique / ~29k raw listings, Poland
is ~8–12× that (Otodom alone lists ~250k sales nationwide).

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

### Krok 1 — layout: region = build unit
- `site/data/<region>/{listings,history,archive,meta,rcnstats,stats}.json`;
  per-region caches (`cache/phash_<region>.json`, `cache/rcn_<region>.json.gz`).
- Dashboard + stats page load from the region's data dir (path or `?region=`);
  root `index.html` becomes a region picker with per-region counts.
- TERYT map for RCN already covers all 16 regions — nothing to do there.

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

### Krok 3 — storage (the actual blocker)
- **GitHub hard limits bite before anything else**: 100 MB/file (śląskie
  history.json is already 63 MB — Mazowieckie will cross 100 MB), repo grows
  by ~40 MB of JSON diffs per commit × 16 regions × daily, Pages caps at
  1 GB site / 100 GB-mo bandwidth.
- Stop committing data into main's history before it balloons. Options:
  (a) orphan `data` branch, force-pushed each run (keeps "local scrape IS
  the cache" workflow, history stays 1 commit deep);
  (b) no commit at all — carry history.json between runs as an Actions
  artifact/cache and deploy Pages straight from the artifact;
  (c) external storage (Cloudflare R2 / S3) once even that outgrows.
- Shard or gzip history.json per region either way; the browser never loads
  it, only the pipeline does.
- The **"Payload split"** backlog item above stops being optional at this
  scale: per-region slim index + lazy detail shards, hashed filenames.

### Rollout order
1. Krok 0 audit + fixes, still śląskie-only (no behavior change).
2. Pilot ONE extra region end-to-end (małopolskie or dolnośląskie — mid-size,
   tests the n-online gap and the overflow subdivision).
3. Krok 3 storage switch while the repo is still small.
4. Add regions in batches of 3–4, watching portal error rates in meta.json.
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
- [ ] Re-run "Update listings" once so the first **voivodeship-wide** scrape +
      cache land (the first run is heavy; later runs reuse the cache and are fast).

## Pending — coverage / completeness
- [ ] **Literal "every listing".** Region search is capped by each portal's
      pagination (~`RENTGEN_MAX_PAGES` × ~36/page), so a single region query returns
      the newest N, not all. For exhaustive coverage, iterate per **powiat** (or raise
      `RENTGEN_MAX_PAGES`) on Otodom/OLX/gratka/Morizon — bigger + slower, but complete.
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
- Region URLs (`…/slaskie`) reuse each portal's proven path pattern but couldn't be
  live-verified from the dev sandbox (portal fetches are blocked there). They're a
  one-line change via `RENTGEN_REGION`; validate with the first CI run.
- Locality `city = last breadcrumb segment` assumes gratka/Morizon order their
  breadcrumb specific→general (street, district, city). True on all observed samples.
- Scrapers depend on each portal's page structure; a redesign may need a parser tweak.
  Logic is isolated per portal and covered by tests, so fixes are small.
