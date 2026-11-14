# Current queue — rentgen-ofert

Updated 2026-11-14. This file owns accepted work and the next-session handoff.
[Development history](docs/HISTORY.md) preserves the former diary and unselected
ideas. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns expansion and capacity gates;
its historical task lists do not authorize additional work.

## Current — 2026-11-04

Last completed slice: adopted canonical AGENTS.md, mirror CLAUDE.md, and agent-instructions CI workflow (`6e0ca66`). Fixed root sys.path in region_storage, schedule_region, and scout_regions for standalone CLI execution (`715fe4f`); 535 tests pass.

### Production status — 2026-11-14

**Data has not been published since November 4** (`data-slaskie` `7f48b4d`,
`data-opolskie` `8e448df`). Every sampled scrape since `715fe4f` fails at the
offline test gate on `test_schedule_region_cli_imports_cleanly`, which passes
locally and fails in Actions; green runs are hourly no-ops. The stability clock
remains at zero and the accepted item below cannot pass until the gate is
repaired. Evidence and nine numbered, unselected proposals are in the
[November 14 triage](docs/audits/2026-11-14-triage.md). The repair itself is not
yet accepted work.

### Accepted next work

- [ ] Verify next scheduled automatic publication across Śląskie and Opolskie cohorts (scheduled scrapes and deploy workflows) without manual workflow dispatch.

### Owner actions / blocked

- Storage & expansion provider selection: S3/R2 object storage infrastructure selection remains unselected by owner; planning-only phase complete.
- Two-region stability clock: observe scheduled publications; new region addition remains blocked pending 7-day stability clock.

### Pending verification

