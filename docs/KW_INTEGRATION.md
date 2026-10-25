# Private catalogue integration and Pi handoff

Development branch: `codex/kw-integration-2026-10-25`. The matching backend and
authoritative Pi plan are in the owner's private `110kc3/sprawdz-kw` repository:
`RPI_HANDOFF.md` and `docs/RPI_DEPLOYMENT.md` on main.

The frontend now supports an exact-address catalogue alongside the existing local
JSON importer. `site/kw-catalogue.js` validates the minimized API response;
`kw-catalogue-view.js` implements the dedicated search form. Regional cards search
the complete address and require confirmation before linking. Land records cannot
be attached as flat registers; ambiguous records are not automatically selected.
The existing KW-only listing filter includes explicit catalogue associations.

The companion command serves one origin:

```text
python -m sprawdz_kw serve --db PRIVATE_DATABASE --site PREPARED_SITE --port 8765
```

API contracts:

- `GET /api/kw/status`: schema 1, service `sprawdz-kw`, catalogue counts/pause state.
- `POST /api/kw/search`: `city`, `street`, `number`, `register_type` (`unit`/`land`),
  and `unit` for a flat. Reply has grouped candidates, separate land context,
  original source dates/hashes and explicit historical/own-I-O status.

Private query and association state stays in tab memory; it does not enter
localStorage, share URLs, public listing JSON or scraper overrides. Refresh clears
it. Public Pages does not call the private API. The client enables loopback HTTP
or HTTPS with a `rentgen-kw-origin` meta tag exactly matching `location.origin`.
Only the private backend inserts this tag into HTML responses; public source and
build assets contain no deployment marker. Requests stay relative to the page
origin, use no-store and reject redirects. The backend still binds to loopback.

For Raspberry Pi remote hosting, explicit trusted HTTPS origin support and optional
Tailscale identity allowlisting are now implemented in the companion backend.
The owner selected private Tailscale HTTPS. The private application service is
installed, enabled and restart-tested with a single allowed identity. Tailscale
account consent to enable Serve/HTTPS is pending; the real remote route is not yet
active or verified. Anonymous/unapproved routes and identity revocation/restoration
pass local checks. A plain SSH tunnel alone does not satisfy the service's Tailscale
identity requirement. Do not expose the bare backend or put database files under
`site/`. The private plan owns deployment paths and the consent/verification handoff.

Prepare public data without scraping:

```bash
python -m scripts.region_storage restore slaskie
python -m scripts.region_storage restore opolskie
python -m scripts.deployment_dry_run --data-root site/data --output OUTSIDE_REPOSITORY_NEW_DIRECTORY
```

Use the builder's `site/` output with the backend. Data/release outputs stay ignored
and the builder validates regional payloads before completing the artifact.

Validation on Windows: **539 pytest tests passed**, including the Node client/link
contracts. The private backend suite and seven browser integration checks also
passed. Browser attachment used fictional offers, not unverified real advertisements.
The prepared preview used the published regional snapshots; no scrape was run.

Portability fixes in this branch keep POSIX locks intact, add real Windows file
locking, support streaming hashes on Python 3.10 and close Parquet files on errors.
Windows lacks POSIX directory-fsync semantics; that limitation is documented in
`docs/STORAGE.md`. On October 25 the Pi/ARM64 run passed all **539 pytest tests**
with Python 3.11.2, Node 22.23.3 and an ARM64 PyArrow wheel. The validated artifact
contains both published regions. Both load real listings, filter/reset and load
timeline details in Chromium. Seven combined checks passed on loopback HTTP and
an authenticated local TLS fixture; the fixture also denied anonymous static/data/API
routes and revoked identity access. Real remote authentication remains unverified.

This branch has not been merged into public main or deployed to Pages. No real
private catalogue records, credentials, SQLite files or generated datasets are
included in the public changes.
