"use strict";

const PLN = new Intl.NumberFormat("pl-PL");
const SRC_LABEL = { otodom: "Otodom", olx: "OLX", gratka: "Gratka", morizon: "Morizon", "nieruchomosci-online": "n-online" };
const label = (s) => SRC_LABEL[s] || s;

// Gliwice neighbourhoods that sometimes arrive as a "locality" -> fold into Gliwice
const GLIWICE_DISTRICTS = new Set([
  "Śródmieście", "Sośnica", "Trynek", "Łabędy", "Wójtowa Wieś", "Szobiszowice",
  "Ostropa", "Żerniki", "Brzezinka", "Stare Gliwice", "Wilcze Gardło", "Bojków",
  "Sikornik", "Zatorze", "Kopernik", "Politechnika", "Obrońców Pokoju",
  "Ligota Zabrska", "Czechowice", "Baildona", "Sośnica Wschód",
]);
const normLoc = (loc) => (!loc ? null : GLIWICE_DISTRICTS.has(loc) ? "Gliwice" : loc);

// town -> [lat, lon]; distance from Gliwice powers the radius filter
const GLIWICE = [50.2945, 18.6714];
const TOWN_COORDS = {
  "Gliwice": [50.2945, 18.6714], "Knurów": [50.2197, 18.6741], "Pyskowice": [50.3958, 18.6286],
  "Gierałtowice": [50.2069, 18.7333], "Pilchowice": [50.1814, 18.6047], "Sośnicowice": [50.2206, 18.5378],
  "Toszek": [50.4586, 18.5219], "Rudziniec": [50.2978, 18.4319], "Wielowieś": [50.4153, 18.5639],
  "Przyszowice": [50.2331, 18.7039], "Paniówki": [50.2206, 18.6919], "Chudów": [50.1947, 18.7256],
  "Żernica": [50.2050, 18.6200], "Zbrosławice": [50.3686, 18.7339], "Wieszowa": [50.3650, 18.8050],
  "Rzeczyce": [50.4000, 18.7200], "Tarnowskie Góry": [50.4456, 18.8625], "Tworóg": [50.4486, 18.7250],
  "Świerklaniec": [50.4072, 18.9072], "Radzionków": [50.3917, 18.9189], "Miasteczko Śląskie": [50.5036, 18.9558],
  "Ożarowice": [50.4661, 18.9803], "Kalety": [50.5503, 18.8806], "Zabrze": [50.3249, 18.7857],
  "Bytom": [50.3483, 18.9157], "Ruda Śląska": [50.2558, 18.8556], "Świętochłowice": [50.2917, 18.9181],
  "Chorzów": [50.2974, 18.9544], "Katowice": [50.2649, 19.0238], "Siemianowice Śląskie": [50.3079, 19.0292],
  "Piekary Śląskie": [50.3826, 18.9497], "Mysłowice": [50.2074, 19.1665], "Sosnowiec": [50.2863, 19.1041],
  "Czeladź": [50.3300, 19.0820], "Będzin": [50.3275, 19.1281], "Dąbrowa Górnicza": [50.3217, 19.1875],
  "Wojkowice": [50.3667, 19.0333], "Psary": [50.3614, 19.1497], "Bobrowniki": [50.3683, 19.0500],
  "Mikołów": [50.1672, 18.9006], "Łaziska Górne": [50.1497, 18.8431], "Orzesze": [50.1547, 18.7242],
  "Ornontowice": [50.1819, 18.7375], "Wyry": [50.1486, 18.9097], "Tychy": [50.1372, 18.9664],
  "Bieruń": [50.0894, 19.0900], "Lędziny": [50.1453, 19.1339], "Imielin": [50.1417, 19.1869],
  "Rybnik": [50.0972, 18.5463], "Żory": [50.0469, 18.7008], "Czerwionka-Leszczyny": [50.1497, 18.6747],
  "Gaszowice": [50.0728, 18.4544], "Jejkowice": [50.1131, 18.4831], "Lyski": [50.1064, 18.4047],
  "Świerklany": [50.0089, 18.6394], "Marklowice": [50.0292, 18.4956], "Kuźnia Raciborska": [50.2017, 18.3186],
  "Nędza": [50.1900, 18.3320],
  // wider ring (mostly 20-45 km) so radii are complete and far cities sort out correctly
  "Nakło Śląskie": [50.4486, 18.9050], "Orzech": [50.3833, 18.9333], "Nowe Chechło": [50.4242, 18.8200],
  "Rogoźnik": [50.3922, 19.0100], "Sarnów": [50.3556, 19.1700],
  "Turza Śląska": [50.0181, 18.4500], "Kobiór": [50.0600, 18.9400], "Suszec": [50.0000, 18.7400],
  "Czyżowice": [50.0000, 18.4200], "Wodzisław Śląski": [50.0036, 18.4708], "Jastrzębie-Zdrój": [49.9550, 18.5733],
  "Racibórz": [50.0917, 18.2192], "Pszczyna": [49.9794, 18.9447], "Czechowice-Dziedzice": [49.9106, 18.9994],
  "Rydułtowy": [50.0578, 18.4108], "Lubliniec": [50.6678, 18.6886], "Kędzierzyn-Koźle": [50.3494, 18.2261],
  "Myszków": [50.5750, 19.3225], "Goczałkowice-Zdrój": [49.9447, 18.9500], "Skoczów": [49.8000, 18.7900],
  "Bielsko-Biała": [49.8224, 19.0469], "Cieszyn": [49.7497, 18.6300], "Żywiec": [49.6875, 19.1922],
  "Ustroń": [49.7236, 18.8100], "Wisła": [49.6561, 18.8600], "Brenna": [49.7270, 18.9050],
};
function haversine(a, b) {
  const R = 6371, p = Math.PI / 180;
  const dLa = (b[0] - a[0]) * p, dLo = (b[1] - a[1]) * p;
  const h = Math.sin(dLa / 2) ** 2 + Math.cos(a[0] * p) * Math.cos(b[0] * p) * Math.sin(dLo / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(h)));
}
function distOf(locality) {
  const n = normLoc(locality);
  const c = n && TOWN_COORDS[n];
  return c ? haversine(GLIWICE, c) : null;
}

