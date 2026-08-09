"""Price-band subdivision: see past the window a portal will actually serve.

Every paginated portal hands over far less than it admits to holding. Measured
on śląskie, 2026-08-08, portal's own stated count vs the most one search can
ever return:

    otodom    18 505 flats, 515 pages   full depth answers, but pages past ~150
                                        come back thin and erratic (page 300 ->
                                        4 items, 490 -> 1), so deep pagination
                                        is not a way to enumerate anything
    gratka     9 856 flats              hard 404 past page 200 (bisected: 200
    morizon   ~9 000 flats              OK, 201 404) -> 7 000 ads, ever
    olx        5 503 visible            serves 1 000 (`totalElements`), and
                                        states the cap as a smaller total

The fix has to be something all four accept, because their location taxonomies
never will: otodom nests region/powiat/gmina/city while the others take one
flat slug. Price is the one axis every portal filters on, and each one's
parameter was verified by probe (see PARAMS below).

**Contract.** The unbanded search runs FIRST and is kept — priceless ads, and
anything a portal's own price filter quietly drops, are only ever visible
there. Then, while a search's stated total exceeds the window its portal will
serve, its price range is bisected and the halves are walked. Everything merges
by URL into the caller's `seen` set, so this is purely additive, exactly like
the OLX town subdivision: a bad band costs one request and can never lose a
listing already held.

Bands are half-open ``[lo, hi)`` — the portals' filters are inclusive on both
ends, so the upper bound is passed as ``hi - 1`` and an ad priced exactly on a
boundary lands in exactly one band. `check_totals` then asserts the bands sum
to at least the unbanded total and says so when they don't, which is how a
portal's price filter silently dropping ads gets caught.
"""
from __future__ import annotations

from collections import deque

from . import coverage

# The most ads one search of this portal can ever hand over. Measured, not
# assumed — see the module docstring.
WINDOW = {
    "otodom": 7_200,     # ~100 pages x 72/page before the results go erratic
    "gratka": 7_000,     # 200-page 404 wall x 35/page
    "morizon": 7_000,    # same frontend, same wall
    "olx": 1_000,        # `totalElements`, the cap it states as a total
}

# Price-filter parameters, one probe each (2026-08-08):
#   otodom   ?priceMin=300000&priceMax=400000        -> 3 348 items / 93 pages
#   gratka   ?cena-calkowita:min=200000&…:max=300000 -> 1 209 ogłoszeń
#   morizon  ?ps[price_from]=200000&ps[price_to]=…   -> 1 000 ogłoszeń
#   olx      ?search[filter_float_price:from|to]     -> 575 = visibleElements
PARAMS = {
    "otodom":  ("priceMin", "priceMax"),
    "gratka":  ("cena-calkowita:min", "cena-calkowita:max"),
    "morizon": ("ps[price_from]", "ps[price_to]"),
    "olx":     ("search[filter_float_price:from]", "search[filter_float_price:to]"),
}

# Seed cut points, in PLN. Chosen so no band holds a disproportionate share of a
# Polish voivodeship's stock; bands that still overflow get bisected from here,
# so these only have to be roughly right, not optimal.
SEED_EDGES = (200_000, 300_000, 400_000, 500_000, 650_000,
              800_000, 1_000_000, 1_500_000, 3_000_000)

MIN_BAND = 10_000      # stop bisecting: below this a band is one price point
MAX_DEPTH = 3          # 9 seed bands -> at most 8 extra cuts each


def params(source, lo, hi) -> dict:
    """Query parameters selecting the half-open band ``[lo, hi)``."""
    keys = PARAMS.get(source)
    if not keys:
        return {}
    lo_key, hi_key = keys
    out = {}
    if lo:
        out[lo_key] = str(int(lo))
    if hi:
        out[hi_key] = str(int(hi) - 1)   # inclusive filter, half-open band
    return out


