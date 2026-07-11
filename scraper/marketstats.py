"""Market-level time series -> site/data/stats.json (the "Statystyki" page).

Two clocks feed the charts:

  * **weekly** (from history.json observations, so it only reaches back to the
    tool's first run): active supply, median asking zl/m2, new listings,
    confirmed withdrawals and price cuts per ISO week — global per type, plus
    active/median for the TOWN_LIMIT busiest towns.
  * **monthly** (from the RCN deed snapshot, reaching back years): median
    transacted zl/m2 + deed count for flats, wtorny/pierwotny split globally
    and wtorny-only per town. Flats only — see rcnstats._bucket_stats for why
    house zl/m2 from the budynki layer would be misinformation.

Everything is parallel arrays over a shared "weeks"/"months" axis (nulls where
a cell has no data) to keep the payload small. Developer records are excluded
from the history-derived series: their observations are rolling marketing, not
properties entering/leaving the market.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from .rcn import _fold

TOWN_LIMIT = 40        # towns that get their own weekly + monthly series
RCN_SINCE = "2018-01"  # first month of the deed series
MIN_MONTH_N = 5        # fewer deeds in a month -> null (a shaky median misleads)
PPM_MIN, PPM_MAX = 500, 40000          # same sanity bounds as rcnstats
DOM_BUCKETS = ((30, "≤30"), (60, "31–60"), (90, "61–90"), (180, "91–180"),
               (365, "181–365"), (None, ">365"))


def _week_of(date_str):
    """ISO date -> that week's Monday (the axis key)."""
    try:
        d = dt.date.fromisoformat(date_str[:10])
    except (TypeError, ValueError):
        return None
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _axis(first, last, step):
    """Inclusive list of week-Mondays or YYYY-MM months from first to last."""
    out = []
    if step == "week":
        d = dt.date.fromisoformat(first)
        stop = dt.date.fromisoformat(last)
        while d <= stop:
            out.append(d.isoformat())
            d += dt.timedelta(days=7)
    else:
        y, m = int(first[:4]), int(first[5:7])
        while f"{y:04d}-{m:02d}" <= last:
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                y, m = y + 1, 1
    return out


def _town_of(rec):
    snap = rec.get("snapshot") or {}
    for key in (snap.get("locality"), snap.get("district")):
        f = _fold(key)
        if f:
            return f, key
    return None, None


def _weekly(records, towns_top):
    """Weekly series from observations. towns_top: {folded: display}."""
    # per (week, type) pools; per (week, type, town) pools for the top towns
    active = Counter()
    ppms = defaultdict(list)
    t_active = Counter()
    t_ppms = defaultdict(list)
    new = Counter()
    gone = Counter()
    cuts = Counter()
    weeks_seen = set()

    for rec in records:
        if rec.get("development"):
            continue
        typ, area = rec.get("type"), rec.get("area")
        if typ not in ("flat", "house"):
            continue
        town, _ = _town_of(rec)
        in_top = town in towns_top
        # count these weeks into the axis too — a withdrawal whose week has no
        # live observation anywhere (e.g. archived-ad evidence) must still show
        w_first = _week_of(rec.get("first_seen") or "")
        if w_first:
            new[(w_first, typ)] += 1
            weeks_seen.add(w_first)
        w_gone = _week_of(rec.get("delisted") or "")
        if w_gone:
            gone[(w_gone, typ)] += 1
            weeks_seen.add(w_gone)

        # one snapshot per week the property was live: last price of the week
        by_week = {}
        last_price = {}
        for o in sorted(rec.get("observations") or [], key=lambda o: o.get("date") or ""):
            w = _week_of(o.get("date") or "")
            if not w or o.get("status") == "archived":
                continue
            p, url = o.get("price"), o.get("url")
            if p is not None and last_price.get(url) is not None and p < last_price[url]:
                cuts[(_week_of(o["date"]), typ)] += 1
            if p is not None:
                last_price[url] = p
                by_week[w] = p
            else:
                by_week.setdefault(w, None)
        for w, p in by_week.items():
            weeks_seen.add(w)
            active[(w, typ)] += 1
            if in_top:
                t_active[(w, typ, town)] += 1
            if p and area and PPM_MIN <= p / area <= PPM_MAX:
                ppms[(w, typ)].append(p / area)
                if in_top:
                    t_ppms[(w, typ, town)].append(p / area)

    if not weeks_seen:
        return {"weeks": [], "global": {}, "towns": {}}
    weeks = _axis(min(weeks_seen), max(weeks_seen), "week")

    def _round_med(vals):
        m = _median(vals or [])
        return round(m) if m is not None else None

    out_global = {}
    for typ in ("flat", "house"):
        out_global[typ] = {
            "active": [active.get((w, typ), 0) for w in weeks],
            "med": [_round_med(ppms.get((w, typ))) for w in weeks],
            "new": [new.get((w, typ), 0) for w in weeks],
            "gone": [gone.get((w, typ), 0) for w in weeks],
            "cuts": [cuts.get((w, typ), 0) for w in weeks],
        }
    out_towns = {}
    for town, disp in towns_top.items():
        entry = {}
        for typ in ("flat", "house"):
            if not any(t_active.get((w, typ, town)) for w in weeks):
                continue
            entry[typ] = {
                "active": [t_active.get((w, typ, town), 0) for w in weeks],
                "med": [_round_med(t_ppms.get((w, typ, town))) for w in weeks],
            }
        if entry:
            out_towns[disp] = entry
    return {"weeks": weeks, "global": out_global, "towns": out_towns}


