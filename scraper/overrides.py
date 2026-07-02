"""Hand-pinned property details (overrides.json in the repo root).

Listings often hide the exact address. When you learn it (from the agent, the
photos, a viewing), pin it to the listing URL and every subsequent run will
use it — which usually upgrades the RCN deed match to street+number certainty:

    {
      "https://www.otodom.pl/pl/oferta/...": {
        "street": "Adama Asnyka", "nr": "11", "locality": "Gliwice",
        "rooms": 2, "floor": 3, "plot_area": null
      }
    }

Edit the file by hand or pin from the CLI:

    python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --nr 11 \
        --pin https://www.otodom.pl/pl/oferta/...

The pinned fields overwrite the record's snapshot (they are ground truth) and
the record is tagged ``manual`` so you can spot it in history.json.
"""
from __future__ import annotations

import json
import pathlib

PATH = pathlib.Path(__file__).resolve().parents[1] / "overrides.json"
FIELDS = ("street", "nr", "locality", "rooms", "floor", "plot_area", "area")


def load(path=PATH) -> dict:
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(overrides: dict, path=PATH) -> None:
    pathlib.Path(path).write_text(
        json.dumps(overrides, ensure_ascii=False, indent=1), encoding="utf-8")


def pin(url: str, path=PATH, **fields) -> dict:
    """Add/merge one override entry (None values are dropped)."""
    ov = load(path)
    entry = ov.setdefault(url, {})
    for k, v in fields.items():
        if k in FIELDS and v is not None:
            entry[k] = v
    save(ov, path)
    return entry


def apply(records, overrides: dict, log=print) -> int:
    """Write pinned fields into the matching records' snapshots (by URL)."""
    if not overrides:
        return 0
    by_url = {}
    for rec in records:
        for o in rec.get("observations") or []:
            if o.get("url"):
                by_url[o["url"]] = rec
    n = 0
    for url, fields in overrides.items():
        rec = by_url.get(url)
        if rec is None:
            continue
        snap = rec.setdefault("snapshot", {})
        for k, v in (fields or {}).items():
            if k in FIELDS and v is not None:
                snap[k] = v
        if "area" in (fields or {}) and fields.get("area") is not None:
            rec["area"] = fields["area"]
        rec["manual"] = True
        n += 1
    if n:
        log(f"  overrides: pinned details applied to {n} records")
    return n
