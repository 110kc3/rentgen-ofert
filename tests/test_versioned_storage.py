"""Rehearse upload failure, immutable versions and rollback without a service."""
import functools
import http.server
import json
import threading
import urllib.error
import urllib.request

import pytest

from scripts import versioned_storage as storage
from scripts.validate_data import DataValidationError, validate_data_dir
from test_validate_data import _compact_dataset


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source"
    path.mkdir()
    _compact_dataset(path)
    (path / "rcnstats.json").write_text("{}")
    return path


def _pointer(store):
    return json.loads((store / "slaskie/current.json").read_bytes())


def _change_meta(source):
    path = source / "meta.json"
    meta = json.loads(path.read_bytes())
    meta["updated"] = "2026-10-19T12:00:00Z"
    path.write_text(json.dumps(meta))


def test_public_validation_omits_only_pipeline_history(source):
    (source / "history.json.gz").unlink()
    with pytest.raises(DataValidationError, match="history"):
        validate_data_dir(source)
    assert validate_data_dir(source, require_history=False)["detail_records"] == 2
    (source / "d/00.json").unlink()
    with pytest.raises(DataValidationError, match="missing detail shard"):
        validate_data_dir(source, require_history=False)


def test_publish_pins_all_public_bytes_and_keeps_previous_version(source, tmp_path):
    store = tmp_path / "store"
    first = storage.publish(source, store, "slaskie")
    old = store / "slaskie/versions" / first["version"]
    original_meta = (old / "meta.json").read_bytes()
    assert not (old / "history.json.gz").exists()
    assert _pointer(store) == {"schema": 1, "version": first["version"]}
    assert first["count"] == 2
    assert storage.publish(source, store, "slaskie") == first
    _change_meta(source)
    second = storage.publish(source, store, "slaskie")
    assert second["version"] != first["version"]  # metadata is pinned too
    assert (old / "meta.json").read_bytes() == original_meta
    assert _pointer(store)["version"] == second["version"]
    storage.activate(store, "slaskie", first["version"])
    assert _pointer(store)["version"] == first["version"]
    assert (store / "slaskie/versions" / second["version"]).is_dir()


@pytest.mark.parametrize("first_upload", [True, False])
def test_interrupted_upload_never_replaces_pointer_or_leaks_partial_version(source, tmp_path, first_upload):
    store = tmp_path / "store"
    if not first_upload:
        storage.publish(source, store, "slaskie")
    pointer = store / "slaskie/current.json"
    previous = pointer.read_bytes() if pointer.exists() else None
    _change_meta(source)
    with pytest.raises(InterruptedError):
        storage.publish(source, store, "slaskie", interrupt_after=4)
    assert (pointer.read_bytes() if pointer.exists() else None) == previous
    assert not list((store / "slaskie").glob(".upload-*"))
    assert len(list((store / "slaskie/versions").iterdir())) == (0 if first_upload else 1)


def test_bad_candidate_does_not_replace_good_pointer(source, tmp_path):
    store = tmp_path / "store"
    first = storage.publish(source, store, "slaskie")
    (source / "a/00.json").unlink()
    with pytest.raises(DataValidationError, match="archive detail shard"):
        storage.publish(source, store, "slaskie")
    assert _pointer(store)["version"] == first["version"]


@pytest.mark.parametrize("target", ["meta.json", "a/00.json", "release.json"])
def test_corrupt_rollback_target_is_rejected_without_changing_current(source, tmp_path, target):
    store = tmp_path / "store"
    first = storage.publish(source, store, "slaskie")
    _change_meta(source)
    second = storage.publish(source, store, "slaskie")
    path = store / "slaskie/versions" / first["version"] / target
    path.write_bytes(path.read_bytes() + b" ")  # even valid JSON byte drift is corruption
    with pytest.raises(ValueError, match="hash"):
        storage.activate(store, "slaskie", first["version"])
    assert _pointer(store)["version"] == second["version"]


def test_regions_remain_isolated_and_unknown_region_is_refused(source, tmp_path):
    store = tmp_path / "store"
    first = storage.publish(source, store, "slaskie")
    other = storage.publish(source, store, "opolskie")
    assert first["version"] != other["version"]
    _change_meta(source)
    storage.publish(source, store, "slaskie")
    assert json.loads((store / "opolskie/current.json").read_bytes())["version"] == other["version"]
    with pytest.raises(ValueError):
        storage.publish(source, store, "../../elsewhere")


def test_storage_http_cors_cache_policy_and_hidden_staging(source, tmp_path):
    store = tmp_path / "store"
    result = storage.publish(source, store, "slaskie")
    origin = "http://127.0.0.1:8000"
    handler = functools.partial(storage.StorageHandler, directory=str(store), origin=origin)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/slaskie/"
    try:
        with urllib.request.urlopen(base + "current.json") as response:
            assert response.headers["Cache-Control"] == "no-store"
            assert response.headers["Access-Control-Allow-Origin"] == origin
        with urllib.request.urlopen(base + f"versions/{result['version']}/a/00.json") as response:
            assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        for path in [".publish.lock", ".upload-partial/meta.json", "versions/", f"versions/{result['version']}/history.json.gz"]:
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(base + path)
            assert exc.value.code == 404
            assert exc.value.headers["Cache-Control"] == "no-store"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
