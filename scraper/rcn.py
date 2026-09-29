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
import hashlib
import json
import math
import os
import pathlib
import re
import urllib.parse
import xml.etree.ElementTree as ET

from .identity import fold as _fold, street_match, street_parts, known_floor, building_number

WFS = "https://mapy.geoportal.gov.pl/wss/service/rcn"
NS_WFS = "{http://www.opengis.net/wfs/2.0}"
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

# Immutable, last healthy evidence before the 2026-09-24 empty-cache incident.
# Restore only this cache, never the old listing history or published payload.
RECOVERY = {
    "24": {
        "ref": "027bcc45f7b92c5e58e3a194d644146d4c463d6e",
        "path": "cache/rcn_slaskie.json.gz",
        "sha256": "0ff615f76e6d47b24a5da7e11c47baf5a3d07deef2543b7af54a073b90457879",
        "counts": {"lokale": 198439, "budynki": 465807},
    },
}


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


def _get_total(session, typename, flt):
    """A hits query supplies the total omitted from normal live responses."""
    params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
              "typeNames": typename, "filter": flt, "resultType": "hits"}
    response = session.get(WFS + "?" + urllib.parse.urlencode(params),
                           headers=HEADERS, timeout=120)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    if (root.tag != f"{NS_WFS}FeatureCollection"
            or root.get("numberReturned") != "0"
            or root.findall(f"{NS_WFS}member")):
        raise ValueError("RCN: invalid WFS hits response")
    value = root.attrib["numberMatched"]
    if value == "unknown":
        return None
    total = int(value)
    if total < 0:
        raise ValueError("RCN: negative WFS total")
    return total


def _parse_page(xml_bytes, tag):
    """Validate the envelope/counts before exposing any rows to the compactor."""
    root = ET.fromstring(xml_bytes)
    if root.tag != f"{NS_WFS}FeatureCollection":
        raise ValueError("RCN: expected WFS 2.0 FeatureCollection")
    members = root.findall(f"{NS_WFS}member")
    returned = int(root.attrib["numberReturned"])
    matched = root.get("numberMatched")
    total = None if matched == "unknown" else int(matched)
    if (returned != len(members) or returned < 0
            or (total is not None and total < returned)):
        raise ValueError("RCN: inconsistent WFS feature counts")
    rows = []
    ids = []
    for member in members:
        if len(member) != 1 or member[0].tag != f"{NS_MS}{tag}":
            raise ValueError(f"RCN: unexpected feature in {tag} page")
        feat = member[0]
        row = {}
        for child in feat:
            name = child.tag.rsplit("}", 1)[-1].lower()
            if name not in ("msgeometry", "boundedby"):
                row[name] = (child.text or "").strip()
        rows.append(row)
        ids.append(feat.get("{http://www.opengis.net/gml/3.2}id"))
    return rows, total, bool(root.get("next")), ids


def _parse_members(xml_bytes, tag):
    return iter(_parse_page(xml_bytes, tag)[0])


def _market(value):
    value = _fold(value)
    markets = {"": None, "p": "p", "w": "w", "pierwotny": "p",
               "wtorny": "w", "rynekpierwotny": "p", "rynekwtorny": "w"}
    if value not in markets:
        raise ValueError(f"RCN: unknown market value {value!r}")
    return markets[value]


def _to_f(v):
    try:
        value = float(v)
        return value if math.isfinite(value) else None
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
           "rynek": _market(row.get("tran_rodzaj_rynku")),  # p/w
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
           "rynek": _market(row.get("tran_rodzaj_rynku")),
           "msc": msc, "ul": ul, "nr": nr}
    dz = _parcel(row.get("bud_id_budynku"))
    if dz:
        out["dz"] = dz
    return out


def fetch(session, typename, flt, props, tag, compact, log=print):
    out, start = [], 0
    page_hashes = set()
    expected_total = _get_total(session, typename, flt)
    # Never interpret a short page or missing next link as EOF: the live
    # service can return both. Continue to a validated empty page when the
    # total is unknown. A repeated page means startIndex is being ignored.
    for _ in range(10000):
        page = _get_page(session, typename, flt, props, start)
        rows, total, has_next, ids = _parse_page(page, tag)
        n = len(rows)
        if expected_total is None:
            expected_total = total
        if (total is not None and total != expected_total) or (
                expected_total is not None and start + n > expected_total):
            raise ValueError(f"RCN {tag}: changing/inconsistent total "
                             f"({expected_total} -> {total}, offset {start}, returned {n})")
        if not n:
            if has_next or (expected_total is not None and start != expected_total):
                raise ValueError(f"RCN {tag}: premature empty page")
            break
        signature = hashlib.sha256(
            json.dumps([ids, rows], sort_keys=True).encode()).digest()
        if signature in page_hashes:
            raise ValueError(f"RCN {tag}: repeated page at {start}")
        page_hashes.add(signature)
        fields = set().union(*(row.keys() for row in rows))
        required = {"dok_data", "tran_rodzaj_rynku", "tran_rodzaj_trans"}
        required.add("lok_pow_uzyt" if tag == "lokale" else "bud_adres")
        prices = {"tran_cena_brutto",
                  "lok_cena_brutto" if tag == "lokale" else "bud_cena_brutto"}
        if not required <= fields or not prices & fields:
            raise ValueError(f"RCN {tag}: missing expected fields")
        # Dedupe within each page only: distinct deeds in different pages can
        # legitimately have identical compact values.
        seen = set()
        for row in rows:
            c = compact(row)
            if c:
                key = json.dumps(c, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
        start += n
        log(f"  rcn {tag}: {start} fetched, {len(out)} kept")
        if expected_total is not None and start == expected_total:
            if has_next:
                raise ValueError(f"RCN {tag}: next link beyond declared total")
            break
    else:
        raise ValueError(f"RCN {tag}: pagination limit exceeded")
    if not out:
        raise ValueError(f"RCN {tag}: no usable transactions")
    final_total = _get_total(session, typename, flt)
    if final_total is not None and final_total != start:
        raise ValueError(f"RCN {tag}: final total {final_total} != fetched {start}")
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
    tmp = p.with_name(p.name + ".tmp")   # atomic: never leave a truncated snapshot
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, p)


