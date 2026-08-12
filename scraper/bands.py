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

import time
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

# Pacing between searches, as multiples of the caller's between-page delay
# (0.7 s in CI). `time.sleep(delay)` inside every portal's page loop paces the
# pages *within* one search and nothing at all paces one search against the
# next — so a subdivision fires its whole queue of bands at a portal back to
# back, which is precisely when a portal stops answering. Otodom 405'd at band
# `300k-400k` page 5 and refused the next seven bands on page 1 before serving
# the eighth (runs 31408840562, 31422141701); a search is a burst of requests,
# so the gap after one has to be wider than the gap between two pages, and the
# gap after a refusal wider still. `delay=0` (tests, dev) disables both.
SEARCH_PAUSE = 4       # x delay -> 2.8 s between searches
ERROR_COOLDOWN = 40    # x delay -> 28 s after a search the portal refused

# ...and a refused search is waited out at most this many times per portal per
# run. A portal that is refusing everything refuses the retries too, and one
# cooldown per refusal would turn an outage into an hour of sleeping: otodom
# walks ~25 bands x 2 types and OLX ~120 towns, against a 350-min CI cap that
# already has no headroom. 10 x 28 s caps it at ~5 min per portal.
MAX_COOLDOWNS = 10


class Pacer:
    """Between-search pacing, and a bounded "wait it out and ask once more".

    One per portal per run, shared by that portal's unbanded search, its town
    searches and every subdivision — so the waiting is budgeted across all of
    them rather than per subdivision, which is what keeps a portal-wide outage
    from spending the run's slack on sleep.
    """

    def __init__(self, source, delay=0.0, log=print, sleep=time.sleep,
                 max_cooldowns=MAX_COOLDOWNS):
        self.source = source
        self.delay = delay
        self.log = log
        self.sleep = sleep
        self.left = max_cooldowns

    def pause(self):
        """The gap between two searches — wider than the gap between pages."""
        self.sleep(self.delay * SEARCH_PAUSE)

    def attempt(self, tag, walk):
        """Walk one search; if the portal refused it outright, ask once more.

        Exactly ONE row comes back, so a recovered search is never counted
        twice by `check_totals`, and it is the better of the two attempts —
        see `best_of`. Never a loop, never unbudgeted.
        """
        row = walk()
        if row.get("stopped") != coverage.ERROR:
            return row
        if self.left <= 0:
            self.log(f"  {self.source} {tag} was refused — no retry budget left "
                     f"this run, moving on")
            return row
        self.left -= 1
        wait = self.delay * ERROR_COOLDOWN
        self.log(f"  {self.source} {tag} was refused — waiting {wait:.0f}s and "
                 f"asking once more ({self.left} more waits left this run)")
        self.sleep(wait)
        return best_of(row, walk())


def _reach(r) -> tuple:
    """How far an attempt actually got, most significant first."""
    return (r.get("pages") or 0, coverage.seen_by(r) or 0,
            r.get("portal_total") or 0)


def best_of(first, retry):
    """The better record of two attempts at the same search.

    A retry restarts at page 1, so "the last one wins" quietly throws away
    whatever the first attempt had already learned. Otodom's `300k-400k` walked
    to page ELEVEN before it was refused; the retry was refused on page 1, and
    that 1-page row replaced it — so the run reported `failed after 1 page(s)`
    for a search that walked eleven, and `check_totals` lost the 46-page total
    the first attempt had read off the portal, dropping the accounted ads from
    6 821 to 3 529 and blaming otodom's price filter for it (run 31502042693).
    The listings themselves were never at risk — the walkers merge into the
    caller's `seen`/`out` as they go — but every number *about* the search was.

    A recovered walk always wins; between two refusals, the one that got
    further does.
    """
    if retry.get("stopped") != coverage.ERROR:
        return retry
    if first.get("stopped") != coverage.ERROR:
        return first
    return retry if _reach(retry) > _reach(first) else first


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


def subdivide(source, walk, log=print, edges=SEED_EDGES, max_depth=MAX_DEPTH,
              delay=0.0, sleep=time.sleep, pacer=None):
    """Walk `source` in price bands until nothing overflows. Returns the rows.

    ``walk(lo, hi, tag)`` runs one full paginated search over the half-open
    band and returns its coverage row; the caller owns merging (by URL, into
    whatever `seen` set it already used for the unbanded search).

    Pacing and retries go through `Pacer` (see there): searches are spaced
    apart, and a band the portal refused outright is walked once more after a
    cooldown. Pass the portal's own `pacer` so its unbanded search, its towns
    and its bands share one retry budget; without one, a private Pacer is built
    from `delay`.
    """
    pacer = pacer or Pacer(source, delay=delay, log=log, sleep=sleep)
    rows, seeds = [], []
    queue = deque((lo, hi, 0) for lo, hi in seed_bands(edges))
    while queue:
        lo, hi, depth = queue.popleft()
        tag = label(lo, hi)
        pacer.pause()
        row = pacer.attempt(f"band {tag}", lambda: walk(lo, hi, tag))
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
