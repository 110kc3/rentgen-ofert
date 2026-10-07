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
No data file is hosted with this public site. The first deployment of this page
is pending the ordinary Pages workflow after the implementation push.

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
a cleared or superseded file. The page's CSP disables connection requests and
external assets. Explicitly opening a source/EKW link is a normal external visit.
All imported text is rendered through textContent; source links require HTTPS
without credentials. Unknown fields, owner fields and claimed verification flags
are rejected. Code and fictional contract fixtures are the only public assets.

The viewer presents source claims, not verified current-register matches or legal
title. Missing rows do not prove no KW exists. Land/parent KWs do not identify a
flat automatically. No listing card is joined to these observations, and cadastral
RCN suffixes are never converted into postal unit numbers.

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