def qs(source, lo, hi) -> str:
    """Band parameters as a query fragment, e.g. 'priceMin=300000&priceMax=399999'.

    Built by hand, not urlencode: gratka's parameter names contain ':' and
    morizon's contain '[]', and those were verified literal against the live
    portals. The values are integers, so nothing here needs escaping.
    """
    return "&".join(f"{k}={v}" for k, v in params(source, lo, hi).items())


def label(lo, hi) -> str:
    """Short band name for logs and coverage rows: '300k-400k', '3M+'."""
    def short(v):
        if v is None:
            return ""
        if v >= 1_000_000 and v % 1_000_000 == 0:
            return f"{v // 1_000_000}M"
        return f"{v // 1000}k" if v >= 1000 else str(v)
    if hi is None:
        return f"{short(lo)}+"
    return f"{short(lo)}-{short(hi)}"


def seed_bands(edges=SEED_EDGES):
    """The seed partition of the whole price line, as half-open [lo, hi)."""
    bounds = (0,) + tuple(edges)
    return [(lo, hi) for lo, hi in zip(bounds, bounds[1:] + (None,))]


def bisect(lo, hi):
    """Split a band in two, or None when it is already too narrow to divide."""
    if hi is None:
        # open-topped band: cut geometrically so it terminates
        mid = max((lo or 0) * 2, (lo or 0) + 1_000_000)
    else:
        if hi - lo <= MIN_BAND:
            return None
        mid = (lo + hi) // 2
    return ((lo, mid), (mid, hi))


# Reasons to ask a narrower question. Deliberately NOT coverage.ERROR: a
# request that failed will fail the same way with a price filter on it, and
# treating it as overflow makes one broken search recurse into dozens.
CAPPED = (coverage.OUR_CAP, coverage.PORTAL_CAP)


def overflows(row, source) -> bool:
    """Is this search still bigger than its portal will serve?

    Either the portal says so outright (`portal_total` past the window) or the
    walk hit a cap. Neither is trustworthy alone, which is the whole lesson of
    `coverage`.
    """
    window = WINDOW.get(source)
    total = row.get("portal_total")
    if window and total and total > window:
        return True
    return row.get("stopped") in CAPPED


def subdivide(source, walk, log=print, edges=SEED_EDGES, max_depth=MAX_DEPTH):
    """Walk `source` in price bands until nothing overflows. Returns the rows.

    ``walk(lo, hi, tag)`` runs one full paginated search over the half-open
    band and returns its coverage row; the caller owns merging (by URL, into
    whatever `seen` set it already used for the unbanded search).
    """
    rows, seeds = [], []
    queue = deque((lo, hi, 0) for lo, hi in seed_bands(edges))
    while queue:
        lo, hi, depth = queue.popleft()
        row = walk(lo, hi, label(lo, hi))
        rows.append(row)
        if depth == 0:
            seeds.append(row)
        if depth >= max_depth or not overflows(row, source):
            continue
        halves = bisect(lo, hi)
        if halves is None:
            log(f"  !! {source} band {label(lo, hi)} still overflows and cannot "
                f"be split further — {row.get('portal_total')} ads at one price")
            continue
        queue.extend((a, b, depth + 1) for a, b in halves)
    return rows, seeds


def check_totals(source, typ, unbanded_total, seeds, log=print) -> bool:
    """Do the seed bands account for the whole unbanded search?

    The seeds partition the price line exactly once, so their stated totals
    should sum to at least the unbanded total. Coming up short means the
    portal's price filter is dropping ads that the unfiltered search shows —
    worth knowing, and invisible without the arithmetic.
    """
    if not unbanded_total:
        return True
    banded = sum(r.get("portal_total") or 0 for r in seeds)
    if banded >= unbanded_total:
        return True
    log(f"  !! {source} {typ}: price bands account for {banded} ads but the "
        f"unbanded search states {unbanded_total} — {unbanded_total - banded} "
        f"ads match no band (portal price filter dropping them?)")
    return False
