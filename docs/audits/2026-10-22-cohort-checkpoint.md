# Two-region acceptance checkpoint — October 22

The owner selected items 1–2 (fresh two-region RCN acceptance and stability
observation) and item 3 (expansion/storage **planning only**), with push after
the work. This checkpoint records the checks possible on October 22; it does
not accept future publications or elapsed observation time. Source checkout:
`1e4db7d1c8e08655d392352199638479f2f73ec1`, clean `main`, matching remote main.
No workflow dispatch, provider requests, production configuration or data-branch
writes were performed. [TODO.md](../../TODO.md) remains the owning queue.

## Current production evidence

The latest real [scheduled scrape 39770778678](https://github.com/110kc3/rentgen-ofert/actions/runs/39770778678)
ran on `1e4db7d`, passed **535 offline tests**, strict generated-data/source/RCN
validation and scoped staging/push. `ALLOW_SOURCE_REGRESSION` was false.
[Deployment 39783221230](https://github.com/110kc3/rentgen-ofert/actions/runs/39783221230)
passed both publication and deploy jobs. The earlier
[hourly check 39761221329](https://github.com/110kc3/rentgen-ofert/actions/runs/39761221329)
skipped tests, scraping and data push: it is not an additional healthy cycle.

| Evidence | Śląskie | Opolskie |
|---|---|---|
| Data ref | `e351e4e5ec02830b3b2f0b7a78977f1771829f70` | `cb36e709d52057eee2a4fd47c1e9bba586fde403` |
| Published, UTC | Oct 22 13:00:42 | Oct 20 01:36:15 |
| Current / archive / archive sale claims | 30,970 / 4,137 / 110 | 3,656 / 605 / 7 |
| RCN matched histories / benchmark towns / gap pairs | 3,906 / 63 / 95 | 212 / 50 / 7 |
| RCN retrieval and health | Oct 16, healthy cache | Sep 28, degraded after export connect timeout |
| Usable flat / building deeds | 315,432 / 576,596 | 13,426 / 34,356 |
| Runtime | 5,479.8 s / 91.3 min | 4,502.8 s / 75.0 min |
| Critical photo deferrals / backlog | 0 / 0 | 0 / 0 |
| Unresolved size groups / listings | 0 / 0 | 1 / 2; unchanged metadata |
| Retained complete archive checkpoint | Oct 15 / 49,854 records | Oct 13 / 7,822 records |
| Unfinished new archive cycle | Oct 22, HTTP 429, 100 partitions pending | Oct 20, HTTP 429, 52 partitions pending |
| Public JSON files / bytes | 134 / 116,550,340 | 134 / 8,586,501 |

Both complete Pages trees pass `validate_data_dir(..., require_history=False)`;
only the private history-file requirement is omitted for these public copies.
The manifest was fetched before and after each download to confirm a stable
publication. Source/RCN continuity against the prior Śląskie metadata (`b0ce686`)
passes four source/type transitions with no regressions or override. Opolskie's
ref is unchanged, confirming no sibling data-branch replacement in this cycle.
This is evidence for this publication, not every future regional-isolation case.
Both immutable data-branch RCN cache files also pass `validate_snapshot`; their
retrieval dates and both layer counts match public health metadata. Opolskie's
last-good cache is valid but stale/degraded; validation is not fresh acceptance.

Śląskie current source counts are Gratka 12,353, Morizon 12,355, n-online 10,839
and Otodom 16,198; OLX remains blocked at zero. Morizon reports partial because
of `partition_total_shortfall` (12,355 served versus 12,357 stated). Its displayed
100.0% is rounded and does not imply complete coverage. Otodom remains partial.

The persisted archive JSONs both retain `complete: true` for the previous full
checkpoint while `cycle.pending` contains 100 / 52 resumable partitions. Public
metadata correctly reports the current harvest as partial. Do not use the old
checkpoint flag alone to accept fresh weekly maintenance.

## Changes reconciled against the previous publication

Śląskie moves from 31,000 to 30,970 current cards, 4,091 to 4,137 archive faces,
3,902 to 3,906 matched histories, and 64 to 63 benchmark towns; archive sale
claims remain 110 and gap pairs remain 95. RCN retrieval date, counts, source
hashes and full health/provenance are unchanged. The four additional matches
therefore do not demonstrate a larger RCN download or sales growth.
The missing benchmark town is Kalety. Replaying `_bucket_stats` against the same
validated cache with the old/new 24-month cutoffs (`2024-10-21` / `2024-10-22`)
reproduces its disappearance: the eligible flat bucket falls below the five-deed
minimum. This is a rolling-window effect, not a missing regional export.

Archive index comparison finds 51 added faces and five removed URL/date keys;
none adds/removes a sale claim. All five removed URLs remain in the immutable
new history file, under changed snapshot URLs that occur among the 51 added
archive faces with the same delisting dates. These five are archive snapshot
replacements, leaving 46 other added faces. Their retained histories are not
active listings; no identity rewrite was performed or accepted by this audit.

| Old n-online offer ID | New archived snapshot ID | Retained delisting date |
|---|---|---|
| 26183366 | 26532651 | 2026-07-11 |
| 25771112 | 26158266 | 2026-07-14 |
| 24297859 | 24300225 | 2026-08-21 |
| 24009598 | 26459674 | 2026-08-19 |
| 24553139 | 26470431 | 2026-09-03 |

Nine focused checks pass in Chromium 156.0.8078.4 against the live Śląskie site:
current count, lazy archive startup, visible source counts/blocked OLX, full
archive count, sale filtering, archived sale timeline expansion, current detail
expansion after archive browsing, four statistics charts and no uncaught errors.
This verifies the changed dataset's readers; the earlier 33-check feature audit
remains the evidence for the broader shipped UI, including manual address lookup.

## Fresh RCN and stability acceptance remain open

RCN cache policy uses `0 <= age < 7` days. Śląskie's October 16 cache becomes
refresh-eligible October 23; its next twice-daily publication must verify that
fresh transport path. Opolskie's next automatic publication is eligible
**October 23 01:36:15 UTC**, subject to the hourly tick, global serial lock and
GitHub scheduling delays. These times are eligibility boundaries, not promised
completion times. No currently running job was observed at this checkpoint.

For each next real publication, retain its source commit, automatic run/deploy
IDs, immutable data ref and previous metadata, then:

1. Verify both RCN layers' new retrieval date, source hashes/counts/provenance,
   healthy status and strict validation without source override. If either layer
   fails, confirm the previous cache/ref remains usable and leave acceptance open.
2. Validate the complete served tree and reconcile changed matches, benchmark
   towns/buckets and archive sale claims against the actual export/cache evidence.
   A larger source inventory alone is not an increase in completed sales.
3. Check source/type continuity, no critical photo deferrals/backlog and that the
   known unresolved Opolskie pair remains separate. Inspect persisted archive
   cycle completion, not only the retained old checkpoint's flag.
4. Record ordinary and fresh-RCN/maintenance durations (≤180 minutes, preferred
   ≤150), successful deployment, regional isolation and lazy-detail/statistics
   browser behavior. Distinguish hourly no-ops from actual publications.

Start the repaired cohort observation only after a healthy accepted two-region
baseline exists. Let its timestamp be `B`; require both elapsed time ≥7 days
from `B` and three successful automatic Opolskie publications under the repaired
baseline. Record dates/refs/runs and gate results in the next dated audit linked
from TODO; do not create another queue. Degraded RCN, unfinished maintenance or
other gate failures cannot be accepted as healthy cycles. Investigate failures
or missed cycles and restart after recovery as required by the queue.

**Current ledger: baseline absent; accepted repaired-cohort cycles 0; seven-day
observation not started.** October 22's successful ordinary publication does not
complete either remaining checkbox. Future eligibility or a green no-op is not
a verified wait on a live process.

## Planning deliverable and push handoff

Item 3's [production storage/expansion plan](../STORAGE.md#production-storage-and-expansion-plan--october-22)
is documented, including retained-version capacity scenarios, remote upload and
rollback gates, service/retention selection, old-tab policy and the ordered pilot
decision. No implementation or infrastructure has been enabled.

This audit and the queue/rollout/storage documentation are the scoped push.
Documentation paths match neither push workflow; no new run is expected solely
from this commit. Push verification is pending before publication; the final
response records the commit and branch Actions link. At the next session inspect
new automatic publications rather than re-polling the terminal runs above.
