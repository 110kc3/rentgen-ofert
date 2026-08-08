# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-08-08

## Done (2026-08-08, late) — whole-Poland steps 0 + 1: the cap, and the truth

**Where to pick up: "Rollout order" in the whole-Poland plan below, at Step 2
(price-band subdivision).** Steps 0 and 1 are done and described here; every
number they rest on was measured and is written down in that plan section, so
nothing needs re-probing to continue.

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

**What to check on the next CI run** (this is the acceptance test for both
steps, and the input to Step 2). That run is **Actions run 31281062431**,
triggered by the commit that shipped these two steps and still in flight when
this was written — `gh run view 31281062431 --log | grep -E "coverage |!!"`:
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
      2026-07-11, Krok 0 (de-Gliwice) 2026-08-08. Measurement on 2026-08-08
      evening put hard numbers on the blocker: it is **coverage and dedupe, not
      storage** — otodom alone lists 18 505 śląskie flats against our 1 482,
      CI still pins the page cap at 50, and ~2 400 morizon cards are unmerged
      duplicates of gratka cards. Steps 0–3 of the rollout order below are all
      single-region work; the region count only goes up after them ↓.
- [ ] **Licytacje komornicze — "deweloperuch dla licytacji"** (nationwide
      bailiff auctions + RCN gap per auction). Feasibility verified
      2026-07-14; full plan in its own section below ↓.

## Plan: scraping whole Poland (notes 2026-07-07, re-audited 2026-08-08)

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

**Step 2 — price-band subdivision (`scraper/bands.py`), the general fix.**
- [ ] One helper, four portals, params verified above. Contract: run the
      unbanded search first (so priceless ads and anything the filter drops are
      still collected), then while a search's stated total exceeds its reachable
      window, bisect its price range and recurse; merge everything by URL.
      **Additive, exactly like the OLX town subdivision** — a bad band costs one
      request and can never lose a listing already held.
- [ ] Reachable windows (measured, put them in the code as named constants):
      otodom ~100 pages/band (full depth works but goes thin and erratic past
      ~150 — do not trust it), gratka/morizon **7 000 ads** (200-page 404 wall),
      olx **1 000 ads**.
- [ ] otodom `&limit=72`: free 2× fewer requests on the biggest portal.
- [ ] Bands are half-open `[min, max)` so a listing priced exactly on a boundary
      lands in exactly one band; assert the band totals sum to ≥ the unbanded
      total, and log it when they do not (that is how a portal's filter
      silently dropping ads gets caught).
- [ ] Expected cost for genuinely full śląskie coverage: ~2 500–3 000 requests
      ≈ 35–45 min at `RENTGEN_DELAY=0.7` (today: ~1 200 requests / 60 min, of
      which n-online is 48). The scrape phase roughly doubles; it is not the
      bottleneck, the photo phase is.
- [ ] Re-measure after landing: śląskie should go from 18 385 to somewhere
      around 30–40k unique properties. If it does not, the bands are wrong.

Where it plugs in (the seams already exist — nothing needs restructuring):
- `gratka.SEARCH` / `morizon.SEARCH` are already `{type: [base_url, …]}` lists
  precisely so one type can become several searches; the page loop and the
  coverage row are per base URL already.
- `olx.search_url(typ, where)` + the additive `seen`/merge in `olx.scrape()`
  are the working precedent for "re-run a capped search narrower and merge by
  URL" — bands follow the same contract, and after Step 1 the `portal_cap` that
  triggers it actually fires.
- `otodom.SEARCH` is `{type: path}`; add the query string alongside `&limit=72`.
- `coverage.short_of_total()` / `covered()` are the loop-exit conditions: keep
  bisecting a band while it is short of its own stated total.

**Step 3 — the dedupe defects, before they get multiplied by 16.**
- [ ] `photomatch._morizon`: add `img\d*\.staticmorizon\.com\.pl` to the host
      pattern, with a fixture test pinned to a real page (this regex has now
      broken twice — the fixture is the point, not the regex).
- [ ] Dedupe gallery URLs by the **base64 origin payload** in the thumb URL and
      hash one rendition per distinct origin, so `MAX_IMAGES = 5` means five
      photos instead of five sizes of one photo. Improves every gratka/morizon
      merge and shrinks the phash cache at the same time.
- [ ] Use that decoded origin as a **direct merge key** for gratka↔morizon:
      identical origin = same ad, no image fetch, no threshold. Cheapest merge
      in the whole pipeline and it removes ~2 400 duplicate cards in śląskie.
- [ ] Re-check `('gratka','morizon')` in the source-pair histogram afterwards —
      it must stop being zero. Same query is the regression test.

**Step 4 — make one region affordable at ~2× the listings.**
- [ ] **phash cache**: gzip it and pack hashes as base64 rather than 78-char
      decimal strings (54.3 MB → ~10 MB). Unblocks the 50 MB warning today and
      the 100 MB hard failure that a bigger region would hit.
- [ ] **Photo budget**: it is already the binding constraint (80 of 90 min).
      Step 3 removes the wasted rendition fetches; after that, re-time and
      decide between a larger budget, more workers, or hashing only listings
      that actually have a size-collision.
- [ ] **Delist sweep**: 300 checks against 21 639 stale records never converges.
      Prioritise (oldest-first is not the same as most-likely-gone), use HEAD
      where the portal allows it, and scale `RENTGEN_VERIFY_MAX` with the record
      count instead of pinning it at 300.
- [ ] **Geo**: 500 lookups/run at 84.9% located — fine for one region, hopeless
      for 16. Scale the budget per region and let a region converge before the
      next one starts.

**Step 5 — region infrastructure (Krok 2, unchanged in substance).**
- [ ] Split the `data` branch per region (`data-<region>`) so a job fetches its
      own ~150 MB, not everyone's 2.3 GB. Do it before region #2 exists.
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
