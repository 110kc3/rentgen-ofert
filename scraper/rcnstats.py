"""Ask-vs-sold benchmarks from RCN deeds -> site/data/rcnstats.json.

The dashboard compares every listing's asking zl/m2 against real notarial-deed
prices and tells the buyer how negotiations around here actually end. Two
pieces, both computed here so the browser only downloads a small lookup:

  towns.<town>.flat.<bucket>.<p|w>  -> {n, med, p25, p75}   deed zl/m2 for
      similar-size flats in that town over the last WINDOW_MONTHS
      (p = rynek pierwotny, w = wtorny; flats only — see _bucket_stats)
  towns.<town>.gap / gap.<all|flat|house> -> {n, med_pct, med_days}
      from properties we watched vanish AND matched to a deed:
      med_pct  = median (deed price - last asking price) / asking, in %
      med_days = median days from first sighting to delisting

Buckets with fewer than MIN_N deeds are dropped — a thin median misleads more
than it helps, so the dashboard shows nothing rather than a shaky number.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter

from .rcn import _fold

WINDOW_MONTHS = 24
MIN_N = 5            # fewer deeds than this -> no benchmark published
PPM_MIN, PPM_MAX = 500, 40000   # zl/m2 outside this is a data error / udział
GAP_MAX_PCT = 40     # |deed vs ask| beyond this is a mismatch, not a discount

FLAT_BUCKETS = ((40, "<40"), (60, "40-59"), (80, "60-79"), (120, "80-119"), (None, "120+"))
HOUSE_BUCKETS = ((100, "<100"), (150, "100-149"), (220, "150-219"), (None, "220+"))


def bucket_of(typ, area):
    if area is None:
        return None
    edges = FLAT_BUCKETS if typ == "flat" else HOUSE_BUCKETS if typ == "house" else None
    if edges is None:
        return None
    for hi, name in edges:
        if hi is None or area < hi:
            return name
    return None


def _pctile(sorted_vals, q):
    """Linear-interpolation percentile of an already-sorted list."""
    if not sorted_vals:
        return None
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _bucket_stats(snapshot, cutoff, min_n):
    """towns[folded] = {"_names": Counter, "flat": {bucket: {mk: [ppm...]}}}

    Flats only. The budynki layer's price is usually a building-value fragment
    of a larger deed, not a house sale (voivodeship-wide median ~200 zl/m2), so
    zl/m2 benchmarks built from it would be misinformation. House deeds still
    feed the ask-vs-sold gap, where the +-GAP_MAX_PCT filter rejects fragments.
    """
    towns = {}
    for typ, rows in (("flat", snapshot.get("lokale") or []),):
        for r in rows:
            d, c, a, mk = r.get("d"), r.get("c"), r.get("a"), r.get("rynek")
            if not d or d < cutoff or not c or not a or mk not in ("p", "w"):
                continue
            ppm = c / a
            if not (PPM_MIN <= ppm <= PPM_MAX):
                continue
            b = bucket_of(typ, a)
            town = _fold(r.get("msc"))
            if not town or not b:
                continue
            t = towns.setdefault(town, {"_names": Counter()})
            t["_names"][r["msc"]] += 1
            t.setdefault(typ, {}).setdefault(b, {}).setdefault(mk, []).append(ppm)

    out = {}
    for town, t in towns.items():
        entry = {"name": t["_names"].most_common(1)[0][0]}
        for typ in ("flat", "house"):
            buckets = {}
            for b, by_mk in (t.get(typ) or {}).items():
                mks = {}
                for mk, vals in by_mk.items():
                    if len(vals) < min_n:
                        continue
                    vals.sort()
                    mks[mk] = {"n": len(vals),
                               "med": round(_pctile(vals, 0.5)),
                               "p25": round(_pctile(vals, 0.25)),
                               "p75": round(_pctile(vals, 0.75))}
                if mks:
                    buckets[b] = mks
            if buckets:
                entry[typ] = buckets
        if len(entry) > 1:
            out[town] = entry
    return out


def gap_pairs(records):
    """(town, town_display, type, gap_pct, days_on_market) for every watched
    property that vanished and got an RCN deed attached.
    gap_pct < 0 = sold below ask."""
    for rec in records:
        if rec.get("development") or not rec.get("delisted"):
            continue
        sold = [s for s in rec.get("sales") or []
                if s.get("kind") == "sold" and s.get("price")]
        if not sold:
            continue
        deed = max(sold, key=lambda s: s.get("date") or "")
        obs = sorted(rec.get("observations") or [], key=lambda o: o.get("date") or "")
        ask = next((o["price"] for o in reversed(obs) if o.get("price")), None)
        if not ask or ask < 10000:
            continue
        pct = (deed["price"] - ask) / ask * 100
        if abs(pct) > GAP_MAX_PCT:
            continue          # almost certainly a mismatched deed / udział sale
        days = None
        try:
            days = (dt.date.fromisoformat(rec["delisted"])
                    - dt.date.fromisoformat(rec["first_seen"])).days
        except (KeyError, TypeError, ValueError):
            pass
        snap = rec.get("snapshot") or {}
        disp = snap.get("locality") if _fold(snap.get("locality")) else snap.get("district")
        town = _fold(snap.get("locality")) or _fold(snap.get("district"))
        yield town, disp, rec.get("type"), pct, days


def _gap_summary(pairs):
    pcts = sorted(p for _, _, _, p, _ in pairs)
    days = sorted(d for _, _, _, _, d in pairs if d is not None)
    if not pcts:
        return None
    out = {"n": len(pcts), "med_pct": round(_pctile(pcts, 0.5), 1)}
    if days:
        out["med_days"] = round(_pctile(days, 0.5))
    return out


def build(snapshot, records, today=None,
          window_months=WINDOW_MONTHS, min_n=MIN_N):
    """Assemble the rcnstats.json payload. Small: towns x buckets x 2 markets."""
    today = today or dt.date.today().isoformat()
    # real calendar months back, not months*30 days (720 days ≠ the advertised
    # 24 months — deeds near the edge were silently dropped)
    d = dt.date.fromisoformat(today)
    m = d.year * 12 + (d.month - 1) - window_months
    cutoff = dt.date(m // 12, m % 12 + 1,
                     min(d.day, 28)).isoformat()
    towns = _bucket_stats(snapshot or {}, cutoff, min_n)

    pairs = list(gap_pairs(records or []))
    by_town = {}
    for pair in pairs:
        if pair[0]:
            by_town.setdefault(pair[0], []).append(pair)
    for town, tp in by_town.items():
        if len(tp) >= min_n:
            g = _gap_summary(tp)
            if g:
                towns.setdefault(town, {"name": tp[0][1]})
                towns[town]["gap"] = g

    gap = {}
    for key in ("all", "flat", "house"):
        sel = pairs if key == "all" else [p for p in pairs if p[2] == key]
        g = _gap_summary(sel)
        if g:
            gap[key] = g

    return {"built": today, "window_months": window_months, "min_n": min_n,
            "towns": towns, "gap": gap}
