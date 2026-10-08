# Private-file KW viewer

Implemented 2026-10-07. Open [Twoja lista KW](https://110kc3.github.io/rentgen-ofert/kw.html)
from the national page or any regional listing header, then choose `records.json`
from the separate sprawdz-kw export. Its CLI command is:

```bash
python3 -m sprawdz_kw index export --db PATH_TO_PRIVATE_DB --output NEW_PRIVATE_DIRECTORY
```

Run that command in the sprawdz-kw checkout. The new directory contains the
importable JSON, a standalone filterable HTML list and a Markdown table.
The user can also read that Markdown table in their private repository. GitHub
shows HTML source; download/open `index.html` locally to use the standalone list.
No data file is hosted with this public site. The original implementation’s
follow-up Actions statuses and the current filter deployment handoff are
recorded in [TODO.md](../TODO.md).

## Filter offers with a KW

Added 2026-10-08 to every regional listing page:

1. Click **Wczytaj KW** and select your `records.json` export. You can use the
   same file as the standalone viewer; each page has its own in-memory import.
2. On the relevant listing card, click **Powiąż KW**. Select the sourced address
   and register. Check the original notice and the actual property's full
   address, including the postal flat number for a flat; confirm the checkbox
   and save the link.
3. Click **Tylko z KW**. The list now contains only linked cards that also pass
   your other filters. Cards show the number, original sources and a manual,
   unverified association label. Houses display **KW gruntu domu** distinctly.

The normal card counts and map use the filtered listing view. The KW chip and
**Wyczyść wszystko** turn off the filter while retaining tab-local links.
**Usuń powiązanie** removes one link immediately; **Usuń dane i powiązania KW**,
a replacement import or refresh clears all links. A replacement import switches
the filter off so the cards are available for review. The KW filter and imported
evidence are not included in localStorage or shared filter URLs.

The currently published slim payload has no reliable full building/postal-flat
address, so importing an address list cannot safely identify the matching offer.
There are no automatic street/area/photo/RCN associations. The button starts
with no linked offers; it does not claim other properties lack a KW. A link is
keyed to the exact card URL, never neighboring cards or inferred relistings.

A flat requires a unit register. A house can link a land record after the user
confirms it covers the house. Known city/type conflicts are refused. When source
records give competing KWs for one address/scope, none is selectable; resolve
the source conflict first. Multiple observations of the same address/KW retain
all source links. A manually confirmed association is still not independent
current-register verification.

## What it does

- Reads a schema-version-1 evidence manifest of at most 4 MiB / 1000 observations.
- Searches street, city or printed KW; preserves exact building/flat suffixes and
  leading zeros in the separate address filters. The Gliwice pilot is explicit.
- Distinguishes unit records, land records and separately sourced parent KWs.
- Shows publication and retrieval dates, a source link, evidence locator and
  original response hash. A hash identifies bytes; it does not authenticate them.
- Displays all observations and flags multiple KWs for the same exact address
  and register scope. It does not choose the newest claim as a winner.
- Copies a KW only after a button click, for manual use in the official EKW viewer.
  Availability of that external viewer is not guaranteed or tested by this page.

## Data boundary

Import uses the browser's File API, with no fetch, telemetry, browser storage or
upload. Records live only in the current tab's JavaScript memory. Refresh or
Clear removes them; a newer import replaces them. Pending reads cannot restore
a cleared or superseded file. The standalone viewer’s CSP disables connection
requests and external assets. The listing app continues its normal public data/image/map
requests; its KW import and linking logic adds no requests. Explicitly opening
a source/EKW link is a normal external visit. Imported text uses textContent
or HTML escaping; source links require HTTPS
without credentials. Unknown fields, owner fields and claimed verification flags
are rejected. Code and fictional contract fixtures are the only public assets.

The viewer presents source claims, not verified current-register matches or legal
title. Missing rows do not prove no KW exists. Land/parent KWs do not identify a
flat automatically. Listing cards can only be joined through the explicit
manual flow above; cadastral RCN suffixes are never converted into postal unit numbers.

## Verification

`./.venv/bin/python -m pytest -q` passed **452 tests**. The Node contract suite
covers schema/source rejection, flat/parent separation, exact filters, conflicting
sources and outstanding file reads after Clear or a newer import. Site-generation
checks preserve the viewer navigation on the national and regional pages.

A separate local Chromium check passed 20 assertions using a privately held
15-observation export. It covered actual file input, four unit versus eleven land
records, exact-address filtering, wrong-unit/absent-address states, source fields,
clipboard copying, malicious text/links, oversize rejection, no requests during
import/filter/copy/clear, empty browser storage, refresh/clear, desktop/mobile
rendering without overflow, and the companion local HTML list. Real records,
raw pages and screenshots remain outside this public repository.

Remote CI/deployment is pending after push; check the matching commit once next
session. The authoritative remaining queue is [TODO.md](../TODO.md).

### Listing-filter verification — 2026-10-08

The full suite passed **453 tests**. The new offline Node suite exercises explicit
confirmation, exact URL identity, house/flat/city incompatibility, conflicting
numbers, source retention, clear/replacement, and the app's actual `passes`,
chip, relaxed-count and reset functions. A focused follow-up exercised the actual
asynchronous listing importer after Clear or a newer import. Existing loading/
retry checks and generated navigation still pass.

Twenty-nine real Chromium assertions covered the normal four-offer view, empty
filter guidance, explicit flat and house linking, filter composition with price,
type and archive, immediate unlink/reset/clear behavior, city contradictions,
absence of imported KW data in requests/storage/share URLs, no guessed links
from the 15-record private export, reload, mobile overflow/dialog layout and
standalone-viewer regression. Real records and screenshots remain local.

The browser check exposed an existing nowrap history-filter group on a 390 px
screen. Mobile groups now wrap; the toolbar scrolls normally so it cannot cover
the cards. Desktop sticky controls are preserved. Remote deployment after this
filter push is pending; the canonical handoff remains in TODO.md.
