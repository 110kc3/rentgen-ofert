# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-07-02

## Done (property lifetime timeline + RCN — this round)
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

## Done (developer new-builds + UI perf — this round)
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

## Done (RCN matching v2 + validator — this round)
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

## Done (address lookup + manual pinning — this round)
- [x] `rcncheck` searches by exact address (`--ulica`, `--nr`, area optional,
      flats+houses) — shows a building's full sale history back to ~2000.
- [x] **overrides.json + `--pin`**: hand-learned addresses attach to listing
      URLs; the pipeline applies them to history snapshots (`manual: true`)
      and the matcher treats street+number as decisive (wysoka), including
      against deeds that lack a usable-area field (kept in the snapshot now).

## Done (address -> parcel resolution — this round)
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

## Done (Śląskie-wide + caching + filtering — this round)
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
- [ ] **Precise distances.** Capture each listing's lat/lon from Otodom/OLX (they
      ship coordinates) so the distance filter works for *every* town, not just the
      ~90 in the hard-coded `TOWN_COORDS` map in `app.js`.

## Pending — features / ideas
- [ ] **adresowo.pl** — client-side rendered; needs a headless browser (Playwright)
      or its JSON API. Deferred to keep the no-browser model.
- [ ] More portals: domiporta.pl, sprzedajemy.pl, Facebook Marketplace
- [ ] Daily email digest of new / price-changed listings
- [ ] Map view of listings
- [ ] Optional rentals (wynajem) toggle

## Known issues / notes
- Region URLs (`…/slaskie`) reuse each portal's proven path pattern but couldn't be
  live-verified from the dev sandbox (portal fetches are blocked there). They're a
  one-line change via `RENTGEN_REGION`; validate with the first CI run.
- Locality `city = last breadcrumb segment` assumes gratka/Morizon order their
  breadcrumb specific→general (street, district, city). True on all observed samples.
- Scrapers depend on each portal's page structure; a redesign may need a parser tweak.
  Logic is isolated per portal and covered by tests, so fixes are small.