const state = { all: [], type: "all", source: "all", owner: "all", history: "all", distance: "all", sort: "newest" };
const $ = (sel) => document.querySelector(sel);

async function boot() {
  try {
    const [listings, meta] = await Promise.all([
      fetch("data/listings.json", { cache: "no-store" }).then((r) => r.json()),
      fetch("data/meta.json", { cache: "no-store" }).then((r) => r.json()).catch(() => null),
    ]);
    state.all = Array.isArray(listings) ? listings : [];
    renderStats(meta);
  } catch (e) {
    $("#grid").innerHTML =
      `<div class="empty">Nie udało się wczytać danych (data/listings.json).</div>`;
    return;
  }
  buildSourceFilter();
  wireControls();
  render();
}

function renderStats(meta) {
  if (!meta) return;
  const d = meta.updated ? new Date(meta.updated) : null;
  const when = d ? d.toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" }) : "—";
  const bySrc = Object.entries(meta.by_source || {})
    .map(([s, n]) => `${label(s)} <b>${PLN.format(n)}</b>`).join(" · ");
  const rel = meta.relisted ? ` · <b>${PLN.format(meta.relisted)}</b> ↻ ponownie` : "";
  $("#stats").innerHTML =
    `<b>${PLN.format(meta.count || 0)}</b> ofert · ${bySrc}${rel} · zaktualizowano ${when}`;
}

function buildSourceFilter() {
  const present = [...new Set(state.all.flatMap((l) => l.sources || [l.source]))]
    .sort((a, b) => label(a).localeCompare(label(b)));
  $("#source-seg").innerHTML =
    `<button data-val="all" class="active">Wszystkie</button>` +
    present.map((s) => `<button data-val="${s}">${label(s)}</button>`).join("");
}

function wireControls() {
  document.querySelectorAll(".seg").forEach((seg) => {
    seg.addEventListener("click", (ev) => {
      const btn = ev.target.closest("button");
      if (!btn) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state[seg.dataset.key] = btn.dataset.val;
      render();
    });
  });
  ["min-price", "max-price", "min-area", "max-area", "min-rooms", "q"].forEach((id) => {
    const el = $("#" + id);
    if (el) el.addEventListener("input", render);
  });
  const sort = $("#sort"); if (sort) sort.addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  const dist = $("#distance"); if (dist) dist.addEventListener("change", (e) => { state.distance = e.target.value; render(); });
}

function currentFilters() {
  const num = (id) => { const v = parseFloat($("#" + id).value); return Number.isFinite(v) ? v : null; };
  return {
    minPrice: num("min-price"), maxPrice: num("max-price"),
    minArea: num("min-area"), maxArea: num("max-area"),
    minRooms: num("min-rooms"), q: $("#q").value.trim().toLowerCase(),
  };
}

function passes(l, f) {
  if (state.type !== "all" && l.type !== state.type) return false;
  if (state.source !== "all" && !(l.sources || [l.source]).includes(state.source)) return false;
  if (state.owner === "private" && l.is_private !== true) return false;
  if (state.owner === "agency" && l.is_private !== false) return false;
  if (state.history === "relisted" && !l.relisted) return false;
  if (state.history === "dropped") {
    const ph = (l.price_history || []).map((x) => x.price).filter((x) => x != null);
    if (!(ph.length > 1 && ph[ph.length - 1] < Math.max(...ph))) return false;
  }
  if (state.distance !== "all") {
    const d = distOf(l.locality);
    if (d == null || d > Number(state.distance)) return false;
  }
  if (f.minPrice != null && (l.price == null || l.price < f.minPrice)) return false;
  if (f.maxPrice != null && (l.price == null || l.price > f.maxPrice)) return false;
  if (f.minArea != null && (l.area == null || l.area < f.minArea)) return false;
  if (f.maxArea != null && (l.area == null || l.area > f.maxArea)) return false;
  if (f.minRooms != null && (l.rooms == null || l.rooms < f.minRooms)) return false;
  if (f.q) {
    const hay = `${l.title || ""} ${l.locality || ""} ${l.district || ""}`.toLowerCase();
    if (!hay.includes(f.q)) return false;
  }
  return true;
}

