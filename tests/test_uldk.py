"""ULDK/UUG parsing with a fake HTTP session (offline)."""
from scraper import uldk


class _Resp:
    def __init__(self, payload, is_json):
        self._p, self._j = payload, is_json
        self.text = payload if not is_json else ""

    def raise_for_status(self): pass

    def json(self): return self._p


class _Sess:
    def __init__(self, responses): self.responses = list(responses)

    def get(self, url, **kw): return self.responses.pop(0)


UUG_OK = {"results": {"1": {"street": "Ignacego Daszyńskiego", "number": "448",
                            "teryt": "246601", "x": "471141.63", "y": "268339.91"}}}


def test_resolve_full_chain():
    sess = _Sess([_Resp(UUG_OK, True),
                  _Resp("0\n246601_1.0041.1506|Ostropa Północ|1506", False)])
    out = uldk.resolve("Gliwice", "Daszyńskiego", "448", session=sess)
    assert out["street"] == "Ignacego Daszyńskiego"
    assert out["dzialka_id"] == "246601_1.0041.1506"
    assert out["obreb"] == "Ostropa Północ"


def test_resolve_rejects_wrong_building_number():
    wrong = {"results": {"1": {"street": "X", "number": "12", "teryt": "1",
                               "x": "1", "y": "2"}}}
    sess = _Sess([_Resp(wrong, True)])
    out = uldk.resolve("Gliwice", "X", "448", session=sess)
    assert out["dzialka_id"] is None and "note" in out


def test_resolve_handles_no_results():
    sess = _Sess([_Resp({"results": None}, True)])
    assert uldk.resolve("Nigdzie", "Zadna", "1", session=sess) is None
