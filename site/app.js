"use strict";

const PLN = new Intl.NumberFormat("pl-PL");
const SRC_LABEL = { otodom: "Otodom", olx: "OLX", gratka: "Gratka", morizon: "Morizon", "nieruchomosci-online": "n-online" };
const label = (s) => SRC_LABEL[s] || s;
const TYPE_LABEL = { house: "Domy", flat: "Mieszkania" };
const OWNER_LABEL = { private: "Prywatne", agency: "Biura" };
const HIST_LABEL = { relisted: "Wystawione ponownie", dropped: "Z obniżką", sold: "Archiwum", sold_rcn: "Sprzedane wg RCN" };
const MARKET_LABEL = { secondary: "Rynek wtórny", primary: "Inwestycje (rynek pierwotny)" };
const inArchive = () => state.history === "sold" || state.history === "sold_rcn";

// Gliwice neighbourhoods that sometimes arrive as a "locality" -> fold into Gliwice
const GLIWICE_DISTRICTS = new Set([
  "Śródmieście", "Sośnica", "Trynek", "Łabędy", "Wójtowa Wieś", "Szobiszowice",
  "Ostropa", "Żerniki", "Brzezinka", "Stare Gliwice", "Wilcze Gardło", "Bojków",
  "Sikornik", "Zatorze", "Kopernik", "Politechnika", "Obrońców Pokoju",
  "Ligota Zabrska", "Czechowice", "Baildona", "Sośnica Wschód",
]);
const normLoc = (loc) => (!loc ? null : GLIWICE_DISTRICTS.has(loc) ? "Gliwice" : loc);

// town -> [lat, lon]; distance from Gliwice powers the (optional) radius filter.
// Voivodeship-wide this can't cover every village, so the town filter is the
// primary geographic control and distance is just a convenience for known towns.
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
  "Nakło Śląskie": [50.4486, 18.9050], "Orzech": [50.3833, 18.9333], "Nowe Chechło": [50.4242, 18.8200],
  "Rogoźnik": [50.3922, 19.0100], "Sarnów": [50.3556, 19.1700],
  "Turza Śląska": [50.0181, 18.4500], "Kobiór": [50.0600, 18.9400], "Suszec": [50.0000, 18.7400],
  "Czyżowice": [50.0000, 18.4200], "Wodzisław Śląski": [50.0036, 18.4708], "Jastrzębie-Zdrój": [49.9550, 18.5733],
  "Racibórz": [50.0917, 18.2192], "Pszczyna": [49.9794, 18.9447], "Czechowice-Dziedzice": [49.9106, 18.9994],
  "Rydułtowy": [50.0578, 18.4108], "Lubliniec": [50.6678, 18.6886], "Kędzierzyn-Koźle": [50.3494, 18.2261],
  "Myszków": [50.5750, 19.3225], "Goczałkowice-Zdrój": [49.9447, 18.9500], "Skoczów": [49.8000, 18.7900],
  "Bielsko-Biała": [49.8224, 19.0469], "Cieszyn": [49.7497, 18.6300], "Żywiec": [49.6875, 19.1922],
  "Ustroń": [49.7236, 18.8100], "Wisła": [49.6561, 18.8600], "Brenna": [49.7270, 18.9050],
  // added so the radius filter covers more of the voivodeship's larger towns
  "Częstochowa": [50.8118, 19.1203], "Zawiercie": [50.4875, 19.4318], "Jaworzno": [50.2050, 19.2742],
  "Kłobuck": [50.9097, 18.9319], "Łazy": [50.4272, 19.3958], "Poręba": [50.4644, 19.3856],
  "Blachownia": [50.7758, 19.0289], "Koniecpol": [50.7833, 19.6833], "Lubomia": [50.0386, 18.3300],
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

const state = { all: [], archive: null, type: "all", source: "all", owner: "all", history: "all", market: "all", distance: "all", sort: "newest", localities: [] };
let locOptions = [];                         // [ [name, count], ... ] sorted by count
const FILTER_KEY = "rentgen.filters.v2";

