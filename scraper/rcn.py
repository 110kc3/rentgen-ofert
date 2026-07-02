"""RCN — Rejestr Cen Nieruchomości (real transaction prices from notarial deeds).

Since Feb 2026 GUGiK publishes the nationwide RCN for free via a WFS 2.0 service:

    https://mapy.geoportal.gov.pl/wss/service/rcn

Layers: ms:lokale (flat transactions) and ms:budynki (buildings on transacted
parcels). Each feature carries the deed date (dok_data), gross price, usable
area, room count / storey, market type (pierwotny/wtórny) and a coarse address
(``MSC:Gliwice;UL:Gdańska;NR_PORZ:13``). We pull the whole voivodeship (teryt
prefix, default 24* = śląskie), store a compact gzipped snapshot in ``cache/``,
and match transactions to our per-property history records:

  * a transaction *before* the listing appeared  -> "kupione w ... za ..."
  * a transaction *after* the listing vanished   -> "sprzedane za ... (RCN)"

Matching is probabilistic (portals hide exact addresses), so every attached
sale carries a confidence level and is only attached when unambiguous.

Notes on the service, learned by probing it:
  * ``PropertyIsLike`` filters work; ``PropertyIsEqualTo`` 500s. A LIKE without
    wildcards is an exact match.
  * ``outputFormat=geojson`` is not enabled — we parse the default GML 3.2.
  * ``sortBy`` puts NULL dates first, so incremental "newest first" pulls are
    unreliable; we re-pull the full set instead (fast: ~0.6 s / 1000 rows).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import pathlib
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

WFS = "https://mapy.geoportal.gov.pl/wss/service/rcn"
NS_MS = "{http://mapserver.gis.umn.edu/mapserver}"
PAGE = 2000
MAX_AGE_DAYS = 7          # re-pull the snapshot when older than this
AREA_TOL = 0.6            # m² tolerance listing-vs-deed
SALE_WINDOW_BEFORE = 60   # deed may precede the delisting we observed (days)
SALE_WINDOW_AFTER = 400   # deed (+ registry lag) may trail delisting (days)

LOK_PROPS = ("teryt,dok_data,tran_rodzaj_rynku,tran_rodzaj_trans,tran_cena_brutto,"
             "lok_cena_brutto,lok_pow_uzyt,lok_liczba_izb,lok_nr_kond,lok_adres,"
             "lok_funkcja,lok_id_lokalu")
BUD_PROPS = ("teryt,dok_data,tran_rodzaj_rynku,tran_rodzaj_trans,tran_cena_brutto,"
             "bud_cena_brutto,bud_pow_uzyt,bud_rodzaj,bud_adres,nier_pow_gruntu,"
             "bud_id_budynku")

HEADERS = {"User-Agent": "rentgen-ofert (+https://github.com/) requests"}


# ---- WFS fetch --------------------------------------------------------------

def _like(field: str, literal: str) -> str:
    return (f'<PropertyIsLike wildCard="*" singleChar="." escapeChar="!">'
            f'<ValueReference>{field}</ValueReference><Literal>{literal}</Literal>'
            f'</PropertyIsLike>')


def _filter(parts) -> str:
    inner = "".join(parts)
    if len(parts) > 1:
        inner = f"<And>{inner}</And>"
    return f'<Filter xmlns="http://www.opengis.net/fes/2.0">{inner}</Filter>'


def _get_page(session, typename, flt, props, start):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": typename, "count": str(PAGE), "startIndex": str(start),
        "filter": flt, "propertyName": f"({props})",
    }
    url = WFS + "?" + urllib.parse.urlencode(params)
    r = session.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    return r.content


def _parse_members(xml_bytes, tag):
    """Yield {field: text} dicts for every <ms:{tag}> feature in a GML page."""
    root = ET.fromstring(xml_bytes)
    if root.tag.endswith("ExceptionReport"):
        raise RuntimeError("WFS exception: " + ET.tostring(root, encoding="unicode")[:300])
    for feat in root.iter(f"{NS_MS}{tag}"):
        row = {}
        for child in feat:
            name = child.tag.rsplit("}", 1)[-1]
            if name in ("msGeometry", "boundedBy"):
                continue
            row[name] = (child.text or "").strip()
        yield row


def _to_f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _addr(raw):
    """'MSC:Gliwice;UL:Gdańska;NR_PORZ:13' -> (msc, ul, nr)."""
    out = {"MSC": None, "UL": None, "NR_PORZ": None}
    for part in (raw or "").split(";"):
        k, _, v = part.partition(":")
        if k in out and v:
            out[k] = v.strip()
    return out["MSC"], out["UL"], out["NR_PORZ"]


def _parcel(egib_id):
    """'221104_4.0004.921_BUD.22_LOK' -> '221104_4.0004.921' (the parcel)."""
    if not egib_id:
        return None
    return egib_id.split("_BUD")[0].strip() or None


def _compact_lok(row):
    date = (row.get("dok_data") or "")[:10]
    price = _to_f(row.get("lok_cena_brutto")) or _to_f(row.get("tran_cena_brutto"))
    area = _to_f(row.get("lok_pow_uzyt"))
    if not date or not price or not area:
        return None
    if row.get("lok_funkcja") not in ("", None, "mieszkalna"):
        return None
    if row.get("tran_rodzaj_trans") not in ("", None, "wolnyRynek"):
        return None
    msc, ul, nr = _addr(row.get("lok_adres"))
    out = {"d": date, "c": round(price), "a": area,
           "izb": _to_i(row.get("lok_liczba_izb")), "kond": _to_i(row.get("lok_nr_kond")),
           "rynek": (row.get("tran_rodzaj_rynku") or "")[:1] or None,  # p/w
           "msc": msc, "ul": ul, "nr": nr}
    dz = _parcel(row.get("lok_id_lokalu"))
    if dz:
        out["dz"] = dz
    return out


def _compact_bud(row):
    date = (row.get("dok_data") or "")[:10]
    price = _to_f(row.get("bud_cena_brutto")) or _to_f(row.get("tran_cena_brutto"))
    area = _to_f(row.get("bud_pow_uzyt"))
    if not date or not price:
        return None            # area may be missing — still useful by address
    if row.get("tran_rodzaj_trans") not in ("", None, "wolnyRynek"):
        return None
    msc, ul, nr = _addr(row.get("bud_adres"))
    out = {"d": date, "c": round(price), "a": area,
           "grunt": _to_f(row.get("nier_pow_gruntu")),
           "rynek": (row.get("tran_rodzaj_rynku") or "")[:1] or None,
           "msc": msc, "ul": ul, "nr": nr}
    dz = _parcel(row.get("bud_id_budynku"))
    if dz:
        out["dz"] = dz
    return out


def fetch(session, typename, flt, props, tag, compact, log=print):
    out, start = [], 0
    while True:
        page = _get_page(session, typename, flt, props, start)
        n = 0
        for row in _parse_members(page, tag):
            n += 1
            c = compact(row)
            if c:
                out.append(c)
        if n:
            log(f"  rcn {tag}: {start + n} fetched, {len(out)} kept")
        if n < PAGE:
            break
        start += n
    return out


def fetch_all(session, teryt_prefix="24", log=print):
    """Pull flats + residential buildings for a voivodeship. Returns (lokale, budynki)."""
    lok = fetch(session, "ms:lokale", _filter([_like("teryt", teryt_prefix + "*")]),
                LOK_PROPS, "lokale", _compact_lok, log=log)
    bud = fetch(session, "ms:budynki",
                _filter([_like("teryt", teryt_prefix + "*"), _like("bud_rodzaj", "mieszkalny")]),
                BUD_PROPS, "budynki", _compact_bud, log=log)
    return lok, bud


# ---- snapshot cache ---------------------------------------------------------

def load_snapshot(path):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_snapshot(path, data):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def refresh(cache_path, session, teryt_prefix="24", today=None, force=False, log=print):
    """Load the cached RCN snapshot, re-pulling from the WFS when stale.

    Returns {"fetched": date, "lokale": [...], "budynki": [...]} or None when
    no snapshot exists and the service is unreachable.
    """
    today = today or dt.date.today().isoformat()
    snap = load_snapshot(cache_path)
    if snap and not force:
        try:
            age = (dt.date.fromisoformat(today)
                   - dt.date.fromisoformat(snap.get("fetched", "1970-01-01"))).days
        except ValueError:
            age = MAX_AGE_DAYS + 1
        if age < MAX_AGE_DAYS:
            return snap
    try:
        log(f"RCN: pulling transactions for teryt {teryt_prefix}* (this takes minutes) ...")
        lok, bud = fetch_all(session, teryt_prefix, log=log)
        snap = {"fetched": today, "lokale": lok, "budynki": bud}
        save_snapshot(cache_path, snap)
        log(f"RCN: snapshot saved ({len(lok)} lokale, {len(bud)} budynki)")
        return snap
    except Exception as exc:
        log(f"RCN: refresh failed ({exc}); using previous snapshot" if snap
            else f"RCN: refresh failed ({exc}); no snapshot available")
        return snap


# ---- matching ---------------------------------------------------------------

def _fold(s):
    """lowercase, strip diacritics (incl. ł) and punctuation."""
    if not s:
        return ""
    s = s.replace("ł", "l").replace("Ł", "L")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


_STREET_NOISE = {"ul", "ulica", "al", "aleja", "pl", "plac", "os", "osiedle", "gen",
                 "sw", "ks", "dr", "prof", "mjr", "kpt", "im"}


def _street_tokens(s):
    return [t for t in _fold(s).split() if t not in _STREET_NOISE and not t.isdigit()]


def _tok_eq(a, b):
    """Token equality tolerant of Polish declension: 'gdanska' == 'gdanskiej',
    'polna' == 'polnej', but 'kwiatowa' != 'kwiatkowskiego'."""
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    common = 0
    for x, y in zip(short, long_):
        if x != y:
            break
        common += 1
    return (common >= 4 and common >= len(short) - 1
            and len(long_) - common <= 3)


def street_match(a, b):
    """True when two street names plausibly refer to the same street.

    Compares the significant last token (surname) with declension tolerance
    and requires any remaining tokens of the shorter name to appear in the
    longer one, so 'Asnyka' == 'Adama Asnyka', 'ul. Gdanskiej' == 'Gdanska',
    but 'Polna' != 'Lipowa'.
    """
    ta, tb = _street_tokens(a), _street_tokens(b)
    if not ta or not tb:
        return False
    if not _tok_eq(ta[-1], tb[-1]):
        return False
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return all(any(_tok_eq(t, u) for u in big) for t in small[:-1])


def _index_by_town(rows):
    idx = {}
    for r in rows:
        idx.setdefault(_fold(r.get("msc")), []).append(r)
    return idx


def _candidates(rec, rows_by_town):
    snap = rec.get("snapshot") or {}
    area = rec.get("area")
    if area is None:
        return [], snap
    rows = ()
    # portals sometimes put a district (Trynek, Srodmiescie) in `locality` and
    # the real town in `district` (or vice versa) — try both
    for key in (snap.get("locality"), snap.get("district")):
        town = _fold(key)
        if town and town in rows_by_town:
            rows = rows_by_town[town]
            break
    pinned_nr = bool(snap.get("nr")) or bool(snap.get("dzialka_id"))
    out = []
    for r in rows:
        if r.get("a") is None:
            if pinned_nr and r.get("ul"):
                out.append(r)      # judged by street+number in _score
            continue
        if abs(r["a"] - area) > AREA_TOL:
            continue
        out.append(r)
    return out, snap


_FLOOR_WORDS = {"parter": 0, "suterena": -1, "poddasze": None}


def _floor_int(v):
    """Portal floors arrive as int, "3", "parter", "> 10", None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    t = str(v).strip().lower()
    if t in _FLOOR_WORDS:
        return _FLOOR_WORDS[t]
    m = re.search(r"-?\d+", t)
    return int(m.group()) if m else None


