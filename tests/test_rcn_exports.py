"""Official export fallback, using fictional Parquet files and no network."""
import datetime as dt
import hashlib
import io

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import requests

from scraper import rcn, rcn_exports


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    monkeypatch.setattr(rcn_exports.time, "sleep", lambda seconds: None)


def _row(layer="lokale", **changes):
    props = rcn.LOK_PROPS if layer == "lokale" else rcn.BUD_PROPS
    row = dict.fromkeys(props.split(","), None)
    row.update(gid=1, teryt="1601", dok_data=dt.date(2026, 1, 2),
               tran_rodzaj_trans="wolnyRynek", tran_rodzaj_rynku="rynekWtorny",
               tran_cena_brutto=200000., lok_pow_uzyt=40.,
               lok_funkcja="mieszkalna", bud_rodzaj="mieszkalny")
    row = {k: v for k, v in row.items() if k == "gid" or k in props.split(",")}
    row.update(changes)
    return row


def _parquet(rows):
    output = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), output)
    return output.getvalue()


class Session:
    def __init__(self, files, declared=None):
        self.files, self.declared, self.urls = files, declared, []

    def get(self, url, **kwargs):
        self.urls.append(url)
        layer = "lokale" if "lokale.parquet" in url else "budynki"
        data = self.files[layer]
        class Response:
            headers = {"Content-Length": str(len(data) if self.declared is None else self.declared)}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def raise_for_status(self): pass
            def iter_content(self, size): yield data
        return Response()


def _session(lok=None, bud=None, **kw):
    return Session({"lokale": _parquet(lok or [_row()]),
                    "budynki": _parquet(bud or [_row("budynki")])}, **kw)


def test_complete_exports_read_dates_scope_and_residential_buildings():
    session = _session(lok=[_row(), _row(gid=2)],
                       bud=[_row("budynki"), _row("budynki", gid=2, bud_rodzaj="inny")])
    lok, bud, source = rcn_exports.fetch_exports(session, "16", log=lambda *a: None)
    assert len(lok) == 2 and len(bud) == 1  # distinct IDs survive identical compact values
    assert lok[0]["d"] == "2026-01-02" and lok[0]["rynek"] == "w"
    rcn.validate_snapshot({"fetched": "2026-10-17", "lokale": lok, "budynki": bud})
    assert source["kind"] == "gugik_exports"
    assert source["files"]["budynki"]["rows"] == 2
    assert len(source["files"]["lokale"]["sha256"]) == 64
    assert all("16_transakcje_ceny_" in url for url in session.urls)


@pytest.mark.parametrize("changes,reason", [
    ({"teryt": "2401"}, "TERYT"), ({"teryt": None}, "TERYT"),
    ({"gid": None}, "feature ID"), ({"gid": -1}, "feature ID"),
    ({"dok_data": None}, "unusable"), ({"tran_rodzaj_rynku": "unsupported"}, "market"),
])
def test_bad_export_rows_are_rejected(changes, reason):
    with pytest.raises(ValueError, match=reason):
        rcn_exports.fetch_exports(_session(lok=[_row(**changes)]), "16")


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate feature ID"):
        rcn_exports.fetch_exports(_session(lok=[_row(), _row()]), "16")


def test_missing_fields_are_rejected():
    row = _row()
    del row["lok_pow_uzyt"]
    with pytest.raises(ValueError, match="missing or ambiguous fields"):
        rcn_exports.fetch_exports(_session(lok=[row]), "16")


def test_truncated_parquet_is_rejected():
    with pytest.raises(pa.ArrowInvalid, match="Parquet"):
        rcn_exports.fetch_exports(Session({"lokale": _parquet([_row()])[:-20]}), "16")


def test_interrupted_download_is_rejected():
    with pytest.raises(ValueError, match="interrupted download"):
        rcn_exports.fetch_exports(_session(declared=999999), "16")


def test_oversize_download_is_rejected(monkeypatch):
    monkeypatch.setattr(rcn_exports, "MAX_EXPORT_BYTES", 1)
    with pytest.raises(ValueError, match="download size"):
        rcn_exports.fetch_exports(_session(), "16")


def test_invalid_region_makes_no_request():
    session = _session()
    with pytest.raises(ValueError, match="TERYT"):
        rcn_exports.fetch_exports(session, "../24")
    assert not session.urls


def test_wfs_failure_uses_two_complete_export_layers(monkeypatch):
    def broken(*a, **kw):
        raise ValueError("changing/inconsistent total (89176 -> 351)")
    monkeypatch.setattr(rcn, "fetch", broken)
    details = {}
    lok, bud = rcn.fetch_all(_session(), "16", details=details)
    assert lok and bud and details["kind"] == "gugik_exports"
    assert "inconsistent total" in details["wfs_error"]


