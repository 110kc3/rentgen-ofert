# RCN transport recovery and Śląskie feature audit — October 21

The owner selected Opolskie RCN download investigation/recovery and an audit of
Śląskie's shipped features. Starting source: `87330601db630fe6bc84c146ce2c946d79920427`,
clean `main`. No manual workflow dispatch, direct data-branch write, new region
or infrastructure was selected. The implementation push needs its own CI check;
[TODO.md](../../TODO.md) owns the handoff.

## Previous push and frozen production evidence

Commit `8733060` passed [scrape 39318260716](https://github.com/110kc3/rentgen-ofert/actions/runs/39318260716)
(518 tests, strict generated-data/source/RCN validation and regional staging)
and [Pages 39318260903](https://github.com/110kc3/rentgen-ofert/actions/runs/39318260903).
All three deployed readers match their source bytes. This resolves that push's
previously pending CI check.

| Evidence read October 21 | Śląskie | Opolskie |
|---|---|---|
| Data ref | `431cdaab30c53b00ad314673b1f333a1b0ae6bdd` | `cb36e709d52057eee2a4fd47c1e9bba586fde403` |
| Publication UTC | Oct 20 22:41:38 | Oct 20 01:36:15 |
| Schema / current / archive cards | 3 / 30,914 / 4,092 | 3 / 3,656 / 605 |
| Public JSON files / bytes | 134 / 116,101,794 | 134 / 8,586,501 |
| RCN health / retrieval date | healthy / Oct 16 | degraded / Sep 28 |
| Matched histories / archive sale claims | 3,894 / 111 | 212 / 7 |
| Runtime | 75.9 min | 75.0 min |
| Critical photo deferrals / backlog | 0 / 0 | 0 / 0 |
| Archive maintenance | cached complete, Oct 15 / 49,854 | new cycle partial, 52 checkpoints pending, HTTP 429 |

Every served JSON file was downloaded; a second manifest read confirmed a stable
publication. Both trees pass `validate_data_dir(..., require_history=False)`,
including payload hashes, both detail namespaces, counts and source/RCN metadata.
Only the deliberately unserved pipeline history is omitted. A valid payload can
still describe degraded RCN or partial portal coverage.

## Opolskie failure and transport change

[Automatic run 39347076178](https://github.com/110kc3/rentgen-ofert/actions/runs/39347076178)
reached RCN at 00:36:47 UTC on October 20. WFS connection retries failed at
00:49:53; the official export host also timed out at 01:02:57. Both errors were
connection timeouts before parsing. The shared portal adapter allowed six
120-second connection attempts per request, costing about 26 minutes in RCN.
The unchanged cache was retained correctly. The upstream outage's cause is
unestablished; a local successful download does not establish GitHub-runner access.

The RCN phase now owns a separate session with one adapter retry, a 10-second
connect timeout and the existing 120-second read timeout. WFS rejects incomplete
traversals as before. Export downloads have at most three whole-file attempts
for connection/read/chunk interruptions or a short Content-Length. Each attempt
restarts the file, size and SHA-256 from zero, with two/four-second backoff.
The adapter may make two connection attempts inside each whole-file attempt;
an unreachable WFS request plus first export therefore has eight 10-second
connection attempts and six seconds of outer backoff, rather than twelve
120-second attempts. DNS, Retry-After and active reads can add time; this is
not a total wall-clock deadline. HTTP status retries retain capped Retry-After.
Permanent HTTP errors and invalid sizes/Parquet/schema/region/counts do not enter
the whole-file retry loop. Both layers must validate before atomic cache save.
Persistent outages still retain the old date and report degraded health.

A forced local refresh of a copy of the actual Opolskie cache completed in
**19.78 seconds**, replacing 13,426 / 34,356 deeds with **63,494 flat /
86,224 residential-building deeds**. WFS still rejects its inconsistent
89,176-hit / 351-member traversal; both official exports validate. Their source
row counts are 89,176 / 273,649 and their hashes match the October 17 audit:

- Flats: `f1efbf4cfcd74a2baf438d018ee27de063e3405d26aeaaf4766a2739d2bb5a66`.
- Buildings: `7540e9837bcbaabadb442f88290454cc432936b39c4aeccfd05428463b0b3b68`.

The local snapshot is dated October 21 and reloads identically after save. It
was not uploaded. Broader evidence is not a claim of sales growth or current
county reporting. The full offline suite passes **524 tests**; new regressions
cover connect/read/chunk failures, clean byte/hash restart, bounded second-layer
failure retaining the prior cache/date, and permanent HTTP failure.

## Śląskie feature results

Real Chromium 156 checked the deployed site: **32 of 33 checks pass**. Checks
use actual UI events and live datasets; the archive failure is injected only
in the audit browser, and KW records are explicitly fictional fixtures.

| Feature group | Result |
|---|---|
| Type, source, private/agency, primary/secondary, relisted, price-drop and RCN filters | Pass |
| Searchable towns, combined price/area/rooms, Gliwice distance and text search | Pass |
| Seven sorts, share URL/filter restore and empty-state recovery | Pass |
| Current timelines, multiple source offers, negotiation and freshness evidence | Pass |
| Separate archive load, injected detail 503/retry and 111 confirmed-sale filter | Pass |
| Map CDN, actual tiles, filtered markers, popup and RCN legend | Pass |
| KW import, explicit confirmation/link, filter, unlink, reload clearing; standalone viewer | Pass |
| Four statistics charts, town/type/range controls and accessible data tables | Pass |
| National picker, 390px mobile layout and no uncaught JavaScript errors | Pass |
| Manual address RCN lookup / copy-command controls | **Fail: delegated clicks blocked** |

`pinBlock()` puts `onclick="event.stopPropagation()"` on its enclosing details.
`wirePinButtons()` listens on the ancestor grid, so the check and copy clicks
cannot reach it. A real check click fires on the button, leaves results hidden
and issues no GUGiK lookup. Calling the existing lookup function directly in
the audit browser bypasses that UI defect, resolves UUG/ULDK, then displays a
connection error during WFS requests. End-to-end manual lookup is therefore
unaccepted even apart from the click defect. No address pin was saved.

Data limits also prevent declaring every feature complete for every offer:

- OLX remains blocked; Otodom is partial (70.7% served). Aggregate coverage is
  partial. Gratka is 99.9%, Morizon 100%; these are portal-reported denominators.
- A preceding [October 20 Śląskie run](https://github.com/110kc3/rentgen-ofert/actions/runs/39413268064)
  published **37 Gratka + 37 Morizon rows** and only **21,458 cards**, yet marked
  those sources healthy and passed categorical continuity. The later publication
  recovered to 12,339 / 12,345 rows and 30,914 cards. The gate detects complete
  categorical loss; it does not protect against this severe nonzero collapse.
- 20,337 of 30,914 cards (**65.8%**) have coordinates; map/distance exclude offers
  without usable coordinates. There are 13,126 current deed benchmarks.
- Fresh retrieval cannot repair stale county reporting. Gliwice's newest deed
  in the current evidence is February 25, a 237-day lag at publication.
- Listing images were blocked during browser checks to avoid bulk portal image
  requests. Stored gallery links/detail structure validate; universal external
  image or outbound listing availability is not asserted. KW checks do not verify
  real register contents or the external EKW service.

## Next acceptance and unselected findings

Opolskie's next automatic eligibility is **October 23 01:36:15 UTC**, plus the
hourly tick, lock and scheduler delay. Confirm healthy RCN on both live regions,
reconcile derived evidence and inspect archive resumption before starting the
seven-healthy-day / three-automatic-cycle observation. This push normally runs
Śląskie; it cannot establish Opolskie production recovery from a local refresh.

Suggested subsequent work, not added to the accepted implementation queue:

1. Repair the manual address check/copy event path and verify real GUGiK success
   or accurate failure reporting in the browser.
2. Investigate the 37-row source collapse and add evidence-based quantitative
   continuity protection without treating ordinary market movement as an outage.

Audit-only scripts, downloaded datasets and JSON results are under
`/tmp/rentgen-audit-20261021/`; they are not production runtime dependencies.