const $ = (sel) => document.querySelector(sel);
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cssEsc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
const apply = () => { persist(); render(); };

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
  buildLocalityOptions();
  wireControls();
  wireLocality();
  wireChips();
  wirePinButtons();
  restoreFilters();
  render();
}

function renderStats(meta) {
  if (!meta) return;
  const d = meta.updated ? new Date(meta.updated) : null;
  const when = d ? d.toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" }) : "—";
  const bySrc = Object.entries(meta.by_source || {})
    .map(([s, n]) => `${label(s)} <b>${PLN.format(n)}</b>`).join(" · ");
  const rel = meta.relisted ? ` · <b>${PLN.format(meta.relisted)}</b> ↻ ponownie` : "";
  const arch = meta.archive
    ? ` · <b>${PLN.format(meta.archive)}</b> w archiwum${meta.sold_confirmed ? ` (<b>${PLN.format(meta.sold_confirmed)}</b> sprzedane wg RCN)` : ""}`
    : "";
  $("#stats").innerHTML =
    `<b>${PLN.format(meta.count || 0)}</b> ofert · ${bySrc}${rel}${arch} · zaktualizowano ${when}`;
}

function buildSourceFilter() {
  const present = [...new Set(state.all.flatMap((l) => l.sources || [l.source]))]
    .sort((a, b) => label(a).localeCompare(label(b)));
  $("#source-seg").innerHTML =
    `<button data-val="all" class="active">Wszystkie</button>` +
    present.map((s) => `<button data-val="${s}">${label(s)}</button>`).join("");
}

// ---- locality (town) multi-select -----------------------------------------

function buildLocalityOptions() {
  const counts = new Map();
  for (const l of state.all) {
    const n = normLoc(l.locality);
    if (n) counts.set(n, (counts.get(n) || 0) + 1);
  }
  locOptions = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pl"));
  renderLocalityList("");
}

function renderLocalityList(term) {
  const t = (term || "").trim().toLowerCase();
  const sel = new Set(state.localities);
  const items = locOptions.filter(([n]) => !t || n.toLowerCase().includes(t)).slice(0, 500);
  $("#loc-list").innerHTML = items.length
    ? items.map(([n, c]) =>
        `<label class="ms-item"><input type="checkbox" value="${escapeHtml(n)}" ${sel.has(n) ? "checked" : ""}>` +
        `<span>${escapeHtml(n)}</span><b>${PLN.format(c)}</b></label>`).join("")
    : `<div class="ms-empty">brak miejscowości</div>`;
}

function syncLocalityLabel() {
  const n = state.localities.length;
  const btn = $("#loc-btn");
  if (!btn) return;
  btn.textContent = n === 0 ? "Wszystkie" : n === 1 ? state.localities[0] : `${n} miejscowości`;
  btn.classList.toggle("has-sel", n > 0);
}

function removeLocality(loc) {
  state.localities = state.localities.filter((x) => x !== loc);
  renderLocalityList(($("#loc-search") || {}).value || "");
}

function wireLocality() {
  const pop = $("#loc-pop"), btn = $("#loc-btn");
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    pop.hidden = !pop.hidden;
    if (!pop.hidden) { const s = $("#loc-search"); if (s) s.focus(); }
  });
  pop.addEventListener("click", (e) => e.stopPropagation());
  $("#loc-search").addEventListener("input", (e) => renderLocalityList(e.target.value));
  $("#loc-list").addEventListener("change", (e) => {
    const cb = e.target.closest('input[type="checkbox"]');
    if (!cb) return;
    const set = new Set(state.localities);
    cb.checked ? set.add(cb.value) : set.delete(cb.value);
    state.localities = [...set];
    apply();
  });
  $("#loc-clear").addEventListener("click", () => {
    state.localities = [];
    renderLocalityList($("#loc-search").value);
    apply();
  });
  document.addEventListener("click", (e) => {
    if (!$("#loc-ms").contains(e.target)) pop.hidden = true;
  });
}

