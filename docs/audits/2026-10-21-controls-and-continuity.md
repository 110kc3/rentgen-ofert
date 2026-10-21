# Address controls and source-volume protection — October 21

The owner selected both findings from the earlier
[feature audit](2026-10-21-rcn-and-features.md): repair manual address lookup/copy
and investigate/protect against the severe source-count collapse. Starting
source: clean `main` at `eb7aeabd0eb635af044b0dad94112d39140f44d2`.
[TODO.md](../../TODO.md) owns the next production check. No manual workflow
dispatch, direct data-branch write or infrastructure change was performed.

## Address lookup and copy

The enclosing address details element stopped click propagation before the
delegated grid handlers could run. Removing that inline stop lets both buttons
reach their handlers. The card-opening handler already ignores controls/details,
so these actions do not open a listing tab. Delegation survives card re-renders.
The generated page bumps the app cache key to version 27.

GUGiK requests now have a 15-second abort timeout per request and require HTTP
success. WFS responses must be valid WFS 2.0 feature collections. Exception
documents, invalid XML, inconsistent returned/matched counts, continuation links
and the 500-feature cap fail with an unavailable/incomplete-data message rather
than a false no-deeds result. A validated empty response remains a distinct
outcome. Controls re-enable after failure; clipboard refusal retains the manual
copy prompt. Address lookups and copying commands do not save a pin.

The reproducible local browser check is:

```bash
PYTHONPATH=. ./.venv/bin/python tests/check_pin_browser.py
```

All **12 Chromium checks** pass with validated fictional regional data and
intercepted provider responses: real lookup/copy clicks, required inputs,
pending-button state, address-specific deed filtering and temporal GML dates,
parcel/map links, no accidental listing opening, quoted shell command arguments,
clipboard fallback, controls after re-render, HTTP/XML/OWS/partial-data failures,
validated empty results, abort handling and no uncaught JavaScript errors.
Playwright remains an optional audit dependency outside the offline CI set.

A separate real-provider check used the published Śląskie page/data with only
`app.js` replaced inside the audit browser by the candidate bytes. UUG, ULDK
and both WFS layers returned **HTTP 200** for Gliwice, Zwycięstwa 21. The parcel
and source/map links appeared, the validated address filter yielded no matching
deeds, and copy reached the clipboard API without opening a listing. No register
contents or property ownership were verified. This is candidate verification,
not a claim that the new code has already deployed.

The broader prior feature audit was also repeated with candidate `app.js` and
published data: **33/33 checks pass**, including filters/sorts, share/restore,
timelines, archive 503/retry, sale filtering, real map tiles, KW import/linking,
statistics, mobile layout and the repaired address controls. No uncaught browser
errors were observed. Portal coverage, county freshness and missing coordinates
remain data limits; these checks do not accept the two-region stability gate.

## Source collapse investigation

The actual adjacent data commits remain readable by immutable full SHA:

| Publication | Śląskie cards | Gratka current: total / flat / house | Morizon current: total / flat / house |
|---|---:|---:|---:|
| [`e5c1a9c6fcadd90ff39949f3a99672462e622521`](https://github.com/110kc3/rentgen-ofert/commit/e5c1a9c6fcadd90ff39949f3a99672462e622521), Oct 19 23:31 UTC | 30,934 | 12,368 / 9,760 / 2,608 | 12,367 / 9,759 / 2,608 |
| [`073b5bbcd2b95ca043ab6315457111f8653c35a0`](https://github.com/110kc3/rentgen-ofert/commit/073b5bbcd2b95ca043ab6315457111f8653c35a0), Oct 20 11:53 UTC | 21,458 | 37 / 33 / 4 | 37 / 33 / 4 |

The [incident run](https://github.com/110kc3/rentgen-ofert/actions/runs/39413268064)
logged only one page per type for each portal. Its metadata declared totals of
33 flats and four houses, 100% coverage and healthy status. The categorical
gate therefore accepted nonzero contributions. Both portals share a frontend/
database, so their agreement is not independent evidence of market inventory.

Historical response bodies/final redirect URLs were not retained. The precise
upstream reason for the narrowed searches cannot be established from these
artifacts. A new read-only probe returned HTTP 503 maintenance pages from both
sites; that is current availability evidence, not proof of the earlier cause.
No parser or request-volume change is justified by the available response evidence.

## Publication rule

For every previously contributing source, and independently for each property
type present in its prior metadata:

- Existing blocked/unknown/missing/zero protection remains.
- With a prior baseline of **at least 100 current offers**, losing **more than
  50%** refuses publication even when the portal claims healthy/100% coverage.
- Exact 50% retention, normal drift, growing sources and small nonzero samples
  can pass. First publications and previously unavailable sources establish no
  positive baseline. A missing previously contributing type is treated as lost.
- The existing explicit `--allow-source-regression` override allows an intentional
  reset and logs the source/type counts and quantitative reason in CLI warnings
  and the Actions summary. It does not bypass schema or RCN validation.

This deliberately conservative abrupt-loss rule targets an incident far outside
normal observed drift: the known sources lost over 99% between adjacent runs.
It avoids requiring exact stability or trusting a newly shrunken denominator.
The 100-offer minimum limits small-sample noise. Comparing each type prevents
growth in flats from masking missing houses. It compares adjacent publications;
gradual long-term deterioration still requires operational review.

Replaying the real incident against its actual predecessor rejects **six**
transitions: both source totals and both types on each source. The current
healthy October 21 publication (30,876 cards) passes against that same baseline;
the complete frozen healthy 134-file public tree also passes full validation.
The workflow already runs this gate before staging/pushing regional data, so
a rejection retains the previous publication and cannot trigger a data deploy.

**535 offline tests pass**, including incident counts despite false healthy
status, threshold/sample boundaries, type collapse hidden by stable totals,
CLI failure and logged override, plus existing workflow ordering, publication,
regional isolation and RCN guards. Candidate production CI/Pages verification is
pending this push. Opolskie's fresh-RCN and the two-region stability gates remain
separate and open. Audit-only source metadata/results are in
`/tmp/rentgen-controls-20261021/`.