const sorters = {
  newest: (a, b) => (b.created || "").localeCompare(a.created || ""),
  price_asc: (a, b) => (a.price ?? Infinity) - (b.price ?? Infinity),
  price_desc: (a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity),
  ppm_asc: (a, b) => (a.price_per_m2 ?? Infinity) - (b.price_per_m2 ?? Infinity),
  area_desc: (a, b) => (b.area ?? -Infinity) - (a.area ?? -Infinity),
};

function render() {
  const f = currentFilters();
  const rows = state.all.filter((l) => passes(l, f)).sort(sorters[state.sort] || sorters.newest);
  $("#count").textContent = rows.length ? `${PLN.format(rows.length)} wyników` : "";
  $("#grid").innerHTML = rows.length
    ? rows.map(card).join("")
    : `<div class="empty">Brak ofert dla wybranych filtrów.</div>`;
}

function priceLabel(l) {
  if (l.price == null) return "Cena: zapytaj";
  if (l.price_max != null && l.price_max !== l.price)
    return `<span class="cheap">${PLN.format(l.price)} zł</span><span class="pmax">do ${PLN.format(l.price_max)} zł</span>`;
  return `${PLN.format(l.price)} zł`;
}

function offersBlock(l) {
  const offers = l.offers || [];
  if (offers.length < 2) return "";
  const cheapUrl = l.cheapest && l.cheapest.url;
  const multiPrice = l.price_max != null && l.price_max !== l.price;
  const rows = offers.map((o) => {
    const p = o.price != null ? `${PLN.format(o.price)} zł` : "zapytaj";
    const dd = o.created ? ` · ${o.created.slice(0, 10)}` : "";
    const best = multiPrice && o.url === cheapUrl ? `<span class="best">najtaniej</span>` : "";
    return `<a href="${o.url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${label(o.source)} — ${p}${best}${dd}</a>`;
  }).join("");
  return `<div class="offers"><div class="offers-h">Ta sama nieruchomość na ${offers.length} ofertach:</div>${rows}</div>`;
}

function historyBlock(l) {
  const bits = [];
  if (l.relisted) bits.push(`<span class="relist">↻ wystawiane ponownie</span>`);
  const ph = (l.price_history || []).filter((x) => x.price != null);
  const also = l.also_listed || [];
  if (also.length) {
    const t = also.map((o) => (o.price != null ? `${PLN.format(o.price)} zł` : "?")).join(", ");
    bits.push(`<span class="trail">także wystawione: ${t}</span>`);
  } else if (ph.length > 1) {
    bits.push(`<span class="trail">${ph.map((x) => PLN.format(x.price)).join(" → ")} zł</span>`);
  } else if (l.relisted && l.prev_price != null) {
    bits.push(`<span class="trail">wcześniej ${PLN.format(l.prev_price)} zł</span>`);
  }
  if (l.first_seen) bits.push(`<span class="since">na rynku od ${l.first_seen}</span>`);
  return bits.length ? `<div class="hist">${bits.join(" · ")}</div>` : "";
}

function card(l) {
  const ppm = l.price_per_m2 != null ? `${PLN.format(l.price_per_m2)} zł/m²` : "";
  const facts = [
    l.area != null ? `${PLN.format(l.area)} m²` : null,
    l.rooms != null ? `${l.rooms} pok.` : null,
    l.type === "house" && l.plot_area != null ? `działka ${PLN.format(l.plot_area)} m²` : null,
  ].filter(Boolean).join(" · ");
  const town = normLoc(l.locality);
  const td = distOf(l.locality);
  const townLabel = town ? (td ? `${town} • ${td} km` : town) : null;
  const loc = [townLabel, l.district].filter(Boolean).join(", ");
  const img = l.image
    ? `<img loading="lazy" src="${l.image}" onerror="this.style.display='none'">`
    : `<div class="noimg">bez zdjęcia</div>`;
  const owner = l.is_private === true ? "prywatne" : l.is_private === false ? "biuro" : "";
  const badges = (l.sources || [l.source]).map((s) => `<span class="badge ${s}">${label(s)}</span>`).join("");
  return `<div class="card" onclick="window.open('${l.url}','_blank','noopener')">
    <div class="thumb">${img}
      <div class="badges">${badges}</div>
      ${owner ? `<span class="tag-priv">${owner}</span>` : ""}
    </div>
    <div class="body">
      <div class="price">${priceLabel(l)}</div>
      ${ppm ? `<div class="ppm">${ppm}</div>` : ""}
      ${facts ? `<div class="facts">${facts}</div>` : ""}
      ${loc ? `<div class="loc">${loc}</div>` : ""}
      <div class="title">${l.title || ""}</div>
      ${historyBlock(l)}
      ${offersBlock(l)}
    </div>
  </div>`;
}

boot();
