# rentgen-ofert

Polish real estate sale listing aggregator and market intelligence engine, combining listings across major portals with official transaction price registers.

- **Cross-portal aggregation:** Normalizes and de-duplicates sale listings from Otodom, OLX, Gratka, Morizon, and Nieruchomości-online.
- **RCN transaction benchmarks:** Integrates official GUGiK Rejestr Cen Nieruchomości transaction data to compare asking prices with actual closed deals.
- **Price drops & relistings:** Tracks asking price history, delistings, and reappearing listings over time.
- **Static architecture:** Fast, searchable client-side UI with Leaflet map clusters and private KW (*księga wieczysta*) verification viewer.
- **Documentation:** [`TODO.md`](TODO.md) · [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md) · [`docs/`](docs/)

**Status:** Śląskie and Opolskie are published. Coverage remains partial: OLX is
blocked on GitHub-hosted runners and Otodom/Morizon coverage is partial. See
[`TODO.md`](TODO.md) and the latest [audits](docs/audits/) for current counts.

The `Publication freshness` workflow runs `python3 -m scripts.check_freshness`
every six hours and fails when an enabled region has not published within its
cadence, so a silent freeze shows as a red run instead of green no-op updates.

## Quick Start

```bash
.venv/bin/pip install -r scraper/requirements-test.txt
.venv/bin/pytest -q
```

The test suite is offline. A local preview needs scraped data first; the scraper
contacts the live portals (limit it with `RENTGEN_MAX_PAGES` and `RENTGEN_DELAY`):

```bash
RENTGEN_REGION=slaskie RENTGEN_MAX_PAGES=3 RENTGEN_DELAY=0.3 python -m scraper.main
node scripts/update-summary.mjs
python -m http.server 8000 -d site
```

Then open `http://localhost:8000/region/slaskie/`.

The social card `site/og.png` is rendered from `scripts/og-card.html`:

```bash
npx playwright screenshot --viewport-size=1200,630 scripts/og-card.html site/og.png
```