def _rcn_monthly(snapshot, towns_top, last_month):
    """Monthly deed medians for flats: global w+p, per-town w only."""
    pools = defaultdict(list)      # (month, market) -> [ppm]
    t_pools = defaultdict(list)    # (month, town) -> [ppm]  (wtorny only)
    for r in (snapshot or {}).get("lokale") or []:
        d, c, a, mk = r.get("d"), r.get("c"), r.get("a"), r.get("rynek")
        if not d or not c or not a or mk not in ("p", "w"):
            continue
        month = d[:7]
        if month < RCN_SINCE or month > last_month:
            continue
        ppm = c / a
        if not (PPM_MIN <= ppm <= PPM_MAX):
            continue
        pools[(month, mk)].append(ppm)
        if mk == "w":
            town = _fold(r.get("msc"))
            if town in towns_top:
                t_pools[(month, town)].append(ppm)

    if not pools:
        return {"months": [], "global": {}, "towns": {}}
    months = _axis(RCN_SINCE, last_month, "month")

    def stat(vals):
        if len(vals or []) < MIN_MONTH_N:
            return None, len(vals or [])
        return round(_median(vals)), len(vals)

    out_global = {}
    for mk in ("w", "p"):
        med, n = [], []
        for m in months:
            v, k = stat(pools.get((m, mk)))
            med.append(v)
            n.append(k)
        out_global[mk] = {"med": med, "n": n}
    out_towns = {}
    for town, disp in towns_top.items():
        med, n = [], []
        for m in months:
            v, k = stat(t_pools.get((m, town)))
            med.append(v)
            n.append(k)
        if any(x is not None for x in med):
            out_towns[disp] = {"w": {"med": med, "n": n}}
    return {"months": months, "global": out_global, "towns": out_towns}


def _dom_and_cuts(records):
    """Days-on-market histogram (delisted only) + share of records that cut."""
    dom = [0] * len(DOM_BUCKETS)
    cut_n = {"flat": 0, "house": 0}
    base_n = {"flat": 0, "house": 0}
    for rec in records:
        if rec.get("development"):
            continue
        typ = rec.get("type")
        if rec.get("delisted") and rec.get("first_seen"):
            try:
                days = (dt.date.fromisoformat(rec["delisted"])
                        - dt.date.fromisoformat(rec["first_seen"])).days
            except ValueError:
                days = None
            if days is not None and days >= 0:
                for i, (hi, _) in enumerate(DOM_BUCKETS):
                    if hi is None or days <= hi:
                        dom[i] += 1
                        break
        if typ not in cut_n:
            continue
        last_price = {}
        prices = 0
        cut = False
        for o in sorted(rec.get("observations") or [], key=lambda o: o.get("date") or ""):
            p, url = o.get("price"), o.get("url")
            if p is None:
                continue
            prices += 1
            if last_price.get(url) is not None and p < last_price[url]:
                cut = True
            last_price[url] = p
        if prices >= 2:
            base_n[typ] += 1
            if cut:
                cut_n[typ] += 1
    share = {t: round(cut_n[t] / base_n[t], 3) if base_n[t] else None
             for t in cut_n}
    return {"buckets": [b for _, b in DOM_BUCKETS], "counts": dom}, share


def _top_towns(records, snapshot):
    """{folded: display} for the TOWN_LIMIT towns with most live records.
    Display spelling prefers the RCN deed register over portal free text."""
    live = Counter()
    disp = {}
    for rec in records:
        if rec.get("development") or rec.get("delisted"):
            continue
        town, raw = _town_of(rec)
        if town:
            live[town] += 1
            disp.setdefault(town, raw)
    rcn_names = {}
    for r in (snapshot or {}).get("lokale") or []:
        f = _fold(r.get("msc"))
        if f and f not in rcn_names:
            rcn_names[f] = r["msc"]
    return {t: rcn_names.get(t) or disp[t]
            for t, _ in live.most_common(TOWN_LIMIT)}


def build(records, snapshot, today=None):
    today = today or dt.date.today().isoformat()
    towns_top = _top_towns(records, snapshot)
    dom, cut_share = _dom_and_cuts(records)
    return {
        "built": today,
        "weekly": _weekly(records, towns_top),
        "rcn": _rcn_monthly(snapshot, towns_top, today[:7]),
        "dom": dom,
        "cut_share": cut_share,
    }
