"""Split the dashboard payload: slim grid index + lazy per-listing detail shards.

`listings.json` grew to ~40 MB, fetched with caching disabled on every visit —
59% of it (timeline, photo_urls, offers, cheapest) is only visible after a
card is expanded. Instead the pipeline now writes, per region:

    manifest.json   {"v": <content-hash>, "shards": N, "count": …}  (~100 B,
                    fetched fresh each visit; everything else is fetched with
                    ?v=<hash> so browsers cache it until the data changes)
    index.json      one slim record per listing — every field the grid needs
                    to filter, sort and paint card faces (~1/3 the size)
    d/NN.json       N shards of detail records keyed by listing URL — offers,
                    timeline, archived photo links… fetched only when a card's
                    expandable section is opened

A listing's shard is FNV-1a(url) % N, computed identically in site/app.js —
keep the two implementations in sync. (URLs are ASCII; a non-ASCII URL would
mis-shard in JS and merely fail to load details, never corrupt anything.)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

SHARDS = 64

# everything the grid filters/sorts on or paints on a card face / map popup
INDEX_FIELDS = (
    "title", "type", "area", "rooms", "plot_area", "locality", "district",
    "image", "is_private", "price", "price_max", "price_per_m2", "created",
    "url", "source", "sources", "ll", "llp", "first_seen", "relisted",
    "prev_price", "development", "price_history",
)
# visible only after expanding a card (or unused by the dashboard entirely)
DETAIL_FIELDS = ("offers", "cheapest", "timeline", "photo_urls",
                 "also_listed", "sales", "street", "floor", "agency", "market")

# sales/also_listed keep a compact face summary in the index (banners + the
# "także wystawione" trail); the full objects live in the shard
_SALE_KEYS = ("kind", "date", "price", "price_m2", "confidence")


def shard_of(url: str, n: int = SHARDS) -> int:
    h = 0x811C9DC5
    for b in url.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h % n


def _slim(l: dict) -> dict:
    out = {k: l[k] for k in INDEX_FIELDS if l.get(k) not in (None, "", [])}
    if l.get("sales"):
        out["sales"] = [{k: s[k] for k in _SALE_KEYS if s.get(k) is not None}
                        for s in l["sales"]]
    if l.get("also_listed"):
        out["also_listed"] = [{"price": o.get("price")} for o in l["also_listed"]]
    # counts let the face render the expandable sections' summaries
    if len(l.get("offers") or []) >= 2:
        out["offers_n"] = len(l["offers"])
    if l.get("timeline"):
        out["tl_n"] = len(l["timeline"])
    if l.get("photo_urls"):
        out["ph_n"] = len(l["photo_urls"])
    return out


def _write(path: pathlib.Path, text: str):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build(listings, data_dir, shards: int = SHARDS, log=print) -> str:
    """Write manifest.json + index.json + d/NN.json under ``data_dir``.

    Returns the content-version hash."""
    data_dir = pathlib.Path(data_dir)
    ddir = data_dir / "d"
    ddir.mkdir(parents=True, exist_ok=True)

    index = []
    shard_maps = [dict() for _ in range(shards)]
    for l in listings:
        index.append(_slim(l))
        url = l.get("url")
        det = {k: l[k] for k in DETAIL_FIELDS if l.get(k) not in (None, "", [])}
        if url and det:
            shard_maps[shard_of(url, shards)][url] = det

    index_json = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    v = hashlib.sha1(index_json.encode("utf-8")).hexdigest()[:10]
    _write(data_dir / "index.json", index_json)
    total = 0
    for i, m in enumerate(shard_maps):
        s = json.dumps(m, ensure_ascii=False, separators=(",", ":"))
        total += len(s)
        _write(ddir / f"{i:02d}.json", s)
    _write(data_dir / "manifest.json",
           json.dumps({"v": v, "shards": shards, "count": len(index)}))
    log(f"  payload: index {len(index_json)/1e6:.1f} MB + {shards} detail shards "
        f"{total/1e6:.1f} MB (v={v})")
    return v
