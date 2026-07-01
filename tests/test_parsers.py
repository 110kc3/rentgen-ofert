import json
import pathlib

from scraper import gratka, nieruchomosci_online as nol, olx, otodom

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_otodom_parse_items():
    sa = json.loads((FIX / "otodom_search_ads.json").read_text(encoding="utf-8"))
    rows = otodom.parse_items(sa["items"], "house")
    assert rows
    for r in rows:
        assert r["source"] == "otodom"
        assert r["url"].startswith("https://www.otodom.pl/pl/oferta/")
        assert r["price"] is None or isinstance(r["price"], int)
    assert all(r["type"] in ("house", "flat") for r in rows)


def test_olx_skips_syndicated_partner_ads():
    state = json.loads((FIX / "olx_state.json").read_text(encoding="utf-8"))
    ads = state["listing"]["listing"]["ads"]
    n_partner = sum(1 for a in ads if (a.get("partner") or {}).get("code") or a.get("externalUrl"))
    rows = olx.parse_ads(ads, "house")
    assert len(rows) == len(ads) - n_partner
    for r in rows:
        assert r["source"] == "olx"
        assert r["url"].startswith("https://www.olx.pl/")
        assert isinstance(r["is_private"], bool)


def test_gratka_parse_cards():
    html = (FIX / "gratka_cards.html").read_text(encoding="utf-8")
    rows = gratka.parse_cards(html, "house")
    assert rows
    for r in rows:
        assert r["source"] == "gratka"
        assert r["url"].startswith("https://gratka.pl")
        assert r["area"] is None or isinstance(r["area"], float)
        assert r["price"] is None or isinstance(r["price"], int)


def test_nieruchomosci_online_parse_offers():
    html = (FIX / "nol_collection.html").read_text(encoding="utf-8")
    rows = nol.parse_offers(nol.extract_offers(html), "house")
    assert rows
    for r in rows:
        assert r["source"] == "nieruchomosci-online"
        assert r["url"].startswith("https://")
        assert r["price"] is None or isinstance(r["price"], int)


def test_nieruchomosci_online_filters_rentals():
    offers = [
        {"url": "https://x/dom,na-wynajem/1.html", "price": "3000", "itemOffered": {}},
        {"url": "https://x/dom,na-sprzedaz/2.html", "price": "500000", "itemOffered": {}},
    ]
    rows = nol.parse_offers(offers, "house")
    assert len(rows) == 1
    assert "na-sprzedaz" in rows[0]["url"]


def test_nieruchomosci_online_flags_archived():
    # archived ads are returned (flagged) so history can record the ad ending;
    # main.py keeps them out of the dashboard.
    offers = [
        {"url": "https://x/dom,na-sprzedaz/1.html", "price": "500000",
         "availability": "https://schema.org/InStock", "itemOffered": {}},
        {"url": "https://x/dom,na-sprzedaz/2.html", "price": "600000",
         "availability": "https://schema.org/OutOfStock", "itemOffered": {}},
    ]
    rows = nol.parse_offers(offers, "house")
    assert [r["archived"] for r in rows] == [False, True]


def test_gratka_image_is_real_photo_not_icon():
    html = (FIX / "gratka_cards.html").read_text(encoding="utf-8")
    rows = gratka.parse_cards(html, "house")
    imgs = [r["image"] for r in rows if r["image"]]
    assert imgs, "expected at least one gratka photo"
    for src in imgs:
        assert src.startswith("http") and not src.endswith(".svg")
        assert "nuxt-assets" not in src        # not a UI icon
