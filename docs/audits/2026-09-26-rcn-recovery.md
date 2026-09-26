# RCN P0 repair and recovery — 2026-09-26

Scope: repair RCN ingestion, prevent loss of deed evidence, and verify recovery
against current listing history. No identity-rule change, portal scrape, data
branch rollback, workflow dispatch, runtime optimization or region expansion.

## Incident and frozen evidence

The September 24 update [35992932009](https://github.com/110kc3/rentgen-ofert/actions/runs/35992932009)
logged 1,914 flat features / 1,808 building features, both with zero retained
transactions, then saved the empty snapshot and passed publication validation.
The September 25 data ref `014e7f7952ef74fa5198b05364a24447ff3d9b1d` carried a
97-byte cache with both layers empty. Its 30,523 cards remained available, but
RCN matches, benchmark towns, gap pairs and confirmed sales were all zero.
Portal coverage and payload integrity checks therefore did not establish RCN
health.

The last healthy reference is
[`027bcc45f7b92c5e58e3a194d644146d4c463d6e`](https://github.com/110kc3/rentgen-ofert/commit/027bcc45f7b92c5e58e3a194d644146d4c463d6e).
Its cache was fetched September 17 and contains **198,439 flat transactions and
465,807 building transactions**. The compressed file SHA-256 is
`0ff615f76e6d47b24a5da7e11c47baf5a3d07deef2543b7af54a073b90457879`.
This immutable cache is the recovery anchor; none of its older listing history
or published payload is restored.

The recovery replay uses the September 26 regional publication
`fa1ca3747cf8c8318afb08a3e87d7c8efb7bfd07`, downloaded into an isolated temporary
directory. Production data branches were not changed during verification.

## Repair behavior

Live WFS probes on September 25–26 returned uppercase property names, with
market values `rynekPierwotny` / `rynekWtorny`. The old parser preserved field
case and read only lowercase keys; its first-character market conversion would
also turn both new values into the unsupported `r`. Field names are now
normalized and market enums mapped explicitly, preserving support for old data.
Unknown market enums fail the refresh rather than silently losing segmentation.

The WFS sometimes omits `next`, including on a full page. Each response must be
a WFS 2.0 FeatureCollection with the requested feature type, matching declared
and parsed counts, and recognized fields. Pagination advances by returned
features, preserving per-page deduplication. WFS `resultType=hits`
queries verify the feature total before and after each layer pull; this avoids
an observed timeout when requesting past the end of the flat layer. If all
totals are unknown, completion requires a validated empty terminal page; a
numeric total can also become available during pagination. Repeated pages,
inconsistent totals, unfinished responses and empty usable layers are failures.

Both provincial cache layers must contain valid records. A reduction greater
than 20% against the previous verified layer is rejected. Fresh data is saved
atomically only after both layers pass; fetch and save failures retain the
previous snapshot. Corrupt/recent-but-empty Silesian caches recover from the
pinned reference before attempting a fresh pull. The fallback date stays
September 17, so it cannot masquerade as newly fetched evidence. Opolskie never
uses this Silesian recovery anchor.

`meta.rcn_health` records status, snapshot date, per-layer counts and failure
reason. Listings and statistics pages show the retained snapshot date after a
failed refresh; CI summaries report RCN status separately from portal coverage.
No usable snapshot stops the scraper before writing publication files. The
publication validator independently rejects a disappearance of previously
positive matches, benchmark towns, gap pairs or confirmed sales. It validates
snapshot health, dates, counts and benchmark presence; portal-source overrides
do not bypass these checks. The conservative 20% gate is an operational safety
threshold, not a statistical assertion that legitimate registry removals cannot
exceed it.

## Local verification

- **396 offline tests passed** with `.venv/bin/python -m pytest -q`, including
  old/new schemas and enums, count queries, omitted pagination links, short
  pages, repeated/changing/incomplete responses, empty/shrunken layers,
  interrupted refreshes, failed saves, poisoned-cache recovery, checksum
  rejection, regional isolation and publication continuity. JavaScript syntax
  and `git diff --check` pass.
- A real recovery download passed the pinned checksum and exact layer counts.
  With a recent empty cache and a deliberately failed fresh fetch, `refresh`
  restored the audited cache and returned `degraded`, fetched September 17.
- Full recovery replay preserved **57,392 history records and 3,702,897
  observations**, asserting each record remained identical except for derived
  `sales`. All **30,664** live cards linked to the current history. Rebuilt
  output has **2,902** matched records, **1,586** live cards with sale evidence,
  **63** benchmark towns, **13** gap pairs, and **15** confirmed sales in the
  **3,427** archive cards. The schema-2 payload has 64 shards and version
  `22d6e93d8e3f199d970a`.
- The recovered payload passes publication validation against the September 26
  metadata and RCN continuity against the last healthy positive baseline. On
  this 8 GB workstation, the validator's gzip JSON syntax read was substituted
  with a streaming `ijson.parse` pass over every token of the 713 MB source
  history; all other validator checks ran unchanged. `ijson` is a temporary
  audit dependency, not a new project/runtime dependency. The replay retained
  arbitrary-sized photo hashes (no float conversion of integer hashes).

- Real Chromium loaded the recovered listings and statistics pages: all
  30,664 cards, 1,586 cards with sale evidence, 15 confirmed archive sales and
  six SVG charts. A restored RCN card opened its lazy timeline successfully;
  both pages displayed the retained snapshot date and recorded no uncaught
  errors. Portal images were blocked during this local browser check.

- The unchanged Opolskie cache at
  `a2ce6adfd979c02d123bad256840453383479d29` passes the new snapshot validator:
  fetched September 18, 12,957 flat transactions and 32,825 building transactions.
  No Opolskie pull or publication was performed.

- The guarded live pull verified **200,811** usable flat transactions
  (125,439 secondary-market, 53,755 primary-market, 21,617 with no market label).
  The building pull reached **396,000** raw features / **333,604** retained
  transactions before a 120-second read timeout. The unfinished combined
  snapshot was not saved. A complete fresh snapshot is therefore **not
  verified**; the tested recovery remains the last-good September 17 evidence.
  The production session has bounded retries, but its outcome is still pending.

## Production handoff and limits

The ordinary main push triggers the existing workflow. It restores the then-current
regional history, repairs the poisoned RCN cache and rebuilds derived claims and
statistics. Production recovery/deployment is **pending verification**; no run
was dispatched manually and no CI polling is performed after pushing. The owning
[queue](../../TODO.md) records the next-session check.

A verified old-cache fallback protects evidence but does not count as fresh WFS
health. Matching remains probabilistic and conservative; restoring benchmarks
and supported claims does not resolve the separately documented floor/locality/
identity limitations. The healthy-cohort and runtime gates remain open.
