"""Check one specific property against the RCN transaction register.

Looks up notarial deeds in the cached snapshot (cache/rcn_snapshot.json.gz,
pulled by the main scraper). Search by size, by exact address, or both — and
optionally *pin* the address to a listing URL so the automatic matcher uses
it on every future run (see scraper/overrides.py).

Examples (run from the repo root):

    # by size (classic)
    python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --pokoje 2

    # by exact address — no area needed, searches flats AND houses
    python -m scraper.rcncheck Gliwice --ulica "Adama Asnyka" --nr 11

    # widen the area net / houses with a plot
    python -m scraper.rcncheck Zabrze 55 --tol 2
    python -m scraper.rcncheck Pyskowice 141.5 --typ house --dzialka 800

    # pin the learned address to a listing -> next pipeline run matches it
    python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --nr 11 --pin URL
"""
from __future__ import annotations

import argparse
import pathlib

from . import overrides as ovmod
from . import rcn

RCN_CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache" / "rcn_snapshot.json.gz"


def _row_line(r, typ):
    addr = "; ".join(str(x) for x in (r.get("msc"), r.get("ul"), r.get("nr")) if x)
    area = f"{r['a']:>7} m²" if r.get("a") is not None else "   ?  m²"
    extra = (f"izb {r.get('izb')} kond {r.get('kond')}" if typ == "flat"
             else f"działka {r.get('grunt')}")
    return f"{r['d']}  {r['c']:>10,} zł  {area}  rynek {r.get('rynek') or '?'}  {extra}  | {addr}"


def _search(rows, town, args):
    out = []
    for r in rows:
        if rcn._fold(r.get("msc")) != town:
            continue
        if args.powierzchnia is not None:
            if r.get("a") is None or abs(r["a"] - args.powierzchnia) > args.tol:
                continue
        if args.ulica:
            if not (r.get("ul") and rcn.street_match(args.ulica, r["ul"])):
                continue
        if args.nr:
            if not (r.get("nr") and rcn._fold(str(r["nr"])) == rcn._fold(args.nr)):
                continue
        out.append(r)
    return sorted(out, key=lambda x: x["d"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("miejscowosc")
    ap.add_argument("powierzchnia", type=float, nargs="?", default=None,
                    help="m² (optional when searching by address)")
    ap.add_argument("--typ", choices=("flat", "house", "oba"), default=None,
                    help="default: oba when searching by address, flat otherwise")
    ap.add_argument("--ulica")
    ap.add_argument("--nr", help="building number (e.g. 11, 102G)")
    ap.add_argument("--pokoje", type=int)
    ap.add_argument("--pietro", type=int)
    ap.add_argument("--dzialka", type=float, help="plot m2 (houses)")
    ap.add_argument("--tol", type=float, default=rcn.AREA_TOL,
                    help=f"area tolerance in m2 (default {rcn.AREA_TOL})")
    ap.add_argument("--pin", metavar="LISTING_URL",
                    help="save these details to overrides.json for this "
                         "listing URL; the pipeline uses them on every run")
    args = ap.parse_args(argv)

    if args.powierzchnia is None and not (args.ulica or args.nr):
        ap.error("podaj powierzchnię albo --ulica/--nr (adres)")

    snap = rcn.load_snapshot(RCN_CACHE)
    if not snap:
        print(f"Brak snapshotu RCN ({RCN_CACHE}). Uruchom najpierw scraper "
              f"(python -m scraper.main) lub pobierz cache z repo.")
        return 1

    typ = args.typ or ("flat" if args.powierzchnia is not None and not args.nr else "oba")
    town = rcn._fold(args.miejscowosc)
    what = [] if args.powierzchnia is None else [f"{args.powierzchnia} m² (±{args.tol})"]
    if args.ulica:
        what.append(f"ul. {args.ulica}" + (f" {args.nr}" if args.nr else ""))
    print(f"RCN snapshot z {snap.get('fetched')} — {args.miejscowosc}, "
          + ", ".join(what) + "\n")

    shown = 0
    for t, key, label in (("flat", "lokale", "LOKALE (mieszkania)"),
                          ("house", "budynki", "BUDYNKI (domy)")):
        if typ not in (t, "oba"):
            continue
        cands = _search(snap.get(key) or [], town, args)
        if typ == "oba" and not cands:
            continue
        print(f"-- {label}: {len(cands)} transakcji")
        rec = {"type": t, "area": args.powierzchnia,
               "snapshot": {"locality": args.miejscowosc, "street": args.ulica,
                            "nr": args.nr, "rooms": args.pokoje,
                            "floor": args.pietro, "plot_area": args.dzialka}}
        unique = len(cands) == 1
        for r in cands:
            conf, ok = rcn._score(rec, rec["snapshot"], r, t == "flat", unique=unique)
            mark = ("✓ wysoka" if (ok and conf == 2)
                    else "✓ średnia" if ok else "  -")
            print(f"{mark}  {_row_line(r, t)}")
            shown += 1
        print()
    if not shown:
        print("Nic — brak aktu notarialnego dla tych kryteriów.\n"
              "Spróbuj --tol 2, sam adres bez powierzchni (--ulica/--nr), albo\n"
              "sprawdź nazwę miejscowości (rejestr używa nazw urzędowych).")

    if args.pin:
        entry = ovmod.pin(args.pin, street=args.ulica, nr=args.nr,
                          locality=args.miejscowosc, rooms=args.pokoje,
                          floor=args.pietro, plot_area=args.dzialka)
        print(f"\nPrzypięto do {args.pin}:\n  {entry}\n"
              f"(zapisane w overrides.json — zacommituj plik; od następnego "
              f"przebiegu scraper dopasuje ten adres automatycznie)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
