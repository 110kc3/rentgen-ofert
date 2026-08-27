"""Two-region branch/cache isolation exercised against real temporary git repos."""
import pathlib
import subprocess

import pytest

from scraper import regions
from scripts import region_storage


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True).stdout


def _put(root, relative, text="fixture"):
    path = pathlib.Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _put(tmp_path, "site/regions.json",
         regions.CATALOG_PATH.read_text(encoding="utf-8"))
    return tmp_path


def test_stage_carries_only_target_region_and_intentional_shared_caches(tmp_path):
    root = _repo(tmp_path)
    _put(root, "site/data/slaskie/index.json", "slaskie")
    _put(root, "site/data/malopolskie/index.json", "malopolskie")
    _put(root, "cache/phash_slaskie.json.gz")
    _put(root, "cache/rcn_slaskie.json.gz")
    _put(root, "cache/nol_archive_slaskie.json")
    _put(root, "cache/phash_malopolskie.json.gz")
    _put(root, "cache/rcn_malopolskie.json.gz")
    _put(root, "cache/nol_archive_malopolskie.json")
    _put(root, "cache/geo_cache.json")
    _put(root, "cache/nol_towns.json")

    staged = set(region_storage.stage_region(root, "slaskie"))
    assert staged == {
        "site/data/slaskie/index.json",
        "cache/phash_slaskie.json.gz",
        "cache/rcn_slaskie.json.gz",
        "cache/nol_archive_slaskie.json",
        "cache/geo_cache.json",
        "cache/nol_towns.json",
    }
    assert not any("malopolskie" in path for path in staged)


def test_stage_refuses_an_index_already_containing_another_region(tmp_path):
    root = _repo(tmp_path)
    _put(root, "site/data/slaskie/index.json", "slaskie")
    _put(root, "site/data/malopolskie/index.json", "malopolskie")
    _git(root, "add", "site/data/malopolskie/index.json")
    with pytest.raises(region_storage.RegionStorageError, match="out-of-scope"):
        region_storage.stage_region(root, "slaskie")


def test_overlay_replaces_one_region_and_preserves_its_sibling(tmp_path):
    root = _repo(tmp_path)
    _put(root, "site/data/slaskie/value.txt", "old slaskie")
    _put(root, "site/data/slaskie/stale-shard.json", "must disappear")
    _put(root, "site/data/malopolskie/value.txt", "keep malopolskie")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "main fixtures")

    _git(root, "checkout", "--orphan", "data-slaskie")
    _git(root, "rm", "-rf", ".")
    _put(root, "site/data/slaskie/value.txt", "new slaskie")
    _git(root, "add", "site/data/slaskie/value.txt")
    _git(root, "commit", "-qm", "slaskie data")
    _git(root, "checkout", "main")

    assert region_storage.overlay_region(root, "data-slaskie", "slaskie")
    assert (root / "site/data/slaskie/value.txt").read_text() == "new slaskie"
    assert not (root / "site/data/slaskie/stale-shard.json").exists()
    sibling = root / "site/data/malopolskie/value.txt"
    assert sibling.read_text() == "keep malopolskie"

    # This branch has no Małopolskie tree. The existing deployed copy must not
    # be removed just because a matching overlay was absent.
    assert not region_storage.overlay_region(
        root, "data-slaskie", "malopolskie")
    assert sibling.read_text() == "keep malopolskie"
