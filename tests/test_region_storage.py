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


def _restore_repo(tmp_path, branch=None, paths=()):
    root = _repo(tmp_path)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "main catalog")
    _git(root, "remote", "add", "origin", str(root))
    if branch:
        _git(root, "checkout", "--orphan", branch)
        _git(root, "rm", "-rf", ".")
        for path in paths:
            _put(root, path)
        _git(root, "add", ".")
        _git(root, "commit", "--allow-empty", "-qm", "data fixture")
        _git(root, "checkout", "main")
    return root


@pytest.mark.parametrize("branch", ["data-slaskie", "data"])
def test_restore_recovers_history_without_changing_main_or_siblings(tmp_path, branch):
    paths = ("site/data/slaskie/meta.json", "site/data/slaskie/history.json.gz",
             "cache/phash_slaskie.json.gz", "cache/phash_opolskie.json.gz",
             "site/data/opolskie/meta.json")
    root = _restore_repo(tmp_path, branch, paths)
    _put(root, "site/data/opolskie/keep.txt", "sibling")
    head = _git(root, "rev-parse", "HEAD")
    assert region_storage.restore_region(root, "slaskie") == branch
    assert (root / paths[1]).read_text() == "fixture"
    assert (root / paths[2]).read_text() == "fixture"
    assert not (root / paths[3]).exists()
    assert not (root / paths[4]).exists()
    assert (root / "site/data/opolskie/keep.txt").read_text() == "sibling"
    assert _git(root, "rev-parse", "HEAD") == head
    assert _git(root, "diff", "--cached", "--name-only") == ""


@pytest.mark.parametrize("legacy_other_region", [False, True])
def test_restore_allows_only_verified_cold_start(tmp_path, legacy_other_region):
    root = _restore_repo(tmp_path, "data" if legacy_other_region else None,
                         ["site/data/opolskie/meta.json"])
    assert region_storage.restore_region(root, "slaskie") is None
    assert not (root / "site/data/slaskie").exists()


@pytest.mark.parametrize("branch,paths", [
    ("data-slaskie", []),
    ("data-slaskie", ["site/data/slaskie/meta.json"]),
    ("data", ["site/data/slaskie/meta.json"]),
    ("data-slaskie", ["site/data/slaskie/history.json.gz"]),
])
def test_restore_rejects_incomplete_existing_tree(tmp_path, branch, paths):
    root = _restore_repo(tmp_path, branch, paths)
    with pytest.raises(region_storage.RegionStorageError, match="incomplete"):
        region_storage.restore_region(root, "slaskie")


def test_restore_transport_failure_is_not_a_cold_start(tmp_path):
    root = _restore_repo(tmp_path)
    _git(root, "remote", "set-url", "origin", str(root / "unreachable.git"))
    with pytest.raises(region_storage.RegionStorageError, match="cannot determine"):
        region_storage.restore_region(root, "slaskie")


@pytest.mark.parametrize("operation", ["fetch", "restore"])
def test_restore_propagates_fetch_and_extraction_failure(tmp_path, monkeypatch, operation):
    root = _restore_repo(tmp_path, "data-slaskie",
                         ["site/data/slaskie/meta.json", "site/data/slaskie/history.json.gz"])
    original = region_storage._git
    calls = []

    def fail(root, *args, **kw):
        calls.append(args)
        if args[0] == operation:
            raise subprocess.CalledProcessError(128, ["git", *args], stderr="fixture failure")
        return original(root, *args, **kw)

    monkeypatch.setattr(region_storage, "_git", fail)
    with pytest.raises(subprocess.CalledProcessError):
        region_storage.restore_region(root, "slaskie")
    assert not any(args[-1] == "refs/heads/data" for args in calls)
