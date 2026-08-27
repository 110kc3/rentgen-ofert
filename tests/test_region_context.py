"""Browser regional URL and persistence semantics, executed in Node."""
import json
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _context_results():
    module = json.dumps(str(ROOT / "site/region-context.js"))
    script = f"""
const r = require({module});
const snap = {{type: "flat", localities: ["Kraków"]}};
const filtered = r.withFilter(
  "https://example.test/rentgen-ofert/index.html?region=malopolskie&utm=x#cards",
  snap, false);
const restored = r.withFilter(`https://example.test${{filtered}}`, snap, true);
const stableFiltered = r.withFilter(
  "https://example.test/rentgen-ofert/region/slaskie/?utm=x#cards",
  snap, false);
console.log(JSON.stringify({{
  listing: r.fromLocation({{pathname: "/rentgen-ofert/region/malopolskie/", search: "?region=slaskie"}}, "listings"),
  stats: r.fromLocation({{pathname: "/rentgen-ofert/region/pomorskie/stats/", search: ""}}, "stats"),
  listingIndex: r.fromLocation({{pathname: "/rentgen-ofert/region/lubuskie/index.html", search: ""}}, "listings"),
  statsIndex: r.fromLocation({{pathname: "/rentgen-ofert/region/lubuskie/stats/index.html", search: ""}}, "stats"),
  legacy: r.fromLocation({{pathname: "/rentgen-ofert/index.html", search: "?region=lodzkie"}}, "listings"),
  invalid: r.fromLocation({{pathname: "/rentgen-ofert/index.html", search: "?region=../../x"}}, "listings"),
  filterSlaskie: r.storageKey("rentgen.filters.v2", "slaskie"),
  filterMalopolskie: r.storageKey("rentgen.filters.v2", "malopolskie"),
  mapSlaskie: r.storageKey("rentgen.map.v1", "slaskie"),
  anchoredDistance: r.distanceForRegion("20", true),
  unanchoredDistance: r.distanceForRegion("20", false),
  invalidDistance: r.distanceForRegion("not-a-radius", true),
  filtered, restored, stableFiltered,
  listingHref: r.pageHref("pomorskie", "listings"),
  statsHref: r.pageHref("pomorskie", "stats"),
  listingUrl: r.pageUrl("pomorskie", "listings", "https://example.test/rentgen-ofert/"),
  statsUrl: r.pageUrl("pomorskie", "stats", "https://example.test/rentgen-ofert/"),
}}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    return json.loads(result.stdout)


def test_stable_paths_win_and_legacy_query_still_works():
    result = _context_results()
    assert result["listing"] == "malopolskie"
    assert result["stats"] == "pomorskie"
    assert result["listingIndex"] == "lubuskie"
    assert result["statsIndex"] == "lubuskie"
    assert result["legacy"] == "lodzkie"
    assert result["invalid"] == "slaskie"


def test_storage_is_region_scoped_and_filter_url_preserves_other_state():
    result = _context_results()
    assert result["filterSlaskie"] == "rentgen.filters.v2.slaskie"
    assert result["filterMalopolskie"] == "rentgen.filters.v2.malopolskie"
    assert result["filterSlaskie"] != result["filterMalopolskie"]
    assert result["mapSlaskie"] == "rentgen.map.v1.slaskie"
    assert result["anchoredDistance"] == "20"
    assert result["unanchoredDistance"] == "all"
    assert result["invalidDistance"] == "all"
    assert "region=malopolskie" in result["filtered"]
    assert "utm=x" in result["filtered"]
    assert "f=" in result["filtered"]
    assert result["filtered"].endswith("#cards")
    assert "region=malopolskie" in result["restored"]
    assert "utm=x" in result["restored"]
    assert "f=" not in result["restored"]
    assert result["restored"].endswith("#cards")
    assert result["stableFiltered"].startswith(
        "/rentgen-ofert/region/slaskie/?")
    assert "utm=x" in result["stableFiltered"]
    assert "f=" in result["stableFiltered"]
    assert result["stableFiltered"].endswith("#cards")


def test_app_and_stats_links_use_stable_regional_paths():
    result = _context_results()
    assert result["listingHref"] == "region/pomorskie/"
    assert result["statsHref"] == "region/pomorskie/stats/"
    assert result["listingUrl"] == \
        "https://example.test/rentgen-ofert/region/pomorskie/"
    assert result["statsUrl"] == \
        "https://example.test/rentgen-ofert/region/pomorskie/stats/"
