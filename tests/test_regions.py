"""Canonical 16-region catalog and portal routing (offline)."""
import copy
import json

import pytest

from scraper import gratka, morizon, olx, otodom, regions


OFFICIAL = {
    "dolnoslaskie": "02", "kujawsko-pomorskie": "04", "lubelskie": "06",
    "lubuskie": "08", "lodzkie": "10", "malopolskie": "12",
    "mazowieckie": "14", "opolskie": "16", "podkarpackie": "18",
    "podlaskie": "20", "pomorskie": "22", "slaskie": "24",
    "swietokrzyskie": "26", "warminsko-mazurskie": "28",
    "wielkopolskie": "30", "zachodniopomorskie": "32",
}


def _write(tmp_path, document):
    path = tmp_path / "regions.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_production_catalog_has_all_official_regions_and_one_default():
    document = regions.load_catalog()
    actual = {entry["slug"]: entry["teryt"]
              for entry in document["regions"]}
    assert actual == OFFICIAL
    assert document["default"] == "slaskie"
    assert [entry["slug"] for entry in document["regions"]
            if entry["enabled"]] == ["opolskie", "slaskie"]
    malopolskie = regions.get_region("malopolskie", document)
    assert malopolskie["cadence"] == "manual"
    assert malopolskie["enabled"] is False
    opolskie = regions.get_region("opolskie", document)
    assert opolskie["cadence"] == "manual"
    assert opolskie["enabled"] is True
    assert regions.get_region("slaskie", document)["cadence"] == "twice_daily"


def test_every_portal_slug_is_explicit_and_used_by_search_roots():
    entry = regions.get_region("slaskie")
    assert set(entry["portals"]) == set(regions.PORTALS)
    assert entry["portals"]["otodom"] in otodom.SEARCH["house"]
    assert entry["portals"]["olx"] in olx.SEARCH["house"]
    assert entry["portals"]["gratka"] in gratka.SEARCH["house"][0]
    assert entry["portals"]["morizon"] in morizon.SEARCH["house"][0]


def test_otodom_compound_region_slugs_are_explicit():
    document = regions.load_catalog()
    assert regions.portal_slug("kujawsko-pomorskie", "otodom", document) == \
        "kujawsko--pomorskie"
    assert regions.portal_slug("warminsko-mazurskie", "otodom", document) == \
        "warminsko--mazurskie"


def test_double_hyphens_are_portal_only_and_triples_are_rejected(tmp_path):
    document = copy.deepcopy(regions.load_catalog())
    document["regions"][0]["slug"] = "dolno--slaskie"
    with pytest.raises(regions.RegionCatalogError, match="invalid canonical"):
        regions.load_catalog(_write(tmp_path, document))

    document = copy.deepcopy(regions.load_catalog())
    document["regions"][0]["portals"]["otodom"] = "dolno---slaskie"
    with pytest.raises(regions.RegionCatalogError, match="invalid otodom"):
        regions.load_catalog(_write(tmp_path, document))


def test_portal_slugs_may_differ_from_each_other(tmp_path):
    document = copy.deepcopy(regions.load_catalog())
    entry = next(r for r in document["regions"] if r["slug"] == "slaskie")
    entry["portals"]["olx"] = "woj-slaskie"
    loaded = regions.load_catalog(_write(tmp_path, document))
    assert regions.portal_slug("slaskie", "olx", loaded) == "woj-slaskie"
    assert regions.portal_slug("slaskie", "otodom", loaded) == "slaskie"


def test_missing_portal_slug_is_rejected(tmp_path):
    document = copy.deepcopy(regions.load_catalog())
    document["regions"][0]["portals"].pop("morizon")
    with pytest.raises(regions.RegionCatalogError, match="exactly"):
        regions.load_catalog(_write(tmp_path, document))


def test_wrong_teryt_mapping_and_unknown_region_are_rejected(tmp_path):
    document = copy.deepcopy(regions.load_catalog())
    document["regions"][0]["teryt"] = "99"
    with pytest.raises(regions.RegionCatalogError, match="TERYT prefixes"):
        regions.load_catalog(_write(tmp_path, document))
    with pytest.raises(regions.RegionCatalogError, match="unknown region"):
        regions.get_region("not-a-region")


def test_workflow_gate_accepts_only_enabled_region(capsys):
    assert regions.main(["--region", "slaskie", "--require-enabled"]) == 0
    assert "TERYT 24" in capsys.readouterr().out
    assert regions.main(["--region", "opolskie", "--require-enabled"]) == 0
    assert "TERYT 16" in capsys.readouterr().out
    for slug in ("malopolskie", "mazowieckie"):
        with pytest.raises(SystemExit):
            regions.main(["--region", slug, "--require-enabled"])
