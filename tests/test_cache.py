"""The phash cache: packing, gzip, the v1 migration, and negative entries.

The v1 file wrote each 256-bit dHash as a ~78-character decimal string in plain
JSON and reached 62.86 MB for one region — past GitHub's 50 MB warning and
heading for the 100 MB hard limit that makes a run's push fail outright. These
tests pin the encoding, and pin that a v1 file is still readable so the
migration needs no separate step.
"""
import gzip
import json

from scraper import cache

H = 2588337559151699339583726016123456789012345678901234567890


def test_pack_round_trips_and_is_shorter_than_decimal():
    packed = cache.pack(H)
    assert cache.unpack(packed) == H
    assert len(packed) == 44 < len(str(H))
    assert cache.unpack(cache.pack(0)) == 0
    assert cache.unpack(cache.pack(2 ** 256 - 1)) == 2 ** 256 - 1


def test_v1_decimal_strings_still_read():
    assert cache.unpack(str(H)) == H
    assert cache.unpack(H) == H


def test_save_is_gzipped_and_drops_the_v1_file(tmp_path):
    plain = tmp_path / "phash_slaskie.json"
    plain.write_text(json.dumps({"version": 1, "entries": {
        "u1": {"hashes": [str(H)], "seen": "2026-08-01",
               "urls": ["https://img/1.jpg"]}}}), encoding="utf-8")
    gz = tmp_path / "phash_slaskie.json.gz"

    loaded = cache.load(gz)          # .gz absent -> reads the legacy plain file
    assert cache.get(loaded, "u1") == [H]
    assert cache.get_urls(loaded, "u1") == ["https://img/1.jpg"]

    cache.save(gz, loaded)
    assert gz.exists() and not plain.exists(), "the huge v1 file must not linger"
    with gzip.open(gz, "rt", encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw["version"] == 2
    assert raw["entries"]["u1"]["h"] == [cache.pack(H)]
    assert cache.get(cache.load(gz), "u1") == [H]


def test_gz_wins_over_a_stale_plain_file(tmp_path):
    gz, plain = tmp_path / "c.json.gz", tmp_path / "c.json"
    plain.write_text(json.dumps({"version": 1, "entries": {"old": {"hashes": ["1"]}}}),
                     encoding="utf-8")
    cache.save(gz, {"version": 2, "entries": {"new": {"h": [cache.pack(H)]}}})
    assert list(cache.load(gz)["entries"]) == ["new"]


def test_cover_scope_round_trips_and_old_hits_default_to_gallery(tmp_path):
    gz = tmp_path / "phash_test.json.gz"
    c = {"version": cache.VERSION, "entries": {}}
    cache.put(c, "cover", [H], "2026-08-28",
              image_urls=["https://img/card.jpg"], scope="cover")
    cache.put(c, "gallery", [H], "2026-08-28")
    cache.save(gz, c)

    loaded = cache.load(gz)
    assert cache.get_scope(loaded, "cover") == "cover"
    assert cache.get_scope(loaded, "gallery") == "gallery"
    assert cache.get_scope(loaded, "missing") == "gallery"


def test_missing_and_corrupt_files_yield_an_empty_cache(tmp_path):
    assert cache.load(tmp_path / "nope.json.gz")["entries"] == {}
    bad = tmp_path / "bad.json.gz"
    bad.write_bytes(b"not gzip at all")
    assert cache.load(bad)["entries"] == {}


# ---- negative entries -------------------------------------------------------

def test_a_miss_is_retried_then_believed_then_re_probed():
    c = {"version": cache.VERSION, "entries": {}}
    for i in range(cache.MISS_RETRIES):
        assert cache.get(c, "u", "2026-08-01") is None      # keep trying
        cache.put(c, "u", [], "2026-08-01")
    assert cache.get(c, "u", "2026-08-01") == []            # believed
    assert c["entries"]["u"]["miss"] == cache.MISS_RETRIES
    # the verdict expires, so a portal that starts serving photos is picked up
    later = "2026-08-08"
    assert cache._days_between("2026-08-01", later) >= cache.MISS_RECHECK_DAYS
    assert cache.get(c, "u", later) is None


def test_a_hit_is_never_overwritten_by_a_blank_read():
    c = {"version": cache.VERSION, "entries": {}}
    cache.put(c, "u", [H], "2026-08-01", image_urls=["https://img/1.jpg"])
    cache.put(c, "u", [], "2026-08-02")            # transient blank
    assert cache.get(c, "u", "2026-08-02") == [H]
    assert cache.get_urls(c, "u") == ["https://img/1.jpg"]


def test_prune_drops_stale_entries_including_negative_ones():
    c = {"version": cache.VERSION, "entries": {}}
    cache.put(c, "fresh", [H], "2026-08-01")
    cache.put(c, "old", [H], "2026-06-01")
    cache.put(c, "old-miss", [], "2026-06-01")
    assert cache.prune(c, "2026-08-01") == 2
    assert list(c["entries"]) == ["fresh"]


# ---- persisted budget backlog ---------------------------------------------

def test_backlog_retains_age_only_for_urls_still_deferred():
    c = {"version": cache.VERSION, "entries": {},
         "backlog": {"old": "2026-08-01", "finished": "2026-08-02"}}
    summary = cache.update_backlog(c, ["old", "new", "old"], "2026-08-05")
    assert c["backlog"] == {"new": "2026-08-05", "old": "2026-08-01"}
    assert summary == {"count": 2, "oldest": "2026-08-01", "age_days": 4}

    assert cache.update_backlog(c, [], "2026-08-06") == {
        "count": 0, "oldest": None, "age_days": 0,
    }
    assert c["backlog"] == {}


def test_backlog_round_trips_through_the_gzip_cache(tmp_path):
    path = tmp_path / "phash_malopolskie.json.gz"
    c = {"version": cache.VERSION, "entries": {}}
    cache.update_backlog(c, ["https://example.test/ad/1"], "2026-08-01")
    cache.save(path, c)
    assert cache.backlog(cache.load(path)) == {
        "https://example.test/ad/1": "2026-08-01",
    }


def test_malformed_backlog_is_ignored():
    assert cache.backlog({"backlog": []}) == {}
    assert cache.backlog({"backlog": {"ok": "2026-08-01", "bad": None,
                                       "nonsense": "last Tuesday",
                                       "": "2026-08-02"}}) == {
        "ok": "2026-08-01",
    }
