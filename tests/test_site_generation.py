"""National picker and regional page generation from two fixture datasets."""
import json
import os
import pathlib
import shutil
import subprocess

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _copy(root, relative):
    source = ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _meta(count, updated, health):
    return {
        "updated": updated,
        "count": count,
        "by_source": {"otodom": count, "olx": 0},
        "by_type": {"flat": count - 2, "house": 2},
        "relisted": 3,
        "archive": 4,
        "health": health,
        "rcn": {"records": 20, "matched": 5},
        "rcn_stats": {"towns": 2},
    }


def _dataset(root, slug, count, updated, health):
    directory = root / "site" / "data" / slug
    directory.mkdir(parents=True)
    (directory / "meta.json").write_text(
        json.dumps(_meta(count, updated, health)), encoding="utf-8")
    (directory / "manifest.json").write_text(
        json.dumps({"shards": 2}), encoding="utf-8")
    (directory / "index.json").write_text("[]", encoding="utf-8")
    (directory / "stats.json").write_text("{}", encoding="utf-8")
    (directory / "rcnstats.json").write_text("{}", encoding="utf-8")
    (directory / "archive.json").write_text("[]", encoding="utf-8")
    shard_dir = directory / "d"
    shard_dir.mkdir()
    (shard_dir / "00.json").write_text("{}", encoding="utf-8")
    (shard_dir / "01.json").write_text("{}", encoding="utf-8")


def _set_enabled(root, slug, enabled):
    path = root / "site" / "regions.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    next(region for region in document["regions"]
         if region["slug"] == slug)["enabled"] = enabled
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _run(root):
    env = os.environ.copy()
    env["RENTGEN_ROOT"] = str(root)
    subprocess.run(["node", str(ROOT / "scripts/update-summary.mjs")],
                   cwd=ROOT, env=env, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_generates_picker_catalog_stable_pages_and_discovery(tmp_path):
    for relative in (
        "site/regions.json", "site/index.html",
        "scripts/templates/listings.html", "scripts/templates/stats.html",
    ):
        _copy(tmp_path, relative)
    _set_enabled(tmp_path, "malopolskie", True)
    _dataset(tmp_path, "slaskie", 30761, "2026-08-26T22:11:02+00:00", "partial")
    _dataset(tmp_path, "malopolskie", 1200, "2026-08-25T10:00:00+00:00", "healthy")

    _run(tmp_path)

    derived = json.loads(
        (tmp_path / "site/data/regions.json").read_text(encoding="utf-8"))
    assert len(derived["regions"]) == 16
    by_slug = {entry["slug"]: entry for entry in derived["regions"]}
    assert by_slug["slaskie"]["data"]["count"] == 30761
    assert by_slug["slaskie"]["data"]["health"] == "partial"
    assert by_slug["slaskie"]["data"]["bytes"] > 0
    assert by_slug["malopolskie"]["published"] is True
    assert by_slug["opolskie"]["published"] is False

    picker = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert "30 761 ofert" in picker
    assert 'href="region/slaskie/"' in picker
    assert 'href="region/malopolskie/"' in picker
    assert "częściowe pokrycie źródeł" in picker
    assert 'class="region-size"' in picker
    assert 'current.searchParams.has("f")' in picker
    assert 'legacyDefault ? "slaskie"' in picker

    listing = (tmp_path / "site/region/slaskie/index.html").read_text(
        encoding="utf-8")
    assert '<base href="../../">' in listing
    assert '<link rel="canonical" href="https://110kc3.github.io/rentgen-ofert/region/slaskie/">' in listing
    assert '"@type":"Dataset"' in listing
    assert "data/slaskie/meta.json" in listing
    assert "{{" not in listing
    assert listing.index('src="region-context.js') < listing.index('src="app.js')

    stats = (tmp_path / "site/region/malopolskie/stats/index.html").read_text(
        encoding="utf-8")
    assert '<base href="../../../">' in stats
    assert "/region/malopolskie/stats/" in stats
    assert "woj. małopolskie" in stats
    assert stats.index('src="region-context.js') < stats.index('src="stats.js')

    unpublished = (tmp_path / "site/region/opolskie/index.html").read_text(
        encoding="utf-8")
    assert '<meta name="robots" content="noindex">' in unpublished
    assert "dane nie zostały jeszcze opublikowane" in unpublished

    sitemap = (tmp_path / "site/sitemap.xml").read_text(encoding="utf-8")
    assert "/region/slaskie/" in sitemap
    assert "/region/malopolskie/stats/" in sitemap
    assert "/region/opolskie/" not in sitemap
    llms = (tmp_path / "site/llms.txt").read_text(encoding="utf-8")
    assert "/data/regions.json" in llms
    assert "### woj. śląskie" in llms

    # The catalog kill switch removes only this region from the Pages artifact
    # and discovery, keeping its configured placeholder and its sibling.
    _set_enabled(tmp_path, "malopolskie", False)
    _run(tmp_path)
    sitemap = (tmp_path / "site/sitemap.xml").read_text(encoding="utf-8")
    assert "/region/slaskie/" in sitemap
    assert "/region/malopolskie/" not in sitemap
    placeholder = (tmp_path / "site/region/malopolskie/index.html").read_text(
        encoding="utf-8")
    assert "dane nie zostały jeszcze opublikowane" in placeholder
    assert not (tmp_path / "site/data/malopolskie").exists()
    assert (tmp_path / "site/data/slaskie/meta.json").exists()

    # A directory claiming publication via meta.json must be atomic enough for
    # the app to load; deployment should fail and keep the previous Pages build.
    (tmp_path / "site/data/slaskie/index.json").unlink()
    with pytest.raises(subprocess.CalledProcessError):
        _run(tmp_path)
    (tmp_path / "site/data/slaskie/index.json").write_text("[]", encoding="utf-8")
    (tmp_path / "site/data/slaskie/rcnstats.json").unlink()
    with pytest.raises(subprocess.CalledProcessError):
        _run(tmp_path)


def test_rejects_every_data_directory_outside_the_catalog(tmp_path):
    for relative in (
        "site/regions.json", "site/index.html",
        "scripts/templates/listings.html", "scripts/templates/stats.html",
    ):
        _copy(tmp_path, relative)
    unknown = tmp_path / "site/data/not-a-region"
    unknown.mkdir(parents=True)
    (unknown / "orphan.json").write_text("{}", encoding="utf-8")

    with pytest.raises(subprocess.CalledProcessError):
        _run(tmp_path)


def test_rejects_nonempty_regional_tree_without_publication_marker(tmp_path):
    for relative in (
        "site/regions.json", "site/index.html",
        "scripts/templates/listings.html", "scripts/templates/stats.html",
    ):
        _copy(tmp_path, relative)
    _dataset(tmp_path, "slaskie", 100, "2026-08-27T00:00:00+00:00", "partial")
    (tmp_path / "site/data/slaskie/meta.json").unlink()

    with pytest.raises(subprocess.CalledProcessError):
        _run(tmp_path)
