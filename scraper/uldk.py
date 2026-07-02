"""Address -> parcel resolution via free GUGiK services.

Two-step chain, no API key needed:

  1. UUG  (services.gugik.gov.pl/uug)  geocodes "Gliwice, Daszyńskiego 448"
     -> canonical street name ("Ignacego Daszyńskiego"), TERYT and an
     EPSG:2180 point of the address.
  2. ULDK (uldk.gugik.gov.pl) GetParcelByXY -> the cadastral parcel id at
     that point, e.g. "246601_1.0041.1506" (TERYT_ark.obręb.działka).

The parcel id is the strongest possible RCN anchor: deed identifiers
(lok_id_lokalu / bud_id_budynku) embed the same parcel prefix.
"""
from __future__ import annotations

import re

import requests

UUG = "https://services.gugik.gov.pl/uug/"
ULDK = "https://uldk.gugik.gov.pl/"
HEADERS = {"User-Agent": "rentgen-ofert requests"}


def geocode(locality, street=None, nr=None, session=None):
    """UUG address search -> {street, number, teryt, x, y} (EPSG:2180) or None."""
    session = session or requests.Session()
    addr = locality
    if street:
        addr += f", {street}" + (f" {nr}" if nr else "")
    try:
        r = session.get(UUG, params={"request": "GetAddress", "address": addr},
                        headers=HEADERS, timeout=20)
        r.raise_for_status()
        res = (r.json().get("results") or {}).get("1")
    except Exception:
        return None
    if not res:
        return None
    return {"street": res.get("street"), "number": res.get("number"),
            "teryt": res.get("teryt"),
            "x": float(res["x"]), "y": float(res["y"])}


def parcel_by_xy(x, y, session=None):
    """ULDK point -> {id, obreb, nr} or None. Coordinates in EPSG:2180."""
    session = session or requests.Session()
    try:
        r = session.get(ULDK, params={"request": "GetParcelByXY",
                                      "xy": f"{x},{y},2180",
                                      "result": "id,region,parcel"},
                        headers=HEADERS, timeout=20)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
    except Exception:
        return None
    if len(lines) < 2 or lines[0].strip() != "0":
        return None
    parts = lines[1].split("|")
    return {"id": parts[0].strip(),
            "obreb": parts[1].strip() if len(parts) > 1 else None,
            "nr": parts[2].strip() if len(parts) > 2 else None}


def _num_eq(a, b):
    n = lambda v: re.sub(r"[^0-9a-z/]", "", str(v).lower())
    return n(a) == n(b)


def resolve(locality, street=None, nr=None, session=None):
    """Full chain. When ``nr`` is given the geocoder must confirm that exact
    building number — otherwise UUG may have snapped to the street/city centre
    and the parcel under that point would be someone else's."""
    session = session or requests.Session()
    g = geocode(locality, street, nr, session=session)
    if not g:
        return None
    if nr and not (g.get("number") and _num_eq(g["number"], nr)):
        return {**g, "dzialka_id": None,
                "note": "geokoder nie potwierdził numeru budynku"}
    p = parcel_by_xy(g["x"], g["y"], session=session) or {}
    return {**g, "dzialka_id": p.get("id"), "obreb": p.get("obreb")}
