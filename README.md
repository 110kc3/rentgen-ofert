# rentgen-ofert (KW Integration Branch)

Polish real estate sale listing aggregator and market intelligence engine with private KW (*księga wieczysta*) catalogue integration.

- **Cross-portal aggregation:** Normalizes and de-duplicates sale listings from Otodom, OLX, Gratka, Morizon, and Nieruchomości-online.
- **RCN transaction benchmarks:** Integrates official GUGiK Rejestr Cen Nieruchomości transaction data to compare asking prices with actual closed deals.
- **KW catalogue integration:** Searches the companion private `sprawdz-kw` catalogue by exact address and links listings only after explicit confirmation.
- **Static architecture:** Searchable client-side UI with Leaflet map clusters and interactive KW verification viewer.
- **Documentation:** [`docs/KW_INTEGRATION.md`](docs/KW_INTEGRATION.md) · [`TODO.md`](TODO.md) · [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md)

**Status:** Śląskie and Opolskie are published. Coverage remains partial: OLX is
blocked on GitHub-hosted runners and Otodom/Morizon coverage is partial. The
public Pages file-import workflow remains available; private KW records are not
shipped in this repository.

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

Then open `http://localhost:8000/region/slaskie/`. Catalogue search needs the
private `sprawdz-kw` backend; see [`docs/KW_INTEGRATION.md`](docs/KW_INTEGRATION.md).

The social card `site/og.png` is rendered from `scripts/og-card.html`:

```bash
npx playwright screenshot --viewport-size=1200,630 scripts/og-card.html site/og.png
```
