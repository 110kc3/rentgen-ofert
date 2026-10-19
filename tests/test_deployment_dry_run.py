"""Artifact/catalog handoff with complete mirrors, legacy data and failures."""
import json
import pytest

from scripts.deployment_dry_run import build
from scripts import versioned_storage as storage
from test_validate_data import _compact_dataset, _dataset


@pytest.fixture
def inputs(tmp_path):
    data = tmp_path / "data"
    for slug, fixture in [("slaskie", _compact_dataset), ("opolskie", _dataset)]:
        path = data / slug
        path.mkdir(parents=True)
        fixture(path)
        (path / "rcnstats.json").write_text("{}")
    # Disabled pilot trees are neither validated nor included in the candidate.
    disabled = data / "malopolskie"
    disabled.mkdir()
    (disabled / "meta.json").write_text("not publishable")
    store = tmp_path / "store"
    version = storage.publish(data / "slaskie", store, "slaskie")["version"]
    mapping = {"slaskie": {"pointer_url": "https://objects.example/slaskie/current.json"}}
    return data, store, mapping, version


def _catalog(output):
    document = json.loads((output / "site/data/regions.json").read_bytes())
    return {entry["slug"]: entry for entry in document["regions"]}


def test_mixed_artifact_omits_external_payload_and_uses_verified_metadata(inputs, tmp_path):
    data, store, mapping, version = inputs
    output = tmp_path / "result"
    result = build(data_root=data, store=store, storage_map=mapping, output=output)
    assert result["dry_run"] and result["regions"]["slaskie"]["backend"] == "external"
    assert result["regions"]["opolskie"]["backend"] == "pages"
    assert not (output / "site/data/slaskie").exists()
    assert not (output / "site/data/malopolskie").exists()
    assert (output / "site/data/opolskie/index.json").is_file()
    assert not list(output.rglob("history.json*"))
    catalog = _catalog(output)
    assert catalog["slaskie"]["data"]["count"] == 2
    assert catalog["slaskie"]["storage"] == mapping["slaskie"] | {"version": version}
    assert "storage" not in catalog["opolskie"]
    assert not catalog["malopolskie"]["published"]
    url = f"https://objects.example/slaskie/versions/{version}"
    for page in ["region/slaskie/index.html", "region/slaskie/stats/index.html", "llms.txt"]:
        rendered = (output / "site" / page).read_text()
        assert url + "/meta.json" in rendered
        assert "/data/slaskie/" not in rendered
    ld = (output / "site/region/slaskie/index.html").read_text()
    assert '"contentUrl":' + json.dumps(url + "/index.json") in ld
    assert result["pages_bytes"] == sum(path.stat().st_size for path in (output / "site").rglob("*") if path.is_file())
    assert json.loads((output / "report.json").read_text()) == result
    # The builder does not change either the local sources or mirror pointer.
    assert (data / "slaskie/history.json.gz").is_file()
    assert json.loads((store / "slaskie/current.json").read_text())["version"] == version


def test_pointer_advancement_does_not_change_a_generated_catalog(inputs, tmp_path):
    data, store, mapping, version = inputs
    first = tmp_path / "first"
    build(data_root=data, store=store, storage_map=mapping, output=first)
    old_catalog = (first / "site/data/regions.json").read_bytes()
    meta_path = data / "slaskie/meta.json"
    meta = json.loads(meta_path.read_text())
    meta["updated"] = "2026-10-19T20:00:00Z"
    meta_path.write_text(json.dumps(meta))
    newer = storage.publish(data / "slaskie", store, "slaskie")["version"]
    assert newer != version
    assert (first / "site/data/regions.json").read_bytes() == old_catalog
    second = tmp_path / "second"
    build(data_root=data, store=store, storage_map=mapping, output=second)
    assert _catalog(second)["slaskie"]["storage"]["version"] == newer
    assert _catalog(second)["slaskie"]["data"]["updated"] == meta["updated"]
    pinned = tmp_path / "pinned"
    build(data_root=data, store=store, storage_map={"slaskie": mapping["slaskie"] | {"version": version}}, output=pinned)
    assert _catalog(pinned)["slaskie"]["storage"]["version"] == version


@pytest.mark.parametrize("failure", ["missing shard", "changed bytes", "partial pointer", "missing pointer"])
def test_incomplete_or_corrupt_upload_cannot_create_candidate_artifact(inputs, tmp_path, failure):
    data, store, mapping, version = inputs
    previous = tmp_path / "previous"
    build(data_root=data, store=store, storage_map=mapping, output=previous)
    original = (previous / "site/data/regions.json").read_bytes()
    if failure == "missing shard":
        (store / "slaskie/versions" / version / "a/00.json").unlink()
    elif failure == "changed bytes":
        path = store / "slaskie/versions" / version / "meta.json"
        path.write_bytes(path.read_bytes() + b" ")
    elif failure == "partial pointer":
        (store / "slaskie/current.json").write_text(json.dumps({"schema": 1, "version": "f" * 64}))
    else:
        (store / "slaskie/current.json").unlink()
    output = tmp_path / "failed"
    with pytest.raises((OSError, ValueError)):
        build(data_root=data, store=store, storage_map=mapping, output=output)
    assert not output.exists()
    assert not list(tmp_path.glob(".rentgen-deployment-*"))
    assert (previous / "site/data/regions.json").read_bytes() == original


def test_broken_pages_sibling_aborts_whole_mixed_artifact(inputs, tmp_path):
    data, store, mapping, _ = inputs
    (data / "opolskie/d/00.json").unlink()
    with pytest.raises(ValueError, match="detail shard"):
        build(data_root=data, store=store, storage_map=mapping, output=tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_local_only_artifact_still_validates_and_keeps_both_regions(inputs, tmp_path):
    data, _, _, _ = inputs
    output = tmp_path / "result"
    report = build(data_root=data, output=output)
    assert report["external_bytes"] == 0
    assert all(value["backend"] == "pages" for value in report["regions"].values())
    assert (output / "site/data/slaskie/a/00.json").is_file()
    assert not (output / "site/data/slaskie/history.json.gz").exists()


@pytest.mark.parametrize("mapping", [
    {"malopolskie": {"pointer_url": "https://objects.example/current.json"}},
    {"not-a-region": {}},
    {"slaskie": {"pointer_url": "http://remote.example/current.json"}},
    {"slaskie": {"pointer_url": "https://objects.example/current.json?secret=x"}},
    {"slaskie": {"pointer_url": "https://objects.example/current.json", "version": "../escape"}},
])
def test_disabled_unknown_and_invalid_mapping_are_refused(inputs, tmp_path, mapping):
    data, store, _, _ = inputs
    with pytest.raises(ValueError):
        build(data_root=data, store=store, storage_map=mapping, output=tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_existing_output_and_input_trees_are_never_overwritten(inputs, tmp_path):
    data, store, mapping, _ = inputs
    output = tmp_path / "result"
    output.mkdir()
    (output / "keep.txt").write_text("existing artifact")
    with pytest.raises(ValueError, match="already exists"):
        build(data_root=data, store=store, storage_map=mapping, output=output)
    assert (output / "keep.txt").read_text() == "existing artifact"
    for target in [data / "artifact", store / "artifact", tmp_path]:
        with pytest.raises(ValueError, match="outside"):
            build(data_root=data, store=store, storage_map=mapping, output=target)