// ---- standard controls -----------------------------------------------------

function wireControls() {
  document.querySelectorAll(".seg").forEach((seg) => {
    seg.addEventListener("click", (ev) => {
      const btn = ev.target.closest("button");
      if (!btn) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state[seg.dataset.key] = btn.dataset.val;
      apply();
    });
  });
  let debounce;   // typing a price shouldn't re-render 20k rows per keystroke
  const debouncedApply = () => { clearTimeout(debounce); debounce = setTimeout(apply, 200); };
  ["min-price", "max-price", "min-area", "max-area", "min-rooms", "q"].forEach((id) => {
    const el = $("#" + id);
    if (el) el.addEventListener("input", debouncedApply);
  });
  const sort = $("#sort"); if (sort) sort.addEventListener("change", (e) => { state.sort = e.target.value; apply(); });
  const dist = $("#distance"); if (dist) dist.addEventListener("change", (e) => { state.distance = e.target.value; apply(); });
}

// ---- persistence (localStorage + shareable URL) ----------------------------

function snapshot() {
  return {
    type: state.type, source: state.source, owner: state.owner, history: state.history,
    market: state.market, distance: state.distance, sort: state.sort, localities: state.localities,
    minPrice: $("#min-price").value, maxPrice: $("#max-price").value,
    minArea: $("#min-area").value, maxArea: $("#max-area").value,
    minRooms: $("#min-rooms").value, q: $("#q").value,
  };
}

function isDefault(s) {
  return s.type === "all" && s.source === "all" && s.owner === "all" && s.history === "all" &&
    (!s.market || s.market === "all") &&
    s.distance === "all" && s.sort === "newest" && (!s.localities || !s.localities.length) &&
    !s.minPrice && !s.maxPrice && !s.minArea && !s.maxArea && !s.minRooms && !s.q;
}

function persist() {
  const snap = snapshot();
  try { localStorage.setItem(FILTER_KEY, JSON.stringify(snap)); } catch (e) {}
  try {
    const url = isDefault(snap)
      ? location.pathname
      : location.pathname + "?f=" + encodeURIComponent(JSON.stringify(snap));
    history.replaceState(null, "", url);
  } catch (e) {}
}

function restoreFilters() {
  let snap = null;
  try { const p = new URLSearchParams(location.search).get("f"); if (p) snap = JSON.parse(p); } catch (e) {}
  if (!snap) { try { snap = JSON.parse(localStorage.getItem(FILTER_KEY) || "null"); } catch (e) {} }
  if (snap) applySnapshot(snap);
}

function setVal(id, v) { const el = $("#" + id); if (el && v != null) el.value = v; }

function setSeg(key, val) {
  if (val == null) return;
  const seg = document.querySelector(`.seg[data-key="${key}"]`);
  if (!seg) return;
  const v = seg.querySelector(`button[data-val="${cssEsc(val)}"]`) ? val : "all";
  state[key] = v;
  seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.val === v));
}

function applySnapshot(s) {
  ["type", "source", "owner", "history", "market"].forEach((k) => setSeg(k, s[k]));
  if (s.distance != null) { state.distance = s.distance; const d = $("#distance"); if (d) d.value = s.distance; }
  if (s.sort != null) { state.sort = s.sort; const so = $("#sort"); if (so) so.value = s.sort; }
  state.localities = Array.isArray(s.localities) ? s.localities.slice() : [];
  setVal("min-price", s.minPrice); setVal("max-price", s.maxPrice);
  setVal("min-area", s.minArea); setVal("max-area", s.maxArea);
  setVal("min-rooms", s.minRooms); setVal("q", s.q);
  renderLocalityList("");
}

function resetAll() {
  ["type", "source", "owner", "history", "market"].forEach((k) => setSeg(k, "all"));
  state.distance = "all"; const d = $("#distance"); if (d) d.value = "all";
  state.sort = "newest"; const so = $("#sort"); if (so) so.value = "newest";
  state.localities = [];
  ["min-price", "max-price", "min-area", "max-area", "min-rooms", "q"].forEach((id) => {
    const el = $("#" + id); if (el) el.value = "";
  });
  renderLocalityList(($("#loc-search") || {}).value || "");
  apply();
}

