# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-08-08

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
- [ ] **Does otodom still overflow at 200 pages?** Unknown — Otodom 403s a
      residential IP, so it can only be measured from CI. The next run's
      `meta.json` → `coverage` answers it: a row with `stopped: "cap"` and
      `portal_pages` far above 200 means otodom needs subdividing too, and its
      town URLs are a different shape (`/region/powiat/gmina/city`) than the
      one-slug form that works for OLX/gratka/morizon.
- [ ] **Watch the run time and the photo budget.** More listings means more
      gallery hashing; `RENTGEN_PHOTO_BUDGET_MIN=90` absorbs it over several
      runs by design, but the first run after this change will be heavy.

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
- [ ] **Multi-voivodeship / whole Poland — NEXT.** Krok 1 + Krok 3 shipped
      2026-07-11. Re-audit 2026-08-08 found the blocker is no longer storage
      but **coverage**: every paginated portal already hits its cap inside
      śląskie, so a second region would only add a second partially-scraped
      dataset. Start with overflow detection + subdivision, per the revised
      rollout order below ↓.
- [ ] **Licytacje komornicze — "deweloperuch dla licytacji"** (nationwide
      bailiff auctions + RCN gap per auction). Feasibility verified
      2026-07-14; full plan in its own section below ↓.

## Plan: scraping whole Poland (notes 2026-07-07, re-audited 2026-08-08)

Region (voivodeship) stays the unit of everything: one scrape job, one data
dir, one dashboard, one RCN snapshot per region. "Poland" = 16 regions, not
one giant run. Rough scale: Śląskie is ~18k unique / ~21k raw listings, Poland
is ~8–12× that (Otodom alone lists ~250k sales nationwide).

### Status of this plan (re-audit 2026-08-08)
**Krok 1 and Krok 3 are DONE** (2026-07-11) — region is already the build unit
and the storage switch has shipped. What is left is Krok 0, Krok 2, and two
things this plan did not know about, below.

**The finding that reorders everything: the pagination caps are already
binding in śląskie, today.** From the last successful run's logs:

```
gratka  flat/slaskie  page 50   morizon flat/slaskie  page 50
gratka  house/slaskie page 50   morizon house/slaskie page 50
otodom  flat          page 50   olx     flat          page 25  <- OLX hard cap
otodom  house         page 50   olx     house         page 25
```

gratka/morizon only break on a 404 or an empty page, so reaching the cap means
they never ran out of results. Corroborating signal in the same run:
**n-online returns 10 178 raw listings, Otodom only 3 310** — and Otodom is by
far the bigger portal nationally. n-online leads precisely because it is the
one scraper that already subdivides (~40 town subdomains, each paginated), so
no single search hits a cap.

So "whole Poland" is not 16× the current pipeline — **the current pipeline
does not fully cover even one region.** Subdivision has to come first, and it
makes each region bigger and slower, which invalidates every estimate below
that was made from today's śląskie run.

### Measured cost per region (śląskie, 2026-08-08)
| | |
|---|---|
| scrape runtime | 85–110 min, 2×/day |
| published to Pages | 53 MB (74 MB less `history.json.gz`, which deploy.yml strips) |
| on the `data` branch | 141 MB — site/data 74 + phash 54.3 + RCN 12.2 |
| RCN snapshot | 12.2 MB gz, 666k deeds (198k lokale + 468k budynki) |

Naive ×16, *before* the coverage fix makes regions bigger:
- **Pages ~850 MB against the 1 GB soft cap** — and śląskie is mid-sized. This
  is the new hard ceiling, now that Krok 3 removed the old one.
- **`data` branch ~2.3 GB, and every region's run would fetch all of it**:
  `update.yml` does `git fetch origin data` + checkout of `site/data cache`
  regardless of which region it is scraping. Fix before region #2 — one branch
  per region (`data-slaskie`, `data-malopolskie`) so a job pulls only its own
  ~140 MB.
- Runtime is *not* a cost problem: the repo is public, so Actions minutes are
  unmetered. Portal rate-limiting is the constraint — hence the staggered
  1×/day-per-region matrix in Krok 2.
- Portal 403s are real and already observable: Otodom serves the search JSON to
  GitHub runners but refuses this Pi's residential IP (`__NEXT_DATA__ not
  found`). Relevant if scraping ever moves off CI.

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
  `cache/rcn_<region>.json.gz`); dashboard + stats read `data/<region>/` via
  `?region=`. TERYT map for RCN already covers all 16 regions.
- Still open from this step: root `index.html` is not yet a region picker with
  per-region counts (single region, so nothing to pick between).

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

### Rollout order (revised 2026-08-08 — Krok 1 and 3 already shipped)
1. [x] **Overflow detection + subdivision — done 2026-08-08.** Turned out the
   caps were mostly ours: raising `RENTGEN_MAX_PAGES` 50 → 200 recovered +757
   gratka houses alone, and only OLX caps itself (page 25) and needed real
   subdivision. `scraper/coverage.py` now reports every truncated search in
   `meta.json`. See the Done section at the top; otodom's true depth is the one
   open question and the next CI run answers it.
2. [x] **Finish de-Gliwice-ing — done 2026-08-08.** Dead `normalize.CITY`
   removed; `nieruchomosci_online.py` builds its town list per region from the
   portal's own city index (cached, with the śląskie list as fallback);
   dashboard anchor city is per-region config (`REGION_ANCHOR` in `app.js`)
   instead of a hardcoded Gliwice, and `GLIWICE_DISTRICTS` became a per-region
   district→city fold. See the Done section at the top.
3. [ ] **Split the `data` branch per region** (`data-<region>`) before region #2
   exists — same reasoning as doing Krok 3 early: cheap now, painful later.
4. [ ] **Pilot ONE extra region** end-to-end (małopolskie or dolnośląskie —
   mid-size, exercises the n-online city index and the subdivision).
5. [ ] **Region picker** on the root page with per-region counts.
6. [ ] **Krok 2 CI matrix**, then add regions in batches of 3–4, watching portal
   error rates in `meta.json` and the total Pages payload against the 1 GB cap.
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