def validate_snapshot(snap, previous=None):
    """Both supported provincial layers must contain usable deed evidence.

    A >20% drop in either complete layer requires investigation, not automatic
    replacement. It is intentionally a publication safety gate, not a claim
    that the source can never legitimately remove records.
    """
    if not isinstance(snap, dict):
        raise ValueError("RCN: missing snapshot")
    dt.date.fromisoformat(snap["fetched"])
    for layer in ("lokale", "budynki"):
        rows = snap.get(layer)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"RCN: empty or missing {layer}")
        for row in rows:
            if (not isinstance(row, dict) or not row.get("d")
                    or (_to_f(row.get("c")) or 0) <= 0):
                raise ValueError(f"RCN: malformed {layer} transaction")
            dt.date.fromisoformat(row["d"])
            if layer == "lokale" and (_to_f(row.get("a")) or 0) <= 0:
                raise ValueError(f"RCN: invalid {layer} area")
            if row.get("rynek") not in (None, "p", "w"):
                raise ValueError(f"RCN: invalid {layer} market")
        if previous and len(rows) < len(previous[layer]) * 0.8:
            raise ValueError(f"RCN: {layer} count fell by more than 20% "
                             f"({len(previous[layer])} -> {len(rows)})")


def recover_snapshot(session, teryt_prefix, log=print):
    recovery = RECOVERY.get(teryt_prefix)
    if not recovery:
        return None
    url = ("https://raw.githubusercontent.com/110kc3/rentgen-ofert/"
           + recovery["ref"] + "/" + recovery["path"])
    response = session.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest() != recovery["sha256"]:
        raise ValueError("RCN: recovery cache checksum mismatch")
    snap = json.loads(gzip.decompress(response.content))
    validate_snapshot(snap)
    if {k: len(snap[k]) for k in recovery["counts"]} != recovery["counts"]:
        raise ValueError("RCN: recovery cache counts mismatch")
    log(f"RCN: recovered last-good evidence from {recovery['ref']}")
    return snap


def refresh(cache_path, session, teryt_prefix="24", today=None, force=False, log=print):
    """Use a verified cache; failed refreshes retain evidence and report degradation.

    No usable fallback returns None. The caller must stop publication in that
    case. Health is exposed separately so cached evidence remains immutable.
    """
    today = today or dt.date.today().isoformat()
    snap = load_snapshot(cache_path)
    try:
        validate_snapshot(snap)
    except (ValueError, KeyError, TypeError):
        snap = None
    refresh.last_health = {"status": "unavailable", "fetched": None,
                           "counts": {}, "error": None}
    if snap is None and teryt_prefix in RECOVERY:
        try:
            snap = recover_snapshot(session, teryt_prefix, log=log)
            save_snapshot(cache_path, snap)
            refresh.last_health["recovered_from"] = RECOVERY[teryt_prefix]["ref"]
        except Exception as exc:
            log(f"RCN: last-good recovery failed ({exc}); attempting fresh pull")
    if snap:
        age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(snap["fetched"])).days
        refresh.last_health.update(fetched=snap["fetched"],
                                   counts={k: len(snap[k]) for k in ("lokale", "budynki")})
        if 0 <= age < MAX_AGE_DAYS and not force:
            refresh.last_health["status"] = "healthy"
            return snap
    try:
        log(f"RCN: pulling transactions for teryt {teryt_prefix}* (this takes minutes) ...")
        lok, bud = fetch_all(session, teryt_prefix, log=log)
        candidate = {"fetched": today, "lokale": lok, "budynki": bud}
        validate_snapshot(candidate, previous=snap)
        # If the recovery download failed, its audited counts still prevent a
        # tiny but non-empty pull from silently replacing the poisoned cache.
        if snap is None and teryt_prefix in RECOVERY:
            for layer, count in RECOVERY[teryt_prefix]["counts"].items():
                if len(candidate[layer]) < count * 0.8:
                    raise ValueError(f"RCN: {layer} below recovery count floor")
        save_snapshot(cache_path, candidate)
        refresh.last_health.update(status="healthy", fetched=today,
                                   counts={"lokale": len(lok), "budynki": len(bud)})
        log(f"RCN: snapshot saved ({len(lok)} lokale, {len(bud)} budynki)")
        return candidate
    except Exception as exc:
        refresh.last_health.update(status="degraded" if snap else "unavailable",
                                   error=str(exc))
        log(f"RCN: refresh failed ({exc}); using previous snapshot" if snap
            else f"RCN: refresh failed ({exc}); no snapshot available")
        return snap


