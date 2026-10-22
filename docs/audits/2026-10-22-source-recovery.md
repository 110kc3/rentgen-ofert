# Scheduled Śląskie source recovery — October 22

The next accepted task was to confirm an automatic healthy Śląskie publication
after the Gratka HTTP 503 outage, with source continuity active and no override.
Codex inspected clean `main`, ran `git pull --ff-only origin main` (already at
`385ea9a568225a0c42a898dc332efb6246d3394c`) and checked the completed scheduled
runs. No implementation change, manual dispatch or direct data-branch write
was required. [TODO.md](../../TODO.md) owns subsequent acceptance.

## Automatic publication verified

[Scheduled scrape 39678803197](https://github.com/110kc3/rentgen-ofert/actions/runs/39678803197)
ran on `385ea9a`, starting October 21 21:26 UTC. It selected Śląskie through the
twice-daily scheduler, passed **535 offline tests**, strict generated-data/
source/RCN validation and scoped regional staging. The log explicitly records
`ALLOW_SOURCE_REGRESSION: false`. The resulting
[deployment 39689522871](https://github.com/110kc3/rentgen-ofert/actions/runs/39689522871)
succeeded on its first attempt. This is a real refresh, unlike the later
[October 22 hourly check](https://github.com/110kc3/rentgen-ofert/actions/runs/39724315005),
which skipped tests, scraping and publication; its dependent deploy job was
also skipped. Green no-ops are not additional healthy cycles.

The new isolated data ref is `b0ce686126eaaa394ed52fea62b43e6d314b0b19`, replacing
`8145ae2e1119c127f27acd5b56c28f713ff2411b`. Live publication timestamp:
**October 21 22:51:19 UTC**.

| Source | Prior published current | Recovered current | Coverage status |
|---|---:|---:|---|
| Gratka | 12,352 | 12,341 | healthy |
| Morizon | 12,335 | 12,341 | healthy |
| n-online | 10,786 | 10,854 | healthy |
| Otodom | 16,164 | 16,234 | partial (70.9% served) |
| OLX | 0 | 0 | blocked |

Both source totals and property-type continuity pass against the actual previous
published metadata without an override. Overall portal coverage remains partial.
The new dataset contains **31,000 current cards**, **4,091 archive faces** and
**110 archive sale claims**, with 3,902 matched histories and 64 benchmark towns.
RCN retains the same healthy October 16 export evidence and both source hashes:
315,432 flat / 576,596 building deeds. This run used the cache; it does not
verify a new RCN download or current reporting in every county.

Runtime is **5,046.1 seconds / 84.1 minutes**, within the 180-minute ceiling and
150-minute preference. Critical photo deferrals/backlog and unresolved size
groups are zero. The persisted archive checkpoint remains complete at October
15 / 49,854 records; a fresh weekly archive-maintenance cycle is a separate check.

## Complete live payload and reader checks

All **134 public JSON files / 116,512,142 bytes** were downloaded from Pages;
another manifest read confirmed a stable publication. The complete existing
validator passes with only the requirement for the deliberately unserved
pipeline history omitted. Source/type continuity and RCN validation also pass
against the frozen prior publication. Schema, both detail namespaces, payload
hashes and record/count summaries remain consistent.

**Nine real Chromium checks pass** against the deployed recovered publication:
31,000 current faces match metadata, archive requests remain lazy at boot,
recovered source counts/blocked OLX are visible, 4,091 archive faces load,
110 sale claims filter correctly, sale timelines expand, current details still
expand after archive browsing, all four statistics charts render, and no
uncaught browser errors occur. Images were blocked during this focused audit;
external image availability is not asserted. No UI source change required a
repeat of unrelated KW/map contracts already accepted in the prior audit.

## Archive and sale-count reconciliation

Compared with the prior publication, exactly two archive identities disappeared
and none were added. One carried a sale claim, explaining **4,093 → 4,091**
archive cards and **111 → 110** sale claims. Gap pairs also move **96 → 95**;
their existing calculation likewise excludes active histories.
A streaming read of the new commit's complete `history.json.gz` finds both
preserved records with active October 21 observations and cleared `delisted`:

- A house first seen June 17 reappeared at the same Otodom URL.
- A flat first seen September 7 retained its older n-online archive observation
  and gained active October 21 observations on a new Otodom URL and a new
  n-online URL. This was the record carrying the former archive sale claim.

The archive excludes active histories under its existing lifecycle rule.
This reconciles a changing archive cohort, not a change in underlying transaction
volume. Streaming used ijson's default number mode to preserve large photo-hash
integers. No historical identity rewrite or sale-matching change was performed.

## Acceptance and next handoff

The accepted **Śląskie post-outage source-recovery task is complete**. The previous
refusal correctly retained the good dataset; a subsequent scheduled run recovered
and published with the same guards active.

Opolskie remains at `cb36e709d52057eee2a4fd47c1e9bba586fde403`, last published
October 20 01:36:15 UTC with degraded September 28 RCN and 52 archive checkpoints
pending. Its next automatic eligibility remains **October 23 01:36:15 UTC**,
subject to tick, serialization and scheduling delays. The fresh two-region RCN
checkbox and seven-healthy-day/three-cycle observation remain open; the clock
has not started. No further region or hosting migration was selected.

Audit-only metadata, downloads, reconciliation and browser results are under
`/tmp/rentgen-recovery-20261022/`. This documentation-only handoff matches neither
configured push workflow. Verify the next eligible automatic Opolskie publication;
do not expect a new scrape from the documentation push.