// ---- active-filter chips ---------------------------------------------------

function activeFilters() {
  const out = [];
  if (state.type !== "all") out.push({ k: "seg:type", label: "Typ: " + (TYPE_LABEL[state.type] || state.type) });
  if (state.source !== "all") out.push({ k: "seg:source", label: "Źródło: " + label(state.source) });
  if (state.owner !== "all") out.push({ k: "seg:owner", label: OWNER_LABEL[state.owner] || state.owner });
  if (state.history !== "all") out.push({ k: "seg:history", label: HIST_LABEL[state.history] || state.history });
  if (state.market !== "all") out.push({ k: "seg:market", label: MARKET_LABEL[state.market] || state.market });
  if (state.distance !== "all") out.push({ k: "distance", label: "≤ " + state.distance + " km od Gliwic" });
  state.localities.forEach((loc) => out.push({ k: "loc:" + loc, label: loc }));
  const nf = (id, lab) => { const v = ($("#" + id).value || "").trim(); if (v) out.push({ k: "num:" + id, label: lab + " " + v }); };
  nf("min-price", "Cena od"); nf("max-price", "Cena do");
  nf("min-area", "m² od"); nf("max-area", "m² do"); nf("min-rooms", "Pokoje od");
  const q = ($("#q").value || "").trim();
  if (q) out.push({ k: "q", label: "„" + q + "”" });
  return out;
}

function renderChips() {
  const af = activeFilters();
  const el = $("#chips");
  if (!el) return;
  if (!af.length) { el.innerHTML = ""; el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML =
    af.map((c) => `<button class="chip" data-k="${escapeHtml(c.k)}">${escapeHtml(c.label)} <span class="x">✕</span></button>`).join("") +
    `<button class="chip reset" data-k="__all__">Wyczyść wszystko</button>`;
}

function wireChips() {
  $("#chips").addEventListener("click", (e) => {
    const b = e.target.closest("button.chip");
    if (!b) return;
    const k = b.dataset.k;
    if (k === "__all__") { resetAll(); return; }
    if (k.startsWith("seg:")) setSeg(k.slice(4), "all");
    else if (k === "distance") { state.distance = "all"; const d = $("#distance"); if (d) d.value = "all"; }
    else if (k.startsWith("loc:")) removeLocality(k.slice(4));
    else if (k.startsWith("num:")) { const el = $("#" + k.slice(4)); if (el) el.value = ""; }
    else if (k === "q") { const el = $("#q"); if (el) el.value = ""; }
    apply();
  });
}

// ---- filtering + rendering -------------------------------------------------

function currentFilters() {
  const num = (id) => { const v = parseFloat($("#" + id).value); return Number.isFinite(v) ? v : null; };
  return {
    minPrice: num("min-price"), maxPrice: num("max-price"),
    minArea: num("min-area"), maxArea: num("max-area"),
    minRooms: num("min-rooms"), q: $("#q").value.trim().toLowerCase(),
    locs: state.localities.length ? new Set(state.localities) : null,
  };
}

function passes(l, f) {
  const archiveMode = inArchive();
  if (state.history === "sold_rcn" && !l.sold) return false;
  if (state.market === "primary" && !l.development) return false;
  if (state.market === "secondary" && l.development) return false;
  if (state.type !== "all" && l.type !== state.type) return false;
  if (state.source !== "all" && !(l.sources || [l.source]).includes(state.source)) return false;
  if (!archiveMode && state.owner === "private" && l.is_private !== true) return false;
  if (!archiveMode && state.owner === "agency" && l.is_private !== false) return false;
  if (state.history === "relisted" && !l.relisted) return false;
  if (state.history === "dropped") {
    const ph = (l.price_history || []).map((x) => x.price).filter((x) => x != null);
    if (!(ph.length > 1 && ph[ph.length - 1] < Math.max(...ph))) return false;
  }
  if (f.locs) {
    const n = normLoc(l.locality);
    if (!n || !f.locs.has(n)) return false;
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

async function loadArchive() {
  if (state.archive) return state.archive;
  try {
    const a = await fetch("data/archive.json", { cache: "no-store" }).then((r) => r.json());
    state.archive = Array.isArray(a) ? a : [];
  } catch (e) {
    state.archive = [];
  }
  return state.archive;
}

// Chunked rendering: with ~20k listings, building the whole grid at once
// freezes the page for seconds on every filter click. Render the first CHUNK,
// then let an IntersectionObserver append more as the user scrolls near the end.
const CHUNK = 60;
let view = [];          // current filtered+sorted rows
let rendered = 0;       // how many of them are in the DOM
let moreObserver = null;

function appendChunk() {
  const sentinel = $("#more-sentinel");
  if (!sentinel || rendered >= view.length) return;
  const next = view.slice(rendered, rendered + CHUNK);
  rendered += next.length;
  sentinel.insertAdjacentHTML("beforebegin", next.map(card).join(""));
  sentinel.hidden = rendered >= view.length;
}

function watchSentinel() {
  if (!moreObserver) {
    moreObserver = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) appendChunk();
    }, { rootMargin: "1500px" });
  }
  moreObserver.disconnect();
  const sentinel = $("#more-sentinel");
  if (sentinel) moreObserver.observe(sentinel);
}

