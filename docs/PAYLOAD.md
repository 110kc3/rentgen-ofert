# Regional payload formats and storage measurements

Schema 3 is live on Śląskie and production-verified October 19, including full
hash/count checks and archive-detail retry. Opolskie still serves schema 2 until
its next automatic publication. Each region migrates independently.
The browser and validator continue reading legacy manifest schemas 1/2.

## Schema 3

`manifest.json` contains `schema: 3`, the content version `v`, current `count`,
current detail `shards`, and `archive: {count, shards}`. It is written last.
`index.json` and `archive.json` are column tables:

```json
{"schema":1,"fields":["url","price","is_private"],"rows":[["https://example.invalid/a",0,false],["https://example.invalid/b"]]}
```

Fields appear once, ordered by frequency with stable alphabetical tie-breaking.
A null cell or omitted trailing cell means an absent field; zero and false are
preserved. Duplicate/unsafe fields, unsupported tables and overlong rows fail
decoding. `site/payload.js` restores ordinary objects for the existing filters,
sorters, cards, map and explicit KW associations.

Current faces keep the same slim fields and summary counts. Opening details
fetches `d/NN.json`, keyed by exact listing URL, with FNV-1a(key) modulo the
manifest's shard count. The archive face index contains delisting/sold banners
and timeline/photo counts; opening its details fetches `a/NN.json`, keyed by
`detail_key`. The key hashes the complete archived record, with an occurrence
suffix for identical records. Histories sharing a URL remain separate. No old
history is merged, split or remapped by this wire-format change.

Archive entry does not download `a/` files. Detail requests are shared per shard,
with separate current/archive caches. Failed requests or missing records leave
the card incomplete and retryable. Legacy full archive arrays stay immediately
usable without a lazy detail fetch.

The schema-3 version covers, in order: current index, archive index, numeric
current shards, numeric archive shards. Length-prefixed SHA-256 input prevents
part-boundary ambiguity. Missing/extra shards, duplicate/missing detail keys,
wrong shard placement, archive summary/count disagreement or any stale content
hash fail validation before publication. Deployment also requires both shard
sets before generating its artifact. The normal per-region branch allowlist and
Pages artifact publication remain in use.

Query versions are cache busters, not immutable object paths. A tab spanning a
later publication may need a refresh if an old detail key has disappeared;
missing records fail rather than displaying a different archive timeline.
The optional [local versioned-storage prototype](STORAGE.md) pins complete
regional versions across pointer switches/rollback. Production still uses the
existing query-version paths; remote storage migration remains a separate gate.

## Measured October 17 slice

Frozen Śląskie ref: `09aa75c472428a8a9378a34b1f8d686284118b08`;
31,063 current cards and 4,103 archive cards. Every current face compares equal
after decoding; every archive record reconstructs its original fields, timeline
and photos, including the two histories sharing one portal URL.

| Component | Legacy | Schema 3 |
|---|---:|---:|
| Current index, raw bytes | 24,296,936 | 18,611,036 |
| Current index, gzip bytes | 3,928,186 | 3,643,234 |
| Archive faces, raw bytes | 17,851,592 including details | 1,299,522 |
| Archive faces, gzip bytes | 1,205,725 including details | 222,374 |
| Entire payload including all detail shards | 124,693,964 | 116,166,048 |
| Largest archive detail shard, raw bytes | n/a | 289,552 |

Raw current-index bytes fall 23.4%, gzip 7.3%. Archive entry drops 92.7% raw /
81.6% gzip bytes by deferring timelines/photos. Total payload bytes fall 6.84%;
lazy loading does not remove the need to store the details.

Chromium 153 on this Pi measured a median **194.6 ms** legacy JSON parse versus
**221.2 ms** compact parse plus decoding (six warm samples). With gzip, emulated
8 Mbps throughput and 80 ms latency, three cold samples had medians **4,188.6 ms**
and **4,080.1 ms**. The compact format trades about 27 ms of warm CPU time for
fewer transferred bytes; it is not a universal speedup. This is a controlled
local browser measurement with precompressed responses, not a production network
or low-end-phone guarantee.

Reproduce the offline byte/Node CPU comparison from frozen source and rebuilt
directories, without scraping portals:

```bash
node scripts/benchmark_payload.mjs LEGACY_DIR COMPACT_DIR
```

That command reports its actual Node version, gzip sizes, decoded counts and
median parse/decode time; Node results are not substituted for browser timings.
The browser harness/results and source/rebuilt files remain under
`/tmp/rentgen-storage-20261017/` and are not committed product data.

## Verification

492 offline tests pass, including roundtrip fields, unsafe tables, separate
equal-URL histories, archive hash invalidation, missing shard/record rejection,
deployment completeness and retries. Eleven real Chromium checks cover 31,063
current faces, 4,103 archive faces without detail requests on entry, an injected
archive-detail HTTP 503 and successful retry, cache reuse, the 112-sale filter,
current details after archive browsing, mobile overflow, an older regional
index/full archive, and absence of uncaught browser errors.

The frozen dataset rebuilt to schema 3 passes the generated-data/source/RCN
validator: 135 JSON/JSON.GZ files, healthy RCN and unchanged card/sale counts.
On this Pi, the 50.96-MB compressed source history's syntax was checked by an
audit-only streaming `ijson.parse` replacement for the validator's eager gzip
JSON read. Every history token was scanned; all other validator checks ran
unchanged. `ijson` and Playwright are audit-only tools, not new runtime
requirements. No listing-history or production data branch was written.

## Capacity and remaining gates

The frozen regional served tree is 124,813,358 bytes. Substituting this measured
payload gives 116,285,442 bytes. Sixteen equally sized regions would require
1,860,567,072 bytes: an explicit sensitivity calculation, not an inventory
forecast. [GitHub documents a 1 GB published-site limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits),
checked October 17. This does not meet the rollout plan's 70% hosting-limit gate.

P4 index compaction and lazy archive details are production-accepted. The
[October 19 local prototype](STORAGE.md) demonstrates immutable versions,
CORS/cache policy, partial-upload protection, rollback and mixed backends.
Nationwide capacity and remote service/deployment acceptance remain open. No
storage service or additional region was deployed. [TODO.md](../TODO.md) owns
the prototype push verification and healthy-cohort handoff;
[POLAND_ROLLOUT.md](../POLAND_ROLLOUT.md) owns the full rollout gates.