def test_failed_second_export_preserves_previous_cache(tmp_path, monkeypatch):
    def broken(*a, **kw): raise ValueError("broken WFS")
    monkeypatch.setattr(rcn, "fetch", broken)
    path = tmp_path / "rcn.gz"
    lok = rcn._compact_lok({k: str(v) if v is not None else "" for k, v in _row().items()})
    previous = {"fetched": "2026-09-28", "lokale": [lok], "budynki": [lok]}
    rcn.save_snapshot(path, previous)
    original = path.read_bytes()
    session = Session({"lokale": _parquet([_row()]), "budynki": b"broken parquet"})
    assert rcn.refresh(path, session, "16", today="2026-10-17") == previous
    assert path.read_bytes() == original and rcn.refresh.last_health["status"] == "degraded"


def test_export_source_persists_across_cached_refresh(tmp_path, monkeypatch):
    def broken(*a, **kw): raise ValueError("broken WFS")
    monkeypatch.setattr(rcn, "fetch", broken)
    path = tmp_path / "rcn.gz"
    candidate = rcn.refresh(path, _session(), "16", today="2026-10-17")
    assert candidate["source"]["kind"] == "gugik_exports"
    assert rcn.refresh.last_health["source"] == candidate["source"]
    assert rcn.refresh(path, None, "16", today="2026-10-17") == candidate
    assert rcn.refresh.last_health["source"] == candidate["source"]


def test_shrunken_complete_export_cannot_replace_cache(tmp_path, monkeypatch):
    def broken(*a, **kw): raise ValueError("broken WFS")
    monkeypatch.setattr(rcn, "fetch", broken)
    path = tmp_path / "rcn.gz"
    lok = {"d": "2026-01-02", "c": 200000, "a": 40, "rynek": "w"}
    previous = {"fetched": "2026-09-28", "lokale": [lok] * 10, "budynki": [lok] * 10}
    rcn.save_snapshot(path, previous)
    original = path.read_bytes()
    assert rcn.refresh(path, _session(), "16", today="2026-10-17") == previous
    assert path.read_bytes() == original
    assert "20%" in rcn.refresh.last_health["error"]


@pytest.mark.parametrize("failure", [
    requests.ConnectTimeout, requests.ReadTimeout, requests.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
])
def test_transient_download_restarts_with_clean_bytes_and_hash(tmp_path, failure):
    good = _session()

    class Interrupted:
        calls = 0
        def get(self, url, **kwargs):
            self.calls += 1
            assert kwargs["timeout"] == (10, 120)
            if self.calls == 1 and failure is requests.ConnectTimeout:
                raise failure("connection timed out")
            response = good.get(url, **kwargs)
            if self.calls == 1:
                def stream(size):
                    yield b"partial bytes that must be discarded"
                    raise failure("stream interrupted")
                response.iter_content = stream
            return response

    session = Interrupted()
    path = tmp_path / "layer.parquet"
    size, digest = rcn_exports._download(session, "https://example.test/lokale.parquet",
                                         path, log=lambda *a: None)
    assert session.calls == 2
    assert path.read_bytes() == good.files["lokale"]
    assert size == len(good.files["lokale"])
    assert digest == hashlib.sha256(good.files["lokale"]).hexdigest()


def test_exhausted_second_layer_timeouts_retain_cache(tmp_path, monkeypatch):
    def broken(*a, **kw):
        raise ValueError("bad WFS")
    monkeypatch.setattr(rcn, "fetch", broken)
    path = tmp_path / "cache.gz"
    tx = {"d": "2026-01-02", "c": 200000, "a": 40, "rynek": "w"}
    previous = {"fetched": "2026-09-28", "lokale": [tx], "budynki": [tx]}
    rcn.save_snapshot(path, previous)
    original = path.read_bytes()
    good = _session()

    class Unavailable:
        attempts = 0
        def get(self, url, **kw):
            if "budynki.parquet" in url:
                self.attempts += 1
                raise requests.ConnectTimeout("export host unreachable")
            return good.get(url, **kw)

    session = Unavailable()
    assert rcn.refresh(path, session, "16", today="2026-10-21") == previous
    assert session.attempts == 3
    assert path.read_bytes() == original
    assert rcn.refresh.last_health["status"] == "degraded"
    assert rcn.refresh.last_health["fetched"] == "2026-09-28"


def test_permanent_http_error_is_not_retried(tmp_path):
    class Missing:
        calls = 0
        def get(self, *a, **kw):
            self.calls += 1
            raise requests.HTTPError("404 missing export")
    session = Missing()
    with pytest.raises(requests.HTTPError):
        rcn_exports._download(session, "https://example.test/lokale.parquet",
                             tmp_path / "layer.parquet", log=lambda *a: None)
    assert session.calls == 1