function render() {
  if (inArchive() && !state.archive) {
    $("#grid").innerHTML = `<div class="empty">Wczytywanie archiwum…</div>`;
    loadArchive().then(render);
    return;
  }
  const f = currentFilters();
  const pool = inArchive() ? state.archive : state.all;
  const sorter = inArchive() && state.sort === "newest"
    ? (a, b) => (b.delisted || "").localeCompare(a.delisted || "")
    : (sorters[state.sort] || sorters.newest);
  view = pool.filter((l) => passes(l, f)).sort(sorter);
  rendered = 0;
  $("#count").textContent = view.length ? `${PLN.format(view.length)} wyników` : "";
  $("#grid").innerHTML = view.length
    ? `<div id="more-sentinel" class="sentinel"></div>`
    : `<div class="empty">Brak ofert dla wybranych filtrów.</div>`;
  appendChunk();
  watchSentinel();
  syncLocalityLabel();
  renderChips();
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

// ---- property lifetime timeline ("rentgen" view) ---------------------------

function tlLabel(e) {
  const p = e.price != null ? `${PLN.format(e.price)} zł` : "";
  const src = e.source ? label(e.source) : "";
  switch (e.kind) {
    case "sale_past":
      return `<b class="tl-sale">🔑 sprzedane (akt notarialny)</b> ${p}` +
             (e.market ? ` · rynek ${e.market}` : "") +
             (e.confidence ? ` · pewność: ${e.confidence}` : "");
    case "sale":
      return `<b class="tl-sale">✓ sprzedane wg RCN</b> ${p}` +
             (e.confidence ? ` · pewność: ${e.confidence}` : "");
    case "listed":
      return `wystawione na ${src}${p ? " — " + p : ""}`;
    case "relist":
      return `↻ wystawione ponownie (${src})${p ? " — " + p : ""}`;
    case "price":
      return `zmiana ceny → <b>${p}</b>${src ? ` (${src})` : ""}`;
    case "archived":
      return `ogłoszenie zarchiwizowane${src ? ` (${src})` : ""}`;
    case "delisted":
      return `<b>zniknęło z portali</b> — wycofane lub sprzedane`;
    default:
      return e.kind;
  }
}

function timelineBlock(l) {
  const tl = l.timeline || [];
  const photos = l.photo_urls || [];
  if (tl.length < 2 && !photos.length && !(l.sales || []).length) return "";
  const rows = tl.map((e) =>
    `<div class="tl-row"><span class="tl-date">${e.date || ""}</span><span class="tl-what">${tlLabel(e)}</span></div>`
  ).join("");
  const ph = photos.length
    ? `<div class="tl-photos">zdjęcia z ogłoszeń: ${photos.map((u, i) =>
        `<a href="${u}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${i + 1}</a>`).join(" ")}</div>`
    : "";
  return `<details class="tl" onclick="event.stopPropagation()">
    <summary>Historia nieruchomości (${tl.length})</summary>
    <div class="tl-body">${rows}${ph}</div>
  </details>`;
}

function soldBanner(l) {
  if (l.sold && l.sold.price != null) {
    const pm2 = l.sold.price_m2 ? ` (${PLN.format(l.sold.price_m2)} zł/m²)` : "";
    return `<div class="soldline">✓ sprzedane ${l.sold.date} za <b>${PLN.format(l.sold.price)} zł</b>${pm2} · RCN, pewność: ${l.sold.confidence}</div>`;
  }
  if (l.delisted) {
    return `<div class="goneline">zniknęło z portali ${l.delisted} — wycofane lub sprzedane</div>`;
  }
  return "";
}

function pastSaleLine(l) {
  const past = (l.sales || []).filter((s) => s.kind === "past" && s.price != null);
  if (!past.length) return "";
  const s = past[past.length - 1];
  return `<div class="pastsale">🔑 poprzednio sprzedane ${s.date} za <b>${PLN.format(s.price)} zł</b> (akt not., pewność: ${s.confidence})</div>`;
}

// ---- "uzupelnij adres" -> ready-to-paste rcncheck --pin command -------------

function pinBlock(l) {
  if (!l.url) return "";
  const extra = l.type === "flat"
    ? `<input class="pin-x" data-flag="--pietro" placeholder="piętro" inputmode="numeric">`
    : `<input class="pin-x" data-flag="--dzialka" placeholder="działka m²" inputmode="numeric">`;
  return `<details class="pinbox" onclick="event.stopPropagation()">
    <summary>📍 znasz adres? sprawdź w RCN</summary>
    <div class="pin-form"
         data-url="${escapeHtml(l.url)}" data-area="${l.area ?? ""}"
         data-type="${l.type}" data-loc="${escapeHtml(normLoc(l.locality) || l.locality || "")}"
         data-rooms="${l.rooms ?? ""}">
      <input class="pin-ul" placeholder="ulica, np. Daszyńskiego" value="${escapeHtml(l.street || "")}">
      <input class="pin-nr" placeholder="nr">
      ${extra}
      <button type="button" class="pin-check">Sprawdź w RCN</button>
      <button type="button" class="pin-copy" title="komenda przypina adres do ogłoszenia na stałe (overrides.json)">📌 Kopiuj</button>
      <div class="pin-results" hidden></div>
      <div class="pin-hint">„Sprawdź" działa od razu w przeglądarce (GUGiK: geokoder + działka +
        akty notarialne). „📌 Kopiuj" daje komendę do terminala, która przypina adres na stałe.</div>
    </div>
  </details>`;
}

// ---- in-browser RCN check (UUG geocoder -> ULDK parcel -> WFS deeds) --------

async function uugResolve(loc, ul, nr) {
  const addr = `${loc}, ${ul} ${nr}`.trim();
  const r = await fetch("https://services.gugik.gov.pl/uug/?request=GetAddress&address=" +
                        encodeURIComponent(addr));
  const d = await r.json();
  const res = d && d.results && d.results["1"];
  if (!res) return null;
  return { street: res.street, number: res.number,
           x: parseFloat(res.x), y: parseFloat(res.y) };
}

async function uldkParcel(x, y) {
  const r = await fetch(`https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy=${x},${y},2180&result=id,region`);
  const lines = (await r.text()).trim().split("\n");
  if (lines[0].trim() !== "0" || !lines[1]) return null;
  const p = lines[1].split("|");
  return { id: p[0].trim(), obreb: (p[1] || "").trim() };
}

const _MS_NS = "http://mapserver.gis.umn.edu/mapserver";

async function rcnDeedsNear(x, y, layer, radius = 60) {
  // WFS bbox in the layer's native EPSG:2180 axis order: northing first.
  // 60 m around the UUG address point covers the building; a bigger radius in
  // a dense city block overflows the feature cap and silently drops deeds.
  const bbox = `${y - radius},${x - radius},${y + radius},${x + radius}`;
  const url = "https://mapy.geoportal.gov.pl/wss/service/rcn?service=WFS&version=2.0.0" +
              `&request=GetFeature&typeNames=ms:${layer}&count=500&bbox=${bbox}`;
  const doc = new DOMParser().parseFromString(await (await fetch(url)).text(), "text/xml");
  const g = (f, n) => { const el = f.getElementsByTagNameNS(_MS_NS, n)[0];
                        return el ? el.textContent.trim() : ""; };
  const out = [];
  for (const f of doc.getElementsByTagNameNS(_MS_NS, layer)) {
    const pfx = layer === "lokale" ? "lok" : "bud";
    const trans = g(f, "tran_rodzaj_trans");
    if (trans && trans !== "wolnyRynek") continue;      // skip auctions etc.
    out.push({
      layer,
      date: g(f, "dok_data").slice(0, 10),
      price: parseFloat(g(f, `${pfx}_cena_brutto`)) || parseFloat(g(f, "tran_cena_brutto")) || null,
      area: parseFloat(g(f, `${pfx}_pow_uzyt`)) || null,
      rooms: layer === "lokale" ? g(f, "lok_liczba_izb") : "",
      grunt: layer === "budynki" ? g(f, "nier_pow_gruntu") : "",
      market: g(f, "tran_rodzaj_rynku"),
      addr: g(f, `${pfx}_adres`),
    });
  }
  return out;
}

function addrNr(addrStr) {
  const m = /NR_PORZ:([^;]+)/.exec(addrStr || "");
  return m ? m[1].trim().toLowerCase().replace(/[^0-9a-z/]/g, "") : null;
}

async function runRcnCheck(box, btn) {
  const results = box.querySelector(".pin-results");
  const ulEl = box.querySelector(".pin-ul");
  const nr = box.querySelector(".pin-nr").value.trim();
  const loc = box.dataset.loc;
  results.hidden = false;
  if (!ulEl.value.trim() || !nr) { results.innerHTML = "podaj ulicę i numer budynku"; return; }
  btn.disabled = true; btn.textContent = "Sprawdzam…";
  try {
    const geo = await uugResolve(loc, ulEl.value.trim(), nr);
    if (!geo) { results.innerHTML = "GUGiK nie zna takiego adresu — sprawdź pisownię"; return; }
    if (geo.street) ulEl.value = geo.street;   // autofill the canonical name
    const wantNr = nr.toLowerCase().replace(/[^0-9a-z/]/g, "");
    const nrOk = geo.number && geo.number.toLowerCase().replace(/[^0-9a-z/]/g, "") === wantNr;
    let head = `<b>ul. ${escapeHtml(geo.street || ulEl.value)} ${escapeHtml(nr)}, ${escapeHtml(loc)}</b>`;
    if (nrOk) {
      const parcel = await uldkParcel(geo.x, geo.y);
      if (parcel) head += ` · działka ${escapeHtml(parcel.id)}${parcel.obreb ? ` (${escapeHtml(parcel.obreb)})` : ""}`;
    } else {
      head += ` · <i>geokoder nie potwierdził numeru ${escapeHtml(nr)} — wyniki mogą być przybliżone</i>`;
    }
    const [lok, bud] = await Promise.all([
      rcnDeedsNear(geo.x, geo.y, "lokale"), rcnDeedsNear(geo.x, geo.y, "budynki")]);
    let deeds = [...lok, ...bud];
    if (nrOk) deeds = deeds.filter((d) => addrNr(d.addr) === wantNr);
    deeds.sort((a, b) => (a.date || "").localeCompare(b.date || ""));
    const rows = deeds.map((d) => {
      const bits = [d.date,
        d.price != null ? `<b>${PLN.format(d.price)} zł</b>` : "cena ?",
        d.area != null ? `${d.area} m²` : null,
        d.market ? `rynek ${d.market.startsWith("p") ? "pierwotny" : "wtórny"}` : null,
        d.layer === "lokale" ? (d.rooms ? `${d.rooms} izb` : null)
                             : (d.grunt ? `działka ${d.grunt} m²` : null),
      ].filter(Boolean).join(" · ");
      return `<div class="tl-row"><span class="tl-what">${d.layer === "lokale" ? "🏠" : "🏡"} ${bits}</span></div>`;
    }).join("");
    results.innerHTML = head + (deeds.length
      ? `<div class="pin-deeds">${rows}</div>`
      : `<div class="pin-deeds">brak aktów notarialnych dla tego ${nrOk ? "budynku" : "miejsca"} w RCN (rejestr od ~2000 r.)</div>`);
  } catch (err) {
    results.innerHTML = "błąd połączenia z usługami GUGiK — spróbuj ponownie";
  } finally {
    btn.disabled = false; btn.textContent = "Sprawdź w RCN";
  }
}

function buildPinCommand(box) {
  const q = (v) => `"${String(v).replace(/"/g, "")}"`;
  const val = (sel) => { const el = box.querySelector(sel); return el ? el.value.trim() : ""; };
  const parts = ["python -m scraper.rcncheck", q(box.dataset.loc || "?")];
  if (box.dataset.area) parts.push(box.dataset.area);
  const ul = val(".pin-ul"), nr = val(".pin-nr");
  if (ul) parts.push("--ulica", q(ul));
  if (nr) parts.push("--nr", nr);
  const x = box.querySelector(".pin-x");
  if (x && x.value.trim()) parts.push(x.dataset.flag, x.value.trim());
  if (box.dataset.type === "house") parts.push("--typ", "house");
  else if (box.dataset.rooms) parts.push("--pokoje", box.dataset.rooms);
  parts.push("--pin", q(box.dataset.url));
  return parts.join(" ");
}

function wirePinButtons() {
  $("#grid").addEventListener("click", async (e) => {
    const check = e.target.closest(".pin-check");
    if (check) {
      e.stopPropagation();
      runRcnCheck(check.closest(".pin-form"), check);
      return;
    }
    const btn = e.target.closest(".pin-copy");
    if (!btn) return;
    e.stopPropagation();
    const cmd = buildPinCommand(btn.closest(".pin-form"));
    try {
      await navigator.clipboard.writeText(cmd);
      btn.textContent = "Skopiowano ✓";
    } catch (err) {
      window.prompt("Skopiuj komendę:", cmd);
    }
    setTimeout(() => { btn.textContent = "📌 Kopiuj"; }, 2500);
  });
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
  const gone = !!l.delisted;
  return `<div class="card${gone ? " gone" : ""}" ${l.url ? `onclick="window.open('${l.url}','_blank','noopener')"` : ""}>
    <div class="thumb">${img}
      <div class="badges">${badges}</div>
      ${owner ? `<span class="tag-priv">${owner}</span>` : ""}
      ${l.development ? `<span class="tag-dev">inwestycja</span>` : ""}
      ${gone ? `<span class="tag-gone${l.sold ? " sold" : ""}">${l.sold ? "sprzedane" : "wycofane"}</span>` : ""}
    </div>
    <div class="body">
      <div class="price">${priceLabel(l)}</div>
      ${ppm ? `<div class="ppm">${ppm}</div>` : ""}
      ${facts ? `<div class="facts">${facts}</div>` : ""}
      ${loc ? `<div class="loc">${loc}</div>` : ""}
      <div class="title">${l.title || ""}</div>
      ${soldBanner(l)}
      ${pastSaleLine(l)}
      ${historyBlock(l)}
      ${offersBlock(l)}
      ${timelineBlock(l)}
      ${pinBlock(l)}
    </div>
  </div>`;
}

boot();