def _decimal_area(area):
    """48.63 m2 is near-unique in a town; 50.0 m2 is not."""
    return area is not None and abs(area - round(area)) > 0.01


def _score(rec, snap, r, is_flat, unique=False):
    """(confidence, ok). Confidence: 2 = street-anchored, 1 = attribute-anchored.

    ``unique`` = this deed is the only area-candidate in the whole town; that
    lets weaker attribute evidence through (still conservative: mismatching
    known attributes always reject).
    """
    dz = snap.get("dzialka_id")
    if dz and r.get("dz"):
        # same cadastral parcel -> same building; different parcel -> not it
        return (2, True) if _fold(dz) == _fold(r["dz"]) else (0, False)
    street = snap.get("street")
    nr = _fold(str(snap.get("nr"))) if snap.get("nr") else None
    if street and r.get("ul") and street_match(street, r["ul"]):
        if nr and r.get("nr"):
            # street AND building number known on both sides -> decisive
            return (2, True) if _fold(str(r["nr"])) == nr else (0, False)
        if r.get("a") is None:
            return 0, False    # area-less deed needs the number to be sure
        return 2, True
    if street and r.get("ul") and not street_match(street, r["ul"]):
        return 0, False        # both known and different -> different property
    if r.get("a") is None:
        return 0, False        # area-less deed without street match -> never
    if is_flat:
        rooms, floor = _to_i(snap.get("rooms")), _floor_int(snap.get("floor"))
        hits = 0
        if rooms is not None and r.get("izb") is not None:
            if rooms != r["izb"]:
                return 0, False
            hits += 1
        if floor is not None and r.get("kond") is not None:
            # kondygnacja is 1-based (parter = 1), listing floor is usually 0-based
            if r["kond"] not in (floor, floor + 1):
                return 0, False
            hits += 1
        if hits >= 2:
            return 1, True
        # a to-the-decimal area that exists exactly once in the town is itself
        # strong evidence — accept with rooms agreeing (or unknown)
        if unique and _decimal_area(rec.get("area")) and hits >= 0:
            return 1, True
        return 0, False
    # houses: no street -> corroborate with the plot area (deed carries it)
    plot = _to_f(snap.get("plot_area"))
    grunt = _to_f(r.get("grunt"))
    if plot and grunt and abs(plot - grunt) <= 0.1 * max(plot, grunt):
        return 1, True
    if unique and _decimal_area(rec.get("area")) and (not plot or not grunt):
        return 1, True
    return 0, False


