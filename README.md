# rentgen-ofert

Polish real estate sale listing aggregator and market intelligence engine, combining listings across major portals with official transaction price registers.

- **Cross-portal aggregation:** Normalizes and de-duplicates sale listings from Otodom, OLX, Gratka, Morizon, and Nieruchomości-online.
- **RCN transaction benchmarks:** Integrates official GUGiK Rejestr Cen Nieruchomości transaction data to compare asking prices with actual closed deals.
- **Price drops & relistings:** Tracks asking price history, delistings, and reappearing listings over time.
- **Static architecture:** Fast, searchable client-side UI with Leaflet map clusters and private KW (*księga wieczysta*) verification viewer.
- **Documentation:** [`TODO.md`](TODO.md) · [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md) · [`docs/`](docs/)

## Quick Start

```bash
# Run unit test suite
.venv/bin/pytest -q tests

# Serve the static frontend locally
python3 -m http.server 8000 --directory site

# Run dry-run regional scrape
python3 -m scraper.main --region slaskie --dry-run
```
