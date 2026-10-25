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
it. Public Pages does not call the private API: the current client only enables
same-origin access on loopback HTTP, and the server binds to loopback.

For Raspberry Pi remote hosting, authenticated HTTPS access and explicit trusted
hostname/origin support remain to be completed. An SSH tunnel using the same port
works for the initial smoke test. Do not expose the bare development server or put
database files under `site/`. Login, a public domain and Pi service startup have not
been configured. The private plan explains Tailscale and HTTPS reverse-proxy options.

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
`docs/STORAGE.md`. The Pi/ARM64 environment still needs its own tests.

This branch has not been merged into public main or deployed to Pages. No real
private catalogue records, credentials, SQLite files or generated datasets are
included in the public changes.
