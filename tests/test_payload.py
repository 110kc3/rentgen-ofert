"""Payload split: slim index + detail shards + manifest (offline)."""
import json
import shutil
import subprocess

from scraper import payload


def _listing(url="https://otodom.pl/pl/oferta/x-1", **kw):
    base = dict(
        title="Mieszkanie", type="flat", area=50.0, rooms=2, locality="Gliwice",
        street="Asnyka", floor="1", agency="Biuro X", market="secondary",
        image="https://img/1.jpg", price=400000, price_per_m2=8000,
        url=url, source="otodom", sources=["otodom", "olx"],
        offers=[{"source": "otodom", "url": url, "price": 400000},
                {"source": "olx", "url": "https://olx.pl/y", "price": 390000}],
        cheapest={"source": "olx", "url": "https://olx.pl/y", "price": 390000},
        timeline=[{"date": "2026-06-01", "kind": "listed"},
                  {"date": "2026-06-05", "kind": "price", "price": 390000}],
        photo_urls=["https://img/a.jpg"],
        price_history=[{"date": "2026-06-01", "price": 400000}],
        sales=[{"date": "2021-01-01", "kind": "past", "price": 300000,
                "confidence": "wysoka", "addr": "Asnyka 11", "dz": "246601_1.0041.1"}],
        also_listed=[{"price": 410000, "url": "https://x", "source": "gratka"}],
        first_seen="2026-06-01", relisted=False,
    )
    base.update(kw)
    return base


def test_build_splits_index_and_shards(tmp_path):
    ls = [_listing(), _listing(url="https://olx.pl/d/oferta/z-2.html", sales=None)]
    v = payload.build(ls, tmp_path, shards=4, log=lambda *a: None)
    mf = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert mf == {"v": v, "shards": 4, "count": 2}
    idx = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(idx) == 2
    slim = idx[0]
    # heavy/expand-only fields are NOT in the index …
    for k in ("offers", "cheapest", "timeline", "photo_urls", "street", "agency"):
        assert k not in slim
    # … but their face summaries are
    assert slim["offers_n"] == 2 and slim["tl_n"] == 2 and slim["ph_n"] == 1
    assert slim["sales"] == [{"kind": "past", "date": "2021-01-01",
                              "price": 300000, "confidence": "wysoka"}]  # no addr/dz
    assert slim["also_listed"] == [{"price": 410000}]
    assert slim["price_history"] == [{"date": "2026-06-01", "price": 400000}]
    # the shard carries the full detail record under the listing URL
    found = {}
    for i in range(4):
        found.update(json.loads((tmp_path / "d" / f"{i:02d}.json").read_text(encoding="utf-8")))
    det = found["https://otodom.pl/pl/oferta/x-1"]
    assert len(det["offers"]) == 2 and det["street"] == "Asnyka"
    assert det["sales"][0]["addr"] == "Asnyka 11"
    assert payload.shard_of("https://otodom.pl/pl/oferta/x-1", 4) in range(4)


def test_shard_hash_matches_js_implementation():
    """scraper/payload.py and site/app.js MUST shard identically."""
    if not shutil.which("node"):
        return  # environment without node — python side alone is deterministic
    urls = ["https://otodom.pl/pl/oferta/mieszkanie-m3-ID4abc",
            "https://www.olx.pl/d/oferta/dom-CID3-ID18kaq1.html",
            "https://gratka.pl/nieruchomosci/dom/ob/123456", "x"]
    js = """
function shardOf(url, n) {
  let h = 0x811c9dc5 | 0;
  for (let i = 0; i < url.length; i++) h = Math.imul(h ^ url.charCodeAt(i), 0x01000193);
  return (h >>> 0) % n;
}
console.log(JSON.stringify(process.argv.slice(1).map(u => shardOf(u, 64))));
"""
    out = subprocess.run(["node", "-e", js, *urls],
                         capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == [payload.shard_of(u, 64) for u in urls]
