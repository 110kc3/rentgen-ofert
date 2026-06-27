# TODO — rentgen-ofert

> Keep this file and `README.md` updated after each change.
> Last updated: 2026-06-16

## Done
- [x] Otodom scraper (houses + flats, Gliwice) — parses `__NEXT_DATA__` JSON
- [x] OLX scraper — parses `__PRERENDERED_STATE__`; skips Otodom-syndicated ads
- [x] gratka scraper — parses server-rendered `data-cy` cards (BeautifulSoup)
- [x] nieruchomości-online scraper — parses schema.org JSON-LD offers
- [x] Cross-portal de-duplication, **matches the same property even at different prices**
- [x] Each card shows every source's link + price + date added, and a price range
- [x] Static dashboard: filters (type/source/owner/price/area/rooms), search, sort
- [x] Resilient scrapers — a page error keeps prior results instead of dropping the portal
- [x] GitHub Actions cron + Pages deploy (`.github/workflows/update.yml`)
- [x] Unit tests (parsers + dedupe) with offline fixtures — `python -m pytest -q`
- [x] Seed data committed (`site/data/listings.json`)
- [x] Skip archived nieruchomości-online listings (`availability: OutOfStock`)
- [x] gratka: extract the real listing photo (was grabbing UI icon SVGs)
- [x] Tighten dedupe to stop over-merging distinct flats — exact key
      (type + area + price to 1000 zł); no room/district keys, no price chaining
- [x] Merge the same flat across portals at different prices + highlight the
      cheapest — exact-area match (type+area[+rooms]) bounded to a +15% price spread
- [x] Photo-matching: perceptual hash (dHash) of each ambiguous listing's gallery
      confirms it's the same property before merging — precise, no false merges

## Pending — deploy (your one-time actions)
- [ ] Delete the stale `.git/index.lock` left in the repo, then commit & push
- [ ] GitHub → Settings → Pages → Source: **GitHub Actions**
- [ ] GitHub → Settings → Actions → Workflow permissions: **Read and write**
- [ ] Run the "Update listings" workflow once for the first full scrape

## Done (area expansion)
- [x] Widen search to Gliwice + ~40 km — radius on Otodom/OLX, powiat + nearby
      towns on gratka/nieruchomości-online; capture each listing's town (locality)
- [x] Locality (town) filter in the dashboard

## Done (history)
- [x] Relist + price history via photo fingerprint — persistent `history.json`,
      flags re-posted listings ("↻ wystawiane ponownie") + price trail per card.
      Accumulates forward; history.json is committed by the Action each run.

## Done (sources)
- [x] Added Morizon (reuses gratka's card frontend — same media group)
- [x] Assessed sprzedajemy (very few Gliwice listings), domiporta + gethome
      (client-rendered shells / aggregator) — deferred, would need a headless browser

## Pending — features / ideas
- [ ] **adresowo.pl** — results are client-side rendered (no listings in the
      initial HTML); needs a headless browser (Playwright) or its JSON API.
      Deferred to keep the no-browser model.
- [ ] More portals: domiporta.pl, sprzedajemy.pl, Facebook Marketplace
- [ ] Daily email digest of new / price-changed Gliwice listings
- [ ] Price-history view (the Action commits data each run → use git history)
- [ ] Map view of listings
- [ ] Optional rentals (wynajem) toggle

## Known issues / notes
- Scrapers depend on each portal's page structure; a redesign may need a parser
  tweak. Logic is isolated per portal and covered by tests, so fixes are small.
- Dedupe is a heuristic (type + area + rooms + district, or type + area + price).
  Two near-identical distinct listings could occasionally merge.
