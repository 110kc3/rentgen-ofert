# rentgen-ofert (KW Integration Branch)

Polish real estate sale listing aggregator and market intelligence engine with private KW (*księga wieczysta*) catalogue integration.

- **Cross-portal aggregation:** Normalizes and de-duplicates sale listings from Otodom, OLX, Gratka, Morizon, and Nieruchomości-online.
- **RCN transaction benchmarks:** Integrates official GUGiK Rejestr Cen Nieruchomości transaction data to compare asking prices with actual closed deals.
- **KW catalogue integration:** Connects with `sprawdz-kw` to resolve and link property addresses to Land and Mortgage Registers.
- **Static architecture:** Searchable client-side UI with Leaflet map clusters and interactive KW verification viewer.
- **Documentation:** [`docs/KW_INTEGRATION.md`](docs/KW_INTEGRATION.md) · [`TODO.md`](TODO.md) · [`POLAND_ROLLOUT.md`](POLAND_ROLLOUT.md)

## Quick Start

```bash
# Run unit test suite
PYTHONPATH=. pytest -q tests

# Serve the static frontend locally
python3 -m http.server 8000 --directory site

# Run dry-run regional scrape
python3 -m scraper.main --region slaskie --dry-run
```
