# Production audit — 2026-09-09

Auditor: Codex. Scope: the seven review fixes at main `092d8de`, followed by
implementation of the selected serial Opolskie cadence. Data snapshots and live
browser responses were read without a new scrape, manual dispatch or data-branch
write. This is a completed audit with precision limits, not a claim that every
property identity or deed association has been independently established.

## Production evidence

The recorded P2 push [Update listings 34017930684](https://github.com/110kc3/rentgen-ofert/actions/runs/34017930684)
and [automatic deploy 34023375015](https://github.com/110kc3/rentgen-ofert/actions/runs/34023375015)
succeeded. All six subsequent scheduled updates at the same code SHA through
September 8 succeeded. The latest checked pair is
[34277683080](https://github.com/110kc3/rentgen-ofert/actions/runs/34277683080) /
[34288019746](https://github.com/110kc3/rentgen-ofert/actions/runs/34288019746).
This session checked the recorded commit once; it did not poll a running job.

| Data ref | Publication UTC | Raw offers | Current cards | RCN matched histories | Confirmed-sale archive records |
|---|---|---:|---:|---:|---:|
| `69c94fc4cd748f0ece948e7a5caa4995ec9c2fbc` | Sep 5, 21:31 | 52,010 | 28,659 | 3,820 | 73 |
| `0de73326bed5f378e45d74f3f90f4506fd281f88` (P1) | Sep 6, 03:13 | 52,010 | 29,661 | 2,520 | 15 |
| `4f877cf955be4095acdc66eb0fb257f04fdd1154` (P2) | Sep 6, 08:59 | 52,006 | 29,657 | 2,523 | 15 |
| `c688f6d8047695716cbe14e2af7ad78394f3b07f` | Sep 8, 22:51 | 52,225 | 29,945 | 2,610 | 15 |

The latest Śląskie scrape took 6,891.5 seconds / 114.9 minutes. Source counts:
Otodom 16,119; Gratka 12,631; Morizon 12,623; n-online 10,852. OLX stopped
with HTTP 403 after its bounded probe. Photo diagnostics report zero critical
or history deferrals, zero backlog and zero unresolved groups; 42,068 of
42,072 critical candidates have hashes. Its manifest is schema 2.

Opolskie remains at `ee1bf78`, September 4 09:03 UTC, with 3,556 properties.
The live catalog exposes only Śląskie and Opolskie; disabled Małopolskie remains
recoverable. Frozen copies of both published regional trees pass
`scripts.validate_data` (71 JSON files each, 118.8 and 7.3 MiB served). Śląskie
also passes the previous-source continuity check against `69c94fc` metadata.
The P2 log confirms publication only to `data-slaskie`.

## Identity changes

Comparing index plus all 64 detail shards by each card's constituent portal
URLs finds **1,005 old groups distributed across multiple P1 cards**. Of these,
**974 contain a pair rejected by the current identity compatibility rule**.
The aggregate raw count is unchanged while the card count rises by 1,002;
this is primarily a change in grouping, not evidence of additional inventory.
Portal URL turnover and group recombination prevent equating either group
count directly with the net card-count difference.

Sampled cases include:

- Gliwice/Szafirowa: Otodom `ID4uEYM` says two rooms / 37.99 m²; Gratka
  `31756961` says one room / 37 m². The room disagreement now vetoes photo identity.
- Czeladź: Otodom `ID4CLzw` and Gratka `48713921` are both 147 m² houses, but
  locality is `Czeladź` versus county label `będziński`. This illustrates
  conservative separation caused by inconsistent portal location fields.
- Gliwice: Otodom `ID4CnMc` and n-online `26855815` both describe 59.51 m²,
  three-room flats. `Zygmuntowska 3a` versus `Zygmuntowska` triggers the street
  veto: an alphanumeric building suffix is currently treated as a street token.

These samples do not establish that every newly separated card represents a
different dwelling. County parsing and street-number normalization merit a
separate, bounded repair; this audit does not select that work or weaken the
current conservative matching rule. Earlier conflated histories remain because
they do not retain enough per-offer identity evidence for safe automatic splitting.
Some stored floor values are portal enum words, another precision limit.

## Sale reconciliation

All four snapshots use the **same compressed RCN cache**, SHA-256
`fd8d3520acf8fbf981f5767c43e1407c21ee3fa43e03e7ec8a694e6494add91b`.
The 5,116 pre-review history records carrying any persisted sale claim were
replayed through the current matcher against that frozen cache. This differs
from the old metadata's 3,820 matches: that counter described a matching pass,
whereas stale attached claims could previously survive outside it.

Of the **73 delisted histories with a confirmed-sale claim**, the frozen replay
retains **15** and removes that classification from **58**, exactly matching
the production archive-count change:

| Reason | Records |
|---|---:|
| Previous deed rejected by known flat attributes | 49 |
| Multiple surviving best candidates | 3 |
| Deed retained as a past sale, rather than a confirmed current sale | 3 |
| Previous deed absent from current town/area candidate set | 2 |
| Previous deed outside the current delisting window | 1 |

Examples checked against cached deed attributes:

- Katowice/Graniczna, n-online `26755770`: listing has two rooms; the former
  July 6 / PLN 340,000 deed has three. The address no longer overrides this.
- Częstochowa/Katedralna, `26698421`: listing has two rooms; the May 29 /
  PLN 305,000 deed has one. The claim is removed.
- Chorzów/Kościuszki, `26745002`: the May 15 / PLN 565,595 deed remains as
  `past`, predating first observation on June 20.
- Rydułtowy/Krzyżkowicka, `26732561`: May 25 predates the June 20 lower bound
  for an August 19 delisting. It cannot remain a confirmed current sale.
- Retained example: Katowice/Nadgórników, `26251353`, with a June 29 /
  PLN 391,000 deed and August 17 delisting remains supported by the matcher.

This validates reconciliation against the project's declared matching policy.
It is not independent confirmation from a buyer, seller or a specific unit's
legal records. Replaying frozen older histories also differs from replaying
newly observed P1 histories, so its total retained past-sale count is not a
prediction of the complete P1 matching funnel.

## Daily prices and browser recovery

Between the P1 and first P2 publication on September 6, **21 portal URLs changed
price**. All 21 have the later value in that day's live history observation.
Examples: Otodom `ID4CVzU` rose PLN 679,000 → 689,000; Otodom `ID4CG6J` fell
PLN 259,500 → 257,000; n-online `26933189` fell PLN 259,000 → 249,000.
Every one of the 52,006 published offer URLs has a matching daily observation.

A second check on the September 8 snapshot finds matching current daily values
for **all 52,225 published offer URLs**. Its 52,450 corresponding observations
include six additional stale values in historical records; the store is not
asserted to have a globally unique record per URL. This is part of the retained
history limitation. Numeric comparisons normalize JSON decimals before testing
equality, avoiding false mismatches between decimal and binary-float parsers.

A real headless Chromium session opened the deployed Śląskie dashboard using
its actual HTML, JavaScript, index and shards. External images were suppressed.
A route injected one detail HTTP 503 and one archive network failure; subsequent
requests used the real live responses. Both Polish retry buttons recovered
without page reload. The detail record stayed incomplete until success, its
timeline then rendered, and the archive loaded 2,686 records. Exactly two
requests occurred for each failed/retried resource; no uncaught page errors.
The detail sample was Otodom `ID4Cb68`. This complements the eight fixture-based
Node loader cases; it does not simulate every browser/cache condition.

## Scheduler implementation and acceptance handoff

Opolskie cadence is `every_72h`; its hourly eligibility tick is `17 * * * *`.
Only metadata is read until 72 hours have elapsed since the last successful
data-branch publication and the latest recorded attempt. Every Opolskie attempt
first uploads a seven-day `cadence-attempt-opolskie` artifact; failed runs therefore
do not turn into hourly full-scrape retries. Failed metadata/attempt reads or
marker uploads stop before portal work. Manual dispatch bypasses the timing gate.

All checks run under the global scrape lock and re-read state after queueing.
`queue: max` preserves waiting runs when a new tick arrives. It is documented by
[GitHub's concurrency reference](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
Artifact names/timestamps use the documented
[Actions artifact API](https://docs.github.com/en/rest/actions/artifacts#list-artifacts-for-a-repository).
Actual starts can be later because of the hourly tick, the serial queue and
[GitHub schedule delays](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

No-op updates skip expensive steps. Deploy's read-only preflight checks the
triggering run's data-push step; only actual publications enter the Pages queue.
Direct site pushes/manual deploys retain their existing behavior. A catalog
change to `manual` pauses the timer; disabling the region also suppresses its
publication via existing behavior. No region expansion or matrix was added.

Local verification: **345 offline tests**; both production payload validations;
live Chromium recovery; read-only live scheduler decision; JavaScript syntax and
`git diff --check`. Actionlint 1.7.12 checks the workflows with only its outdated
`concurrency.queue` syntax diagnostic excluded (current GitHub docs support it).
The deployment predicate was also exercised against the real P2 jobs response
and the same response with the publication step marked skipped.

The impending push is not production-verified. Next session, check that commit
once, then audit the first scheduled Opolskie publication and following no-op.
Begin the seven-day cohort observation only after the first scheduled refresh
succeeds; require at least three healthy Opolskie cycles before selecting a new
region. Failed/missed cycles require investigation and restart that observation.
The canonical handoff and acceptance details are in [TODO.md](../../TODO.md).

Audit working files (local, not runtime inputs):
`/tmp/rentgen-audit-20260909/` contains fetched immutable snapshots, streamed
semantic/price replay scripts and results, browser script/screenshot and
validator inputs. Histories were streamed with the existing temporary `ijson`
installation to limit memory; no runtime dependency was added to the repo.
