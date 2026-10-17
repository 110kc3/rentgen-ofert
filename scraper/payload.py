"""Compact grid indexes and separate lazy current/archive detail shards.

Schema 3 writes index.json + archive.json column tables, URL-keyed d/ shards,
and content-keyed a/ archive shards. Its manifest version covers both indexes
and every detail byte. Passing archive=None retains the legacy schema-2 writer
for compatibility fixtures. See docs/PAYLOAD.md for the wire contract.

FNV-1a(key) % N matches site/app.js. Listing URLs and archive keys are ASCII;
non-ASCII listing URLs remain outside the existing shard-hash contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
from itertools import chain

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


def pack_rows(records):
    """Column names once, trimmed rows; null cells mean an absent field."""
    counts = {}
    for record in records:
        for key in record:
            counts[key] = counts.get(key, 0) + 1
    fields = sorted(counts, key=lambda key: (-counts[key], key))
    rows = []
    for record in records:
        row = [record.get(key) for key in fields]
        while row and row[-1] is None:
            row.pop()
        rows.append(row)
    return {"schema": 1, "fields": fields, "rows": rows}


def unpack_rows(value):
    """Read both legacy object arrays and schema-1 column tables."""
    if isinstance(value, list):
        if any(not isinstance(row, dict) for row in value):
            raise ValueError("invalid listing rows")
        return value
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
        raise ValueError("unsupported column table")
    fields, rows = value.get("fields"), value.get("rows")
    if (not isinstance(fields, list) or not isinstance(rows, list)
            or any(not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", key)
                   or key in ("constructor", "prototype") for key in fields)
            or len(set(fields)) != len(fields)):
        raise ValueError("invalid column table fields")
    result = []
    for row in rows:
        if not isinstance(row, list) or len(row) > len(fields):
            raise ValueError("invalid column table row")
        result.append({fields[i]: cell for i, cell in enumerate(row) if cell is not None})
    return result


def content_version(index_bytes, shard_bytes, *, schema=2):
    """Length-prefixed bytes in the schema's documented payload order."""
    digest = hashlib.sha256(f"rentgen-payload-v{schema}\0".encode())
    for part in chain((index_bytes,), shard_bytes):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()[:20]


def build(listings, data_dir, shards: int = SHARDS, log=print, archive=None) -> str:
    """Write manifest.json + index.json + d/NN.json under ``data_dir``.

    Returns the content-version hash."""
    if archive is not None:
        return _build_compact(listings, archive, data_dir, shards, log)
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
    _write(data_dir / "index.json", index_json)
    total = 0
    for i, m in enumerate(shard_maps):
        s = json.dumps(m, ensure_ascii=False, separators=(",", ":"))
        total += len(s)
        _write(ddir / f"{i:02d}.json", s)
    v = content_version(index_json.encode("utf-8"),
                        ((ddir / f"{i:02d}.json").read_bytes() for i in range(shards)))
    _write(data_dir / "manifest.json",
           json.dumps({"schema": 2, "v": v, "shards": shards, "count": len(index)}))
    log(f"  payload: index {len(index_json)/1e6:.1f} MB + {shards} detail shards "
        f"{total/1e6:.1f} MB (v={v})")
    return v


def _build_compact(listings, archive, data_dir, shards, log):
    """Schema 3 includes both compact indexes and both lazy detail namespaces."""
    root = pathlib.Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    indexes = {"index.json": [], "archive.json": []}
    maps = {"d": [dict() for _ in range(shards)], "a": [dict() for _ in range(shards)]}
    identities = {}
    for listing in listings:
        indexes["index.json"].append(_slim(listing))
        key = listing["url"]
        maps["d"][shard_of(key, shards)][key] = {
            k: listing[k] for k in DETAIL_FIELDS if k in listing}
    for listing in archive:
        # Old histories can share a portal URL. Never overwrite their different
        # timelines, and also preserve byte-identical historical rows separately.
        encoded = json.dumps(listing, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()[:20]
        occurrence = identities.get(digest, 0)
        identities[digest] = occurrence + 1
        key = digest if not occurrence else f"{digest}-{occurrence}"
        slim = _slim(listing)
        for field in ("delisted", "sold"):
            if listing.get(field) is not None:
                slim[field] = listing[field]
        slim["detail_key"] = key
        indexes["archive.json"].append(slim)
        maps["a"][shard_of(key, shards)][key] = {
            k: listing[k] for k in DETAIL_FIELDS if k in listing}
    parts = []
    for name, rows in indexes.items():
        text = json.dumps(pack_rows(rows), ensure_ascii=False, separators=(",", ":"))
        _write(root / name, text)
        parts.append(root / name)
    for namespace, shard_maps in maps.items():
        directory = root / namespace
        directory.mkdir(exist_ok=True)
        expected = {f"{i:02d}.json" for i in range(shards)}
        for old in directory.glob("*.json"):
            if old.name not in expected:
                old.unlink()
        for i, shard in enumerate(shard_maps):
            text = json.dumps(shard, ensure_ascii=False, separators=(",", ":"))
            _write(directory / f"{i:02d}.json", text)
            parts.append(directory / f"{i:02d}.json")
    v = content_version(parts[0].read_bytes(), (path.read_bytes() for path in parts[1:]), schema=3)
    _write(root / "manifest.json", json.dumps({"schema": 3, "v": v, "shards": shards,
           "count": len(listings), "archive": {"count": len(archive), "shards": shards}}))
    log(f"  payload: compact current/archive indexes + {shards} detail shards each (v={v})")
    return v