- Commit `6e0ca66` pushed to `origin/main`; [Actions runs](https://github.com/110kc3/rentgen-ofert/actions) pending observation next session.

### History / deferred

## October 22 selected acceptance checks and storage plan

The owner selected fresh two-region RCN acceptance, the stability observation,
and **planning only** for expansion/storage, with push authorized. Infrastructure,
provider/account selection, a new region and manual workflow dispatch remain
outside this batch. The [cohort checkpoint](docs/audits/2026-10-22-cohort-checkpoint.md)
records the current evidence and the next verification procedure; the
[storage plan](docs/STORAGE.md#production-storage-and-expansion-plan--october-22)
defines item 3's deliverable and future acceptance criteria.

Latest Śląskie ref `e351e4e`, published October 22 13:00:42 UTC: 30,970 current
cards, 4,137 archives, 110 sale claims and 3,906 matched histories. Scheduled
scrape `39770778678` and deploy `39783221230` passed; 535 CI tests, all 268 live
JSON files across both regions and nine focused Śląskie Chromium checks pass.
Strict continuity against the previous publication passes without override.
Runtime is 91.3 minutes and critical photo deferrals/backlog remain zero.

Neither remaining acceptance gate is complete. Śląskie still uses its healthy
October 16 RCN cache; the seven-day refresh boundary is October 23. Opolskie
still publishes degraded September 28 RCN, with automatic eligibility October
23 01:36:15 UTC plus schedule/lock delays. Both retained archive checkpoints are
complete, but new maintenance cycles have **100 / 52 pending partitions** after
HTTP 429. Retaining the old checkpoint does not accept those unfinished cycles.
The repaired two-region stability clock remains unstarted, with zero accepted
cycles. Verify the next automatic publications rather than dispatching a run.

Documentation push `bdccad5` verified on main; scheduled scrapes and site deployments continue automatically. No runtime or production configuration changes are included.

## October 22 scheduled source recovery — verified

Pulled `main` with `--ff-only`; already at `385ea9a`. The next accepted task is
complete: [automatic Śląskie scrape 39678803197](https://github.com/110kc3/rentgen-ofert/actions/runs/39678803197)
passed 535 tests, strict source/type/RCN validation and regional staging with
`ALLOW_SOURCE_REGRESSION: false`; [deploy 39689522871](https://github.com/110kc3/rentgen-ofert/actions/runs/39689522871)
passed. This is a real publication, not a green hourly no-op.

New data ref `b0ce686`, published Oct 21 22:51:19 UTC: 31,000 cards, 4,091 archive
faces, 110 sale claims, 3,902 RCN matches; Gratka/Morizon recovered to 12,341 rows
each. Runtime 84.1 minutes, zero critical photo deferrals/backlog, persisted archive
checkpoint complete. All 134 public JSON files validate and nine live Chromium
checks pass. The two removed archive histories are preserved and active; one
carried the former sale claim, explaining the archive/sale-count changes.
See the [source-recovery audit](docs/audits/2026-10-22-source-recovery.md).

Śląskie still uses its healthy October 16 RCN cache. Opolskie remains on its
October 20 publication with degraded September 28 RCN and 52 archive checkpoints
pending. Next automatic eligibility is **October 23 01:36:15 UTC** plus schedule/
lock delays. Fresh two-region RCN acceptance and the stability observation remain
open; the clock has not started. No manual dispatch, override, new region or
hosting work was selected. Earlier dated sections retain their original evidence.

## Earlier October 21 selected address/source repairs

The owner selected both numbered audit findings. Implementation and live UI
verification are complete. The initial data refresh was correctly refused after
Gratka HTTP 503 responses; a healthy automatic replacement remains pending.

- [x] Repair manual address RCN lookup/copy clicks and verify success, re-render,
  clipboard fallback and accurate provider-failure handling in Chromium.
- [x] Investigate the 37-row collapse and reject abrupt source/type volume loss
  before publication, with an explicit logged override for intentional resets.

535 offline tests, 12 focused and 33 broad candidate Chromium checks pass. A real-provider candidate
check reaches UUG, ULDK and both WFS layers with HTTP 200, displays the parcel and
copies the command without opening a listing. The actual failed October 20
metadata is rejected at six source/type transitions; healthy publication drift
and the full frozen public dataset pass. Baselines of at least 100 offers must
retain at least half, independently per source/type. The conservative threshold
does not assert complete coverage or detect gradual long-term decline.
See the [repair audit](docs/audits/2026-10-21-controls-and-continuity.md).

Production follow-up: commit `3780e09` passed
[UI deploy 39627380687](https://github.com/110kc3/rentgen-ofert/actions/runs/39627380687),
and 33/33 live Chromium checks pass, including real GUGiK address lookup/copy.
All 268 public JSON files validate. Its
[scrape 39627380782](https://github.com/110kc3/rentgen-ofert/actions/runs/39627380782)
passed 535 tests but failed source continuity after Gratka returned zero offers.
Regional push and the dependent data deploy were skipped. Śląskie retains the
healthy 14:04 UTC publication (`8145ae2`, 30,876 cards / 4,093 archives / 111 sale
claims) and both regions' prior evidence is intact. This refused refresh cannot
count toward stability. The audit records complete production evidence.

Transport commit `eb7aeab` passed [scrape 39592569525](https://github.com/110kc3/rentgen-ofert/actions/runs/39592569525)
(524 tests and strict validation) and [Pages 39602509595](https://github.com/110kc3/rentgen-ofert/actions/runs/39602509595)
at the single recovery check. Production Opolskie fresh-RCN acceptance and the
seven-day/three-cycle observation remain open; next eligibility remains October
23 01:36:15 UTC plus scheduling delays. No manual dispatch or new region selected.

## Earlier October 21 recovery and feature audit

The owner selected Opolskie RCN transport recovery and a Śląskie feature audit.
Production logs show both GUGiK connections timed out before parsing, spending
26 minutes in the portal retry ladder. RCN now has its own session, 10-second
connect timeout, one adapter retry and up to three complete export-download
attempts. Interrupted streams restart bytes/hashes; invalid data and failed
second layers still preserve the previous atomic cache and retrieval date.

524 offline tests pass. A fresh local refresh of the actual Opolskie cache copy
validated 63,494 flat / 86,224 building deeds in 19.78 seconds. No cache was
uploaded. Commit `8733060` passed its 518-test scrape, strict validation and
Pages deployment. Its previously pending verification is resolved.

Both complete live public trees validate (134 JSON files each). Śląskie passes
32/33 live Chromium checks; manual address RCN check/copy controls are blocked
by event propagation. A transient 37-row Gratka/Morizon collapse also escaped
categorical continuity. These were unselected findings at that audit; both were
subsequently selected and repaired above. The
[earlier audit](docs/audits/2026-10-21-rcn-and-features.md) retains its original evidence.

Opolskie published October 20 01:36:15 UTC with degraded September 28 RCN and
a new archive cycle rate-limited at 52 pending checkpoints. Next automatic
eligibility is **October 23 01:36:15 UTC**, subject to scheduling/lock delays.
Śląskie remains healthy with 30,914 current cards, 4,092 archive cards and 111
sale claims; zero critical photo deferrals/backlog. The repaired two-region
stability clock has **not started**. This transport push requires its own
CI/Pages check; production Opolskie recovery remains pending.

Earlier dated sections below retain their original evidence; this section
supersedes their outstanding-status snapshots.

## Completed repair and selected stability/storage follow-up

The owner selected review items 1–3, then continued items 3 and 4: stability
verification and the measured P4 index/archive slice, with push authorized.
On October 19 the owner selected production acceptance and a local versioned-
storage/rollback prototype, with push authorized.
The owner then selected Opolskie recovery verification and the local deployment
dry-run, with push authorized. Retention/provider selection was not selected.
No additional region, concurrent matrix, new hosting infrastructure, automatic
KW acquisition, historical identity rewrite or manual workflow dispatch is selected.

1. **RCN ingestion repair:** support GML temporal deed dates and use GUGiK's
   official provincial GeoParquet exports when a complete WFS pull fails.
   Both export layers must pass schema, region, unique-ID, file completeness
   and existing snapshot-count checks before atomic replacement. Source URLs,
   file hashes, raw row counts and the WFS failure are retained in provenance.
   Nonpositive rounded prices and nonpositive flat areas are unusable deeds.
   Local verification passed: 476 tests, fresh validated snapshots for both
   regions and frozen-history replays reproducing the prior baseline before
   passing RCN continuity validation with the broader export evidence.
   See the [October 17 audit](docs/audits/2026-10-17-rcn-exports.md).
2. **Documentation reconciliation:** this compact queue replaces the historical
   diary as the current entrypoint. README, rollout status and KW verification
   now distinguish completed evidence from pending acceptance.
3. **Stability gate assessed, not accepted:** the last three automatic Opolskie
   cycles (October 10, 13 and 16) published successfully but all retained degraded
   RCN evidence. They cannot count as three healthy cycles or seven healthy days.
   Restart the observation only after the repaired code publishes a fresh,
   healthy snapshot in both regions. Time and successful CI alone are insufficient.

## Production acceptance — verified October 19

Storage commit `2c20374` passed [scrape 39019602305](https://github.com/110kc3/rentgen-ofert/actions/runs/39019602305)
and [deploy 39019602307](https://github.com/110kc3/rentgen-ofert/actions/runs/39019602307).
All gate/publication steps passed. The live regional copies pass every public
payload/source/RCN check, including schema-3 hashes and both detail namespaces.
Eleven live Chromium checks pass, including archive-detail 503/retry, correct
timelines, sold filtering, mobile layout and the real older Opolskie archive.
[The October 19 audit](docs/audits/2026-10-19-storage.md) records complete evidence.

Śląskie ref `d9613011be98fb8532c8d163ebfdb3a3b7a51771`, updated Oct 19
15:14:04 UTC: schema 3, 30,926 cards, 4,092 archive cards,
3,872 RCN matches and 111 archive sale claims. Healthy export-backed RCN retains
315,432 flat / 576,596 building deeds and the validated October 17 hashes.
Ordinary runtime is 82.3 minutes, with zero critical photo deferrals/backlog;
archive checkpoint remains complete (Oct 15 / 49,854 records).

Opolskie remains at `a50362a7f49edf54dc9bdadbef7c3c2eb4e55a0b`:
schema 2, 3,665 cards, degraded September 28 RCN and complete October 13 archives.
Its next eligibility is **October 19 22:15:19 UTC**, subject to the hourly tick,
queue and schedule delays. The repaired two-region stability clock has **not
started**. Do not dispatch a workflow to accelerate it. Małopolskie remains
disabled and recoverable at `cba13c7`.

## Local versioned storage/rollback — completed October 19

`scripts/versioned_storage.py` stages and validates complete public trees,
seals immutable version directories, then atomically switches an 89-byte
regional pointer. File hashes/lengths cover metadata/statistics as well as the
payload. Interrupted/invalid uploads retain the prior pointer; rollback verifies
the complete target and retains newer versions for open tabs. The local server
rehearses CORS and mutable/immutable cache policy.

Optional per-region pointer URLs reach both listing/statistics readers. Each
page pins all requests to one version; absent configuration retains legacy Pages
behavior. No production region is configured for external storage. The generator
still includes local payloads in its normal Pages workflow; the separately
selected artifact dry-run below omits external payloads without uploading them.
[The storage guide](docs/STORAGE.md) records commands, contract, capacity and limits.

Verification: **504 offline tests**, **12 Chromium prototype checks**, and
successful local publication of both full live payloads (134 / 70 files).
The prior compact-index/lazy-archive slice is production-accepted; its frozen
byte and browser measurements remain in [docs/PAYLOAD.md](docs/PAYLOAD.md).
Nationwide hosting capacity, remote atomic publication and rollout acceptance
remain open. There are no owner-only blockers for the completed local slice.

Prototype/reader commit `f195e9b` passed [scrape 39252423912](https://github.com/110kc3/rentgen-ofert/actions/runs/39252423912)
(504 tests, strict pipeline/source/RCN validation and 140-path regional staging)
and [deployment 39263676649](https://github.com/110kc3/rentgen-ofert/actions/runs/39263676649).
All three shipped reader scripts match the source; 13 live Chromium checks pass,
including both statistics pages. The sale-archive drop from 112 to 111 is traced
to one preserved history returning to the active market under another portal URL;
it is not a count of new transactions. See the audit's production follow-up.

## Deployment artifact dry-run — completed locally October 19

`scripts/deployment_dry_run.py` builds a new isolated `site/` artifact and size
report from frozen Pages inputs plus verified local storage mirrors. Catalog
metadata, raw-data discovery and both readers pin the same immutable version.
External payloads never enter the candidate Pages artifact; legacy siblings stay
on Pages. Missing/corrupt versions or invalid local siblings abort the whole
candidate. Existing artifacts, source data and object pointers are unchanged.

Verification: **518 offline tests**, **12 complete-artifact Chromium checks**,
and **12 pointer-only prototype Chromium checks**. Frozen full-data rehearsal:
126.42 MB for both datasets on Pages versus 9.67 MB with Śląskie external and
Opolskie local. The [storage guide](docs/STORAGE.md) and
[dry-run audit](docs/audits/2026-10-19-deployment.md) record commands, source
versions, exact measurements and limitations. The normal deployment workflow
does not invoke this dry-run; no remote host/provider was configured.

**Historical selected item 1 check:** at Oct 19 20:15:17 UTC Opolskie still
serves its Oct 16 publication and degraded Sep 28 RCN, before its next eligibility
at 22:15:19 UTC. The repaired two-region observation has not started. Continue
after the scheduled publication; do not accelerate it with a dispatch or wait
for the seven-day/three-cycle gate in this session.

## Next accepted checks — after this push

- [x] Verify repair commit `6fbb266` and healthy Silesian RCN production recovery.
- [x] Verify compact storage commit `2c20374`, complete live payloads, archive retry
  and the older regional format; reconcile production documentation.
- [x] Rehearse local immutable publication/rollback and mixed storage backends.
- [x] Verify prototype/reader commit `f195e9b`: scrape/deploy, strict pipeline
  validation and default Pages listing/statistics readers all pass.
- [x] Verify handoff commit `6a5894d`: [scrape 39279297132](https://github.com/110kc3/rentgen-ofert/actions/runs/39279297132)
  and [deploy 39282872502](https://github.com/110kc3/rentgen-ofert/actions/runs/39282872502)
  passed at the one recorded status check.
- [x] Build and verify a local artifact/catalog dry-run; see the completed slice above.
- [x] Verify RCN transport commit `eb7aeab`: scrape/strict validation and Pages pass.
- [x] Check address/continuity commit `3780e09` once: UI deployed, 535 CI tests
  pass, live controls/readers/payloads pass; source guard correctly refuses a
  Gratka outage and preserves the previous publication. See the audit.
- [x] Confirm a healthy automatic Śląskie publication after Gratka HTTP 503
  recovery: scrape 39678803197/deploy 39689522871 passed; full live payload,
  continuity without override and archive reconciliation verified October 22.
- [x] Standardize pytest configuration (`pytest.ini` with `pythonpath = .` and `testpaths = tests`), ensuring direct CLI invocations pass all 535 unit and integration tests cleanly without manual PYTHONPATH overrides.
- [x] Ensure direct execution compatibility for all standalone scripts (`scripts/validate_data.py`, `scripts/versioned_storage.py`, `scripts/deployment_dry_run.py`, `scripts/schedule_region.py`, `scripts/region_storage.py`, `scripts/scout_regions.py`) by resolving root `sys.path` on invocation; verified CLI options and all 538 tests pass.
- [ ] Confirm both regions publish fresh healthy RCN snapshots under the repair.
  Reconcile changed matches, benchmarks and derived sale claims against broader
  export evidence. A rise in source records is not a sales-growth claim.
  Preserve the last good cache if either layer fails validation.
- [ ] From the first healthy repaired two-region baseline, record at least seven
  healthy days and three successful automatic Opolskie cycles. Require source
  continuity, no critical photo deferrals/backlog, persisted archive completion,
  normal no-op behavior, regional isolation, and ordinary plus fresh-RCN runs
  ≤180 minutes (preferred ≤150). The known unresolved two-ad Opolskie group
  must stay separate. Investigate failures/missed cycles and restart after recovery.

Expansion/storage planning is selected and recorded in the storage guide.
Expansion implementation, provider selection, remote migration and the remaining
P4 hosting work require separate selection. Local rollback checks do not accept nationwide
capacity or the seven-day cohort. [POLAND_ROLLOUT.md](POLAND_ROLLOUT.md) owns those gates.

Both address/continuity push verification and healthy Śląskie source recovery
are recorded; do not repeatedly poll those terminal runs. The next TODO is the
fresh healthy two-region RCN check, led by Opolskie's next eligible October 23
publication. Leave guards active and preserve prior data on failure; no manual
dispatch selected. This documentation-only handoff matches neither push workflow.
Two-region fresh-RCN acceptance and the stability cohort remain open. The newest
checkpoint above supersedes earlier same-day publication/maintenance counts.

## Review findings and proposals — 2026-11-14 (not accepted work)

Later the same day `8d66a01` replaced the nonexistent README `--dry-run` command
(B4) and restored the coverage caveat (part of B6). The
[November 14 triage](docs/audits/2026-11-14-triage.md) prioritises these findings
alongside the production freeze; it does not select any of them.

These are unselected review proposals. They do not change, reorder or extend the
accepted queue above; nothing here is authorized implementation until the owner
selects it.

Reviewed 2026-11-14 by Claude Code against commit `9fc89c5`. Read-only review:
nothing was fixed and no file other than this one was changed. Run in a scratch
`git archive` copy with the repo's `.venv` (Python 3.11.2):
`python -m pytest -q -p no:cacheprovider` → exit 0, **538 passed** in 41.5 s;
`node --check` on every `site/*.js`, `scripts/*.mjs` and `tests/*.cjs` → all pass;
`python3 -m site.build` (the AGENTS.md build command) → exit 1. Synthetic
reproduction scripts exercised `history`, `normalize`, `overrides`, `delist` and
`discountOf` from `site/app.js` offline. Not checked: no scraper, portal, RCN,
ULDK/UUG or geoportal request was made; no live payload, browser check, CI run or
`data-<region>` branch was inspected; `scripts/update-summary.mjs` and the
per-portal n-online/Morizon parsers were only skimmed.

Comment-removal commit `9fc89c5`: no functional collateral damage found. No
`# type: ignore`, `noqa`, `pragma`, `fmt`, shebang or encoding line was removed;
CSS colours, URLs, regexes, docstrings and test assertions are intact (only
trailing assertion comments went). Losses are documentary: the county-list
source URL in `scraper/identity.py`, the regeneration command in
`scripts/og-card.html`, the rationale for `[hidden] { display:none !important }`
in `site/styles.css`, and the README's coverage caveats (see B6).

### Bugs

- [ ] **B1 (Medium) — same-size neighbours produce a fake price-drop badge and
  pollute the "discount" sort.** `scraper/normalize.py:507-509` sets
  `prev_price = min(others' prices)` for every member of a 2–3-listing same
  area/rooms/locality group, even when the other listing is *more* expensive;
  `site/app.js:779-786` (`discountOf`) then treats `prev_price` as an earlier
  price of this card. Scenario: two 51.2 m² 2-room flats in one town at
  300 000 and 420 000 zł → the cheaper card shows "▼ −29% (−120 000 zł)" and
  ranks at the top of the discount sort, although its price never changed.
  REPRODUCED (synthetic `link_same_size` + `discountOf`: pct 28.6).
  Acceptance: a card's discount uses only its own observed earlier prices;
  `also_listed` prices never become `prev_price`; a regression test covers the pair.
- [ ] **B2 (Medium) — price history mixes portals, so a one-day source gap
  reads as a price change.** `scraper/history.py:260-272` builds
  `price_history` from the minimum price across *all* offer URLs per date.
  Scenario: Otodom 500 000 + Gratka 520 000 on day 1, Otodom missed on day 2
  (partial Otodom coverage is a known state), both back on day 3 → published
  trail `500 000 → 520 000 → 500 000`, shown on the card as a price history.
  REPRODUCED (synthetic `history.update`, one record, three days).
  Acceptance: a missing offer on a date does not create a trail point; the
  trail changes only when an observed URL's own price changes.
- [ ] **B3 (Medium) — an archived-ad observation dates the delisting on the
  harvest day, not the last live day, which shifts the RCN "sold" window.**
  `scraper/history.py:316-320` sets `delisted = today`, while
  `scraper/delist.py:142` uses the last live date. Scenario: last live
  observation 2026-08-10, n-online archive harvest matches it on 2026-11-14 →
  `delisted` 2026-11-14; the sold window (`rcn.py` −60/+400 days) starts
  2026-09-15, so a deed dated 2026-08-20 is never attached, and the archive card
  shows a delisting date three months late. REPRODUCED (synthetic; the URL-sweep
  path on the same record yields 2026-08-10). Existing tests
  (`tests/test_history.py:121`, `tests/test_bugfixes.py:30`) encode the current
  date, so this needs an owner decision. Acceptance: both lifecycle paths
  produce the same `delisted` date for the same evidence, with tests updated.
- [ ] **B4 (Medium) — the README "dry-run" command runs a full live scrape.**
  `README.md:21` documents `python3 -m scraper.main --region slaskie --dry-run`,
  but `scraper/main.py:78`/`357` never reads `argv`; region comes only from
  `RENTGEN_REGION`. Scenario: a reader follows Quick Start and starts a
  multi-hour crawl of all five portals plus RCN from their own IP, outside the
  `rentgen-scrape` concurrency lock, writing `site/data/` and `cache/`.
  CODE-READING ONLY (not executed, as it would contact portals).
  Acceptance: either the flags exist and `--dry-run` makes no network request,
  or the README stops advertising them.
- [ ] **B5 (Medium) — a malformed `overrides.json` silently drops every pin,
  and `pin()` then overwrites the file.** `scraper/overrides.py:32-38` returns
  `{}` on any exception; `pin()` (`:45-52`) saves the result. Scenario: a hand
  edit leaves a trailing comma → CI (which `update.yml` triggers on
  `overrides.json` pushes) runs without any manual address, and the next
  `rcncheck --pin` rewrites the file with only the new entry. REPRODUCED
  (synthetic: two pins plus a trailing comma → file contains one entry after
  `pin()`). Acceptance: invalid JSON fails loudly in `load()` and in the offline
  test gate; `pin()` refuses to save over an unreadable file.
- [ ] **B6 (Low) — README and AGENTS.md claim more than the code does.**
  `AGENTS.md:18` gives `python3 -m site.build` as the build command (no such
  module; exit 1, reproduced) and `AGENTS.md:16` says Python 3.11 while CI uses
  3.12. `README.md:5` lists OLX as an aggregated source, but OLX has been
  blocked at zero in every recent audit (e.g. `docs/audits/2026-10-22-cohort-checkpoint.md:48`);
  `9fc89c5` removed the "coverage remains partial; OLX blocked" caveat.
  `README.md:18` serves `site/` locally, which has no `site/data/` on `main`,
  so the page shows no listings. REPRODUCED (build command) / CODE-READING
  (others). Acceptance: AGENTS/README commands run as written and the README
  states current source coverage and RCN matching limits.
- [ ] **B7 (Low) — site-only pushes deploy with no test gate.**
  `.github/workflows/deploy.yml` (push on `site/**`, `scripts/update-summary.mjs`,
  `scripts/templates/**`) runs catalog validation and rendering but no pytest or
  Node tests; the JS/browser-loading tests only run inside `update.yml`, whose
  push paths exclude `site/**` (other than `regions.json`). Scenario: a broken
  `site/app.js` edit (as `9fc89c5` touched 112 lines of it) is published to
  Pages without any check. CODE-READING ONLY. Acceptance: deploy runs at least
  the offline Python+Node suite (no portal traffic) before `upload-pages-artifact`.
- [ ] **B8 (Low) — the delist sweep probes only one URL of a multi-portal
  property.** `scraper/delist.py:118-119` takes the last observation URL.
  Scenario: a property merged from Otodom and n-online drops out of both scrapes
  (Otodom coverage is partial); the n-online ad expired but the Otodom ad is
  live → record marked delisted, appears in the archive as withdrawn and becomes
  eligible for a "sold" deed claim. It self-heals only if a later scrape sees a
  URL again. CODE-READING ONLY. Acceptance: a record is delisted only when every
  known non-archived URL is confirmed gone (or the remaining ones are unknown
  and documented as such).

### Next development tasks

- [ ] **T1 — Frozen synthetic demo dataset (still missing).** Why: the site
  cannot be shown or tested without live portals and the `data-<region>`
  branches; B6's local-serve instruction shows an empty page. Generate a small
  synthetic region (fake addresses/URLs, all lifecycle states, one RCN match per
  confidence level) through `payload.build`, validate it with
  `scripts/validate_data.py`, and serve it with one command. Effort: M (1–2 days).
  Acceptance: `README` Quick Start renders listings, archive, map and stats
  offline; the dataset passes the validator in CI.
- [ ] **T2 — Data-lifecycle diagram (still missing).** Why: the identity →
  history → delist/archive → RCN → payload → orphan branch → overlay → Pages
  chain spans ~10 modules and three workflows; B2/B3/B8 all sit at its seams.
  One diagram (Mermaid in `docs/`) with each state transition and its evidence.
  Effort: S. Acceptance: every `delisted`/`archived`/`sold` transition in code
  maps to one arrow, linked from README.
- [ ] **T3 — Reliability case study (still missing).** Why: the audits hold
  strong evidence (source-volume guard refusing a Gratka outage, RCN export
  fallback, capped retries, atomic regional storage) but it is spread over 11
  dated files and the trimmed README no longer tells it. One page with failure
  mode → guard → evidence run link. Effort: S. Acceptance: each guard cites the
  run or audit that proved it.
- [ ] **T4 — Deploy test gate and fixture freshness check.** Covers B7 and adds
  a check that each portal fixture still exercises its parser's current
  required fields. Effort: S. Acceptance: deploy fails on a broken `app.js` in a
  test branch; no network access in the gate.
- [ ] **T5 — Lifecycle property tests.** Why: B1–B3 passed 538 tests because
  tests assert single steps. Add multi-day scenario tests (source gap, archive
  after long absence, relist, multi-portal delisting) over `history`, `delist`,
  `rcn.match` and `link_same_size`. Effort: M. Acceptance: each scenario asserts
  the published card fields (`price_history`, `prev_price`, `delisted`, `sales`).
- [ ] **T6 — Restore lost provenance as Markdown.** The county-list source,
  og-card regeneration command and `[hidden]` rationale removed in `9fc89c5`
  belong in `docs/`, per the no-comments rule. Effort: XS. Acceptance: each has
  a documented home.

### Feature ideas

Deferred by `POLAND_ROLLOUT.md` (auctions, rentals/yield, new portals, agency
statistics, alerts, card sparklines) are deliberately excluded. All ideas are
static/self-service and add no portal traffic.

- [ ] **F1 — Property permalink.** Problem: a buyer cannot send one property's
  timeline and RCN comparison to a partner; filters are shareable, single cards
  are not. A `#p=<detail key>` link opens that card (current or archive).
  Effort: S. Worked if: links survive a data refresh for current cards and
  resolve to the archive card after delisting.
- [ ] **F2 — Printable negotiation sheet.** Problem: the RCN gap and price
  history are useful at a viewing, offline. A print stylesheet/"Drukuj" view for
  one card: price trail, deeds nearby, confidence, sources, dates. Effort: S.
  Worked if: one A4 page in Chromium print preview with all evidence and source
  links.
- [ ] **F3 — "Why this match" on RCN claims.** Problem: confidence labels
  (`wysoka`/`średnia`) do not say whether the match came from street+number,
  parcel, or a unique decimal area, and the matcher's limits are now absent
  from the README. Publish the match basis from `rcn._score` and show it beside
  the confidence. Effort: S–M. Worked if: every sale claim shows its basis and
  the validator rejects claims without one.
- [ ] **F4 — CSV export of the filtered view.** Problem: analysts and buyers
  copy cards by hand. Client-side CSV of visible rows (price, m², zł/m², town,
  RCN gap, first seen, URL). Effort: S. Worked if: the export matches the grid
  count and opens correctly in a spreadsheet with Polish characters.
- [ ] **F5 — Time-on-market filter.** Problem: long-listed properties signal
  negotiation room; `first_seen` is already on every card but not filterable.
  (Related to an unselected historical sort idea in `docs/HISTORY.md`.) Effort:
  XS. Worked if: a "na rynku > N dni" filter matches a manual count on the
  frozen demo dataset (T1).
- [ ] **F6 — Compare up to four properties.** Problem: buyers shortlist across
  portals. A tab-local comparison table (price, m², zł/m², RCN gap, price trail,
  days on market) kept in `localStorage`. Effort: M. Worked if: comparison
  survives reload and uses only already-published fields.

### Unverified suspicions

- `normalize.to_float` concatenates every digit and dot it finds: `"120 m2"` →
  1202, `"ok. 50"` → 0.5, `"1,5 mln"` → 1.5. Function behaviour is reproduced;
  whether Gratka/Morizon card text ever contains such strings was not checked
  (fixtures show `"273 m²"`, `"7 pokoi"`).
- `delist._GONE_MARKERS` searches the whole page body; a live portal page that
  embeds "oferta nieaktualna" in i18n bundles or related-ad widgets would be
  marked gone. Not checked against real pages.
- `scout.yml` pins `actions/checkout@v7`, `setup-python@v7`,
  `upload-artifact@v7` while the other workflows use v4/v5; manual-only, not
  verified to resolve.
- Gratka `_walk` records `kept_keys` identical to `served_keys`, so its coverage
  "kept" figure cannot show filtering losses (cosmetic unless relied on).
- Dates are UTC (`dt.date.today()` on runners); the hourly Opolskie check can
  record a Polish-calendar day early/late around midnight. Impact not measured.

### Already recorded elsewhere (still open)

- Fresh healthy two-region RCN acceptance and the seven-day / three-cycle
  stability cohort (queue above; `docs/audits/2026-10-22-cohort-checkpoint.md`).
- OLX blocked on GitHub-hosted runners; Otodom/Morizon coverage partial
  (audits 2026-10-21/22).
- Source-continuity guard does not detect gradual decline (October 21 repair
  section above).
- Storage/provider selection and expansion beyond two regions are owner-gated
  (`POLAND_ROLLOUT.md`, `docs/STORAGE.md`).
- Archive entries have no map coordinates (known gap in `docs/HISTORY.md`).
