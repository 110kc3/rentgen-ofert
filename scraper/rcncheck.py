"""Check one specific property against the RCN transaction register.

Looks up notarial deeds in the cached snapshot (cache/rcn_snapshot.json.gz,
pulled by the main scraper) for a town + area, optionally narrowed by street,
rooms, floor or plot size — and shows which deeds the automatic matcher would
accept and with what confidence.

Examples (run from the repo root):

    python -m scraper.rcncheck Gliwice 48.63
    python -m scraper.rcncheck Gliwice 48.63 --ulica Asnyka --pokoje 2
    python -m scraper.rcncheck Pyskowice 141.5 --typ house --dzialka 800
    python -m scraper.rcncheck Zabrze 55 --tol 2       # widen the area net
"""
from __future__ import annotations

import argparse
import pathlib

from . import rcn

RCN_CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache" / "rcn_snapshot.json.gz"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("miejscowosc")
    ap.add_argument("powierzchnia", type=float)
    ap.add_argument("--typ", choices=("flat", "house"), default="flat")
    ap.add_argument("--ulica")
    ap.add_argument("--pokoje", type=int)
    ap.add_argument("--pietro", type=int)
    ap.add_argument("--dzialka", type=float, help="plot m2 (houses)")
    ap.add_argument("--tol", type=float, default=rcn.AREA_TOL,
                    help=f"area tolerance in m2 (default {rcn.AREA_TOL})")
    args = ap.parse_args(argv)

    snap = rcn.load_snapshot(RCN_CACHE)
    if not snap:
        print(f"Brak snapshotu RCN ({RCN_CACHE}). Uruchom najpierw scraper "
              f"(python -m scraper.main) lub pobierz cache z repo.")
        return 1
    rows = snap["lokale"] if args.typ == "flat" else snap["budynki"]
    town = rcn._fold(args.miejscowosc)
    cands = [r for r in rows
             if rcn._fold(r.get("msc")) == town
             and abs(r["a"] - args.powierzchnia) <= args.tol]
    print(f"RCN snapshot z {snap.get('fetched')}: {len(cands)} transakcji "
          f"{args.miejscowosc}, {args.powierzchnia} m² (±{args.tol})\n")

    rec = {"type": args.typ, "area": args.powierzchnia,
           "snapshot": {"locality": args.miejscowosc, "street": args.ulica,
                        "rooms": args.pokoje, "floor": args.pietro,
                        "plot_area": args.dzialka}}
    unique = len(cands) == 1
    for r in sorted(cands, key=lambda x: x["d"]):
        conf, ok = rcn._score(rec, rec["snapshot"], r, args.typ == "flat",
                              unique=unique)
        mark = ("✓ wysoka" if (ok and conf == 2)
                else "✓ średnia" if ok else "  -")
        addr = "; ".join(filter(None, [r.get("msc"), r.get("ul"), r.get("nr")]))
        extra = (f"izb {r.get('izb')} kond {r.get('kond')}" if args.typ == "flat"
                 else f"działka {r.get('grunt')}")
        print(f"{mark}  {r['d']}  {r['c']:>10,} zł  {r['a']:>7} m²  "
              f"rynek {r.get('rynek') or '?'}  {extra}  | {addr}")
    if not cands:
        print("Nic — brak aktu notarialnego dla tej wielkości w tej miejscowości\n"
              "(rejestr sięga ~2010 r.; spróbuj --tol 2 albo sprawdź nazwę miejscowości).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