def _within(d, lo, hi):
    return (not lo or d >= lo) and (not hi or d <= hi)


def _shift(date_str, days):
    try:
        return (dt.date.fromisoformat(date_str) + dt.timedelta(days=days)).isoformat()
    except ValueError:
        return None


def match(records, snapshot, log=print):
    """Attach RCN sale events to history records (in place).

    rec["sales"] = [{date, price, price_m2, market, confidence, kind}]
      kind: "past"  — deed predates our first sighting (previous sale of the flat)
            "sold"  — deed follows the listing's disappearance (confirmed sale)
    """
    if not snapshot:
        return 0
    by_town = {"flat": _index_by_town(snapshot.get("lokale") or []),
               "house": _index_by_town(snapshot.get("budynki") or [])}
    attached = 0
    funnel = {"records": 0, "no_location_yet": 0, "no_deed_candidates": 0,
              "candidates_rejected": 0, "matched": 0}
    for rec in records:
        typ = rec.get("type")
        if typ not in by_town:
            continue
        if rec.get("development"):
            continue   # marketing photos != a specific flat; deeds can't be attributed
        funnel["records"] += 1
        cands, snap = _candidates(rec, by_town[typ])
        if not cands:
            if not _fold(snap.get("locality")) and not _fold(snap.get("district")):
                funnel["no_location_yet"] += 1
            else:
                funnel["no_deed_candidates"] += 1
            continue
        first_seen = rec.get("first_seen")
        delisted = rec.get("delisted")
        sales = []
        for kind, lo, hi in (
            ("past", None, _shift(first_seen, -1) if first_seen else None),
            ("sold", _shift(delisted, -SALE_WINDOW_BEFORE) if delisted else None,
                     _shift(delisted, SALE_WINDOW_AFTER) if delisted else None),
        ):
            if kind == "sold" and not delisted:
                continue
            window = [r for r in cands if _within(r["d"], lo, hi)]
            unique = len(cands) == 1
            scored = []
            for r in window:
                conf, ok = _score(rec, snap, r, typ == "flat", unique=unique)
                if ok:
                    scored.append((conf, r))
            if not scored:
                continue
            best_conf = max(c for c, _ in scored)
            best = [r for c, r in scored if c == best_conf]
            # "sold" must be unambiguous; "past" may legitimately have several deeds
            if kind == "sold" and len(best) > 1:
                continue
            if kind == "past" and len(best) > 3:
                continue           # a whole new-build staircase — too ambiguous
            for r in sorted(best, key=lambda x: x["d"]):
                sales.append({
                    "date": r["d"], "price": r["c"],
                    "price_m2": round(r["c"] / r["a"]) if r.get("a") else None,
                    "market": {"p": "pierwotny", "w": "wtórny"}.get(r.get("rynek")),
                    "confidence": "wysoka" if best_conf == 2 else "średnia",
                    "kind": kind,
                })
        if sales:
            seen = set()
            uniq = []
            for s in sales:
                k = (s["date"], s["price"])
                if k not in seen:
                    seen.add(k)
                    uniq.append(s)
            rec["sales"] = uniq
            attached += 1
            funnel["matched"] += 1
        else:
            funnel["candidates_rejected"] += 1
    funnel["candidates_rejected"] -= funnel["matched"] if False else 0
    match.last_funnel = funnel
    log(f"RCN: matched sale events onto {attached} properties "
        f"(funnel: {funnel})")
    return attached
