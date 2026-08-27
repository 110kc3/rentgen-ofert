"""geo: EPSG:2180 -> WGS84 transform, geocode cache, listing attach. Offline."""
import json

from scraper import geo

TODAY = "2026-07-07"


def test_to_wgs84_known_points():
    # UUG-returned points for places with well-known WGS84 positions
    lat, lon = geo.to_wgs84(475336.0325, 270285.1244)     # Gliwice centroid
    assert abs(lat - 50.299) < 0.005 and abs(lon - 18.654) < 0.005
    lat, lon = geo.to_wgs84(496693.2134, 186859.4546)     # Koniaków
    assert abs(lat - 49.549) < 0.005 and abs(lon - 18.954) < 0.005


class FakeResp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    """Returns a street hit for 'Gliwice, Polna', a town hit for 'Gliwice',
    and a miss for anything else. Counts calls."""
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, **kw):
        addr = params["address"]
        self.calls.append(addr)
        if addr == "Gliwice, Polna":
            return FakeResp({"results": {"1": {
                "street": "Polna", "teryt": "246601",
                "x": "476458.9563", "y": "269949.1121"}}})
        if addr == "Gliwice":
            return FakeResp({"results": {"1": {
                "street": None, "teryt": "246601",
                "x": "475336.0325", "y": "270285.1244"}}})
        return FakeResp({"results": None})


def _listing(loc="Gliwice", street=None):
    l = {"locality": loc}
    if street:
        l["street"] = street
    return l


def test_attach_precision_and_fallback():
    ls = [_listing(street="Polna"), _listing(), _listing("Wymyślin")]
    cache = {}
    s = FakeSession()
    new, located = geo.attach(ls, cache, s, today=TODAY, max_new=99, delay=0,
                              teryt_prefix="24")
    assert located == 2
    assert ls[0]["llp"] == "s" and ls[1]["llp"] == "t"
    assert ls[0]["ll"] != ls[1]["ll"]
    assert "ll" not in ls[2]
    assert cache["24|wymyslin"]["ll"] is None         # regional miss cached
    # towns are looked up before streets
    assert s.calls.index("Gliwice") < s.calls.index("Gliwice, Polna")

    # second run: everything cached, no new lookups, misses not retried yet
    s2 = FakeSession()
    new2, located2 = geo.attach(ls, cache, s2, today=TODAY, max_new=99, delay=0,
                                teryt_prefix="24")
    assert new2 == 0 and s2.calls == [] and located2 == 2


def test_miss_retried_after_expiry():
    cache = {"24|wymyslin": {"ll": None, "d": "2026-01-01"}}  # expired
    s = FakeSession()
    geo.attach([_listing("Wymyślin")], cache, s, today=TODAY,
               max_new=99, delay=0, teryt_prefix="24")
    assert s.calls == ["Wymyślin"]


def test_budget_cap():
    ls = [_listing("Gliwice"), _listing("Wymyślin")]
    s = FakeSession()
    new, _ = geo.attach(ls, cache={}, session=s, today=TODAY, max_new=1,
                        delay=0, teryt_prefix="24")
    assert new == 1 and len(s.calls) == 1


def test_cache_roundtrip(tmp_path):
    p = tmp_path / "geo.json"
    geo.save(p, {"24|gliwice": {"ll": [50.3, 18.65], "p": "t", "d": TODAY}})
    assert geo.load(p)["24|gliwice"]["ll"] == [50.3, 18.65]
    assert geo.load(tmp_path / "missing.json") == {}


class AmbiguousSession:
    """The service's first textual match is deliberately in the wrong region."""
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, **kw):
        self.calls.append(params["address"])
        return FakeResp({"results": {
            "1": {"teryt": "066301", "street": None,
                  "x": "750000", "y": "400000"},
            "2": {"teryt": "247501", "street": None,
                  "x": "475336.0325", "y": "270285.1244"},
            "3": {"teryt": "126101", "street": None,
                  "x": "560000", "y": "245000"},
        }})


def test_lookup_selects_candidate_by_teryt_prefix():
    entry = geo._lookup(AmbiguousSession(), "Sosnowiec", None, TODAY,
                        teryt_prefix="24")
    assert entry["teryt"] == "247501"
    assert entry["ll"] == list(geo.to_wgs84(475336.0325, 270285.1244))


def test_cache_keys_isolate_same_named_places_between_regions():
    cache = {}
    session = AmbiguousSession()
    slaskie = [_listing("Sosnowiec")]
    malopolskie = [_listing("Sosnowiec")]
    geo.attach(slaskie, cache, session, today=TODAY, max_new=5, delay=0,
               teryt_prefix="24")
    geo.attach(malopolskie, cache, session, today=TODAY, max_new=5, delay=0,
               teryt_prefix="12")
    assert cache["24|sosnowiec"]["teryt"].startswith("24")
    assert cache["12|sosnowiec"]["teryt"].startswith("12")
    assert slaskie[0]["ll"] != malopolskie[0]["ll"]


def test_no_candidate_in_requested_region_is_cached_as_a_miss():
    entry = geo._lookup(AmbiguousSession(), "Sosnowiec", None, TODAY,
                        teryt_prefix="32")
    assert entry == {"ll": None, "d": TODAY}