# ---- matching ---------------------------------------------------------------

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
    pinned_nr = bool(snap.get("nr") or street_parts(snap.get("street"))[1]
                     or snap.get("dzialka_id"))
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


def _floor_int(v):
    """Shared exact-floor normalization; ranges/attics remain unknown."""
    return known_floor(v)


def _decimal_area(area):
    """48.63 m2 is near-unique in a town; 50.0 m2 is not."""
    return area is not None and abs(area - round(area)) > 0.01


def _score(rec, snap, r, is_flat, unique=False):
    """(confidence, ok). Confidence: 2 = street-anchored, 1 = attribute-anchored.

    ``unique`` = this deed is the only area-candidate in the whole town; that
    lets weaker attribute evidence through (still conservative: mismatching
    known attributes always reject).
    """
    # A street/parcel locates a building, not a particular unit. Known flat
    # attributes must agree BEFORE any address evidence can accept a deed.
    hits = 0
    if is_flat:
        rooms, floor = _to_i(snap.get("rooms")), _floor_int(snap.get("floor"))
        if rooms is not None and r.get("izb") is not None:
            if rooms != r["izb"]:
                return 0, False
            hits += 1
        if floor is not None and r.get("kond") is not None:
            # Keep the existing tolerance for portal/storey numbering.
            if r["kond"] not in (floor, floor + 1):
                return 0, False
            hits += 1
    dz = snap.get("dzialka_id")
    if dz and r.get("dz") and _fold(dz) == _fold(r["dz"]):
        return 2, True             # same cadastral parcel -> same building
    # NOTE: a parcel MISmatch is not decisive on its own — parcels get
    # renumbered over the years (real case: a 2008 deed on działka 974 whose
    # address sits on today's działka 1506). Street+number agreement wins.
    street, embedded_nr = street_parts(snap.get("street"))
    # building numbers compare space-free: '13 A' and '13A' are the same door
    nr = snap.get("nr") or embedded_nr
    nr = building_number(nr) if nr else None
    deed_street, deed_embedded_nr = street_parts(r.get("ul"))
    deed_nr = r.get("nr") or deed_embedded_nr
    if street and deed_street and street_match(street, deed_street):
        if nr and deed_nr:
            # street AND building number known on both sides -> decisive
            return (2, True) if building_number(deed_nr) == nr else (0, False)
        if r.get("a") is None:
            return 0, False    # area-less deed needs the number to be sure
        return 2, True
    if street and r.get("ul") and not street_match(street, r["ul"]):
        return 0, False        # both known and different -> different property
    if dz and r.get("dz"):
        return 0, False        # parcels differ and no street agreement -> not it
    if r.get("a") is None:
        return 0, False        # area-less deed without street match -> never
    if is_flat:
        if hits >= 2:
            return 1, True
        # a to-the-decimal area that exists exactly once in the town is itself
        # strong evidence — accept (mismatching known attributes already rejected)
        if unique and _decimal_area(rec.get("area")):
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
    # Missing snapshot/layer is unavailable evidence; a present empty layer is
    # evidence with no deeds. Validate before changing any persisted claims.
    by_town = {}
    for typ, layer in (("flat", "lokale"), ("house", "budynki")):
        rows = snapshot.get(layer)
        if rows is None:
            continue
        if not isinstance(rows, list):
            raise ValueError(f"RCN {layer} must be a list or unavailable")
        by_town[typ] = _index_by_town(rows)
    attached = 0
    funnel = {"records": 0, "no_location_yet": 0, "no_deed_candidates": 0,
              "candidates_rejected": 0, "matched": 0}
    for rec in records:
        typ = rec.get("type")
        if typ not in by_town:
            continue
        # These are derived claims: rebuild even when candidates disappear,
        # become ambiguous, contradict a corrected address or change lifecycle.
        rec.pop("sales", None)
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
                    # provenance: which deed this is (address + cadastral parcel)
                    "addr": " ".join(str(x) for x in (r.get("ul"), r.get("nr")) if x) or None,
                    "dz": r.get("dz"),
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
    match.last_funnel = funnel
    log(f"RCN: matched sale events onto {attached} properties "
        f"(funnel: {funnel})")
    return attached
