"use strict";

/* Statystyki: renders site/data/stats.json (weekly listing series + monthly
   RCN deed series) as hand-rolled responsive SVG charts. No libraries. */

const PLN = new Intl.NumberFormat("pl-PL");
// data lives per voivodeship in data/<region>/ — same convention as app.js
const REGION = ((new URLSearchParams(location.search).get("region") || "slaskie")
  .replace(/[^a-z-]/g, "")) || "slaskie";
const DATA = `data/${REGION}`;
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// series identity is fixed: a series keeps its color no matter what's visible
const COL = { ask: "var(--s1)", rcnW: "var(--s2)", rcnP: "var(--s3)" };
const NAME = { ask: "oferty (cena ofertowa)", rcnW: "transakcje RCN — wtórny", rcnP: "transakcje RCN — pierwotny" };

const state = { data: null, gap: null, town: "", type: "flat", range: "60" };

async function boot() {
  try {
    const [data, rcnstats] = await Promise.all([
      fetch(`${DATA}/stats.json`, { cache: "no-store" }).then((r) => r.json()),
      fetch(`${DATA}/rcnstats.json`, { cache: "no-store" }).then((r) => r.json()).catch(() => null),
    ]);
    state.data = data;
    state.gap = rcnstats && rcnstats.gap ? rcnstats.gap : null;
  } catch (e) {
    $("main").innerHTML = `<div class="empty">Nie udało się wczytać danych (data/stats.json).</div>`;
    return;
  }
  if (REGION !== "slaskie") {              // keep the region across page links
    const a = document.querySelector('a[href="index.html"]');
    if (a) a.href = `index.html?region=${REGION}`;
  }
  $("#stats").innerHTML = `dane z ${esc(state.data.built || "—")} · oferty tygodniowo (od startu narzędzia) · akty notarialne miesięcznie (RCN/GUGiK)`;
  const towns = Object.keys(state.data.weekly.towns || {});
  $("#town").innerHTML = `<option value="">Całe województwo</option>` +
    towns.map((t) => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
  $("#town").addEventListener("change", (e) => { state.town = e.target.value; render(); });
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
  render();
}

// ---- data selection ---------------------------------------------------------

const last = (arr) => { for (let i = (arr || []).length - 1; i >= 0; i--) if (arr[i] != null) return arr[i]; return null; };

function weeklySel() {
  const w = state.data.weekly;
  const pool = state.town ? (w.towns[state.town] || {})[state.type] : w.global[state.type];
  return { weeks: w.weeks, s: pool || null, full: !state.town ? w.global[state.type] : null };
}

// weekly asking medians -> monthly (median of the month's weekly medians)
function askMonthly() {
  const { weeks, s } = weeklySel();
  if (!s) return {};
  const by = {};
  weeks.forEach((wk, i) => {
    if (s.med[i] != null) (by[wk.slice(0, 7)] = by[wk.slice(0, 7)] || []).push(s.med[i]);
  });
  const out = {};
  for (const m in by) {
    const v = by[m].sort((a, b) => a - b);
    out[m] = Math.round(v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2);
  }
  return out;
}

function rcnSel() {
  const r = state.data.rcn;
  if (!r.months || !r.months.length) return { months: [], w: null, p: null };
  if (state.town) {
    const t = r.towns[state.town];
    return { months: r.months, w: t ? t.w : null, p: null };
  }
  return { months: r.months, w: r.global.w, p: r.global.p };
}

// ---- svg helpers ------------------------------------------------------------

const W = 720, H = 240, PAD = { l: 50, r: 14, t: 14, b: 24 };

function yScale(vals, int) {
  const v = vals.filter((x) => x != null);
  if (!v.length) return null;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (lo === hi) { lo -= 1; hi += 1; }
  const span = hi - lo;
  lo = Math.max(0, lo - span * 0.08);
  hi += span * 0.08;
  let step = niceStep((hi - lo) / 5);
  if (int) step = Math.max(1, Math.round(step));
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  const ticks = [];
  for (let t = lo; t <= hi + 1e-9; t += step) ticks.push(t);
  const y = (val) => PAD.t + (H - PAD.t - PAD.b) * (1 - (val - lo) / (hi - lo));
  return { y, ticks };
}

function niceStep(raw) {
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 2, 2.5, 5, 10]) if (raw <= m * mag) return m * mag;
  return 10 * mag;
}

const xScale = (n) => (i) => PAD.l + (n < 2 ? 0 : (W - PAD.l - PAD.r) * (i / (n - 1)));

function grid(sc, fmt) {
  return sc.ticks.map((t) =>
    `<line class="gridline" x1="${PAD.l}" x2="${W - PAD.r}" y1="${sc.y(t)}" y2="${sc.y(t)}"></line>` +
    `<text class="tick" x="${PAD.l - 6}" y="${sc.y(t) + 3}" text-anchor="end">${fmt(t)}</text>`).join("");
}

function xTicks(labels, every) {
  const x = xScale(labels.length);
  const out = [];
  for (let i = 0; i < labels.length; i += every) {
    out.push(`<text class="tick" x="${x(i)}" y="${H - 6}" text-anchor="middle">${esc(labels[i])}</text>`);
  }
  return out.join("");
}

function linePath(values, sc, x) {
  let d = "", pen = false;
  values.forEach((v, i) => {
    if (v == null) { pen = false; return; }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${sc.y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

// ---- generic charts (line with crosshair tooltip, bars with per-bar hover) --

function fmtPLN(v) { return PLN.format(Math.round(v)); }

function lineChart(el, { title, sub, labels, series, unit, xEvery, note, int }) {
  const visible = series.filter((s) => s.values && s.values.some((v) => v != null));
  const sc = yScale(visible.flatMap((s) => s.values), int);
  const x = xScale(labels.length);
  const legend = visible.length >= 2
    ? `<div class="legend">${visible.map((s) => `<span><span class="sw" style="background:${s.color}"></span>${esc(s.name)}</span>`).join("")}</div>`
    : "";
  if (!sc) {
    el.innerHTML = `<div class="chart-h">${esc(title)}</div><div class="note">brak danych dla tego wyboru</div>`;
    return;
  }
  const paths = visible.map((s) =>
    `<path d="${linePath(s.values, sc, x)}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></path>`).join("");
  // selective direct labels: series name at its last point
  const ends = visible.map((s) => {
    let i = s.values.length - 1;
    while (i >= 0 && s.values[i] == null) i--;
    if (i < 0) return "";
    return `<text class="endlabel" fill="${s.color}" x="${Math.min(x(i) + 4, W - 4)}" y="${sc.y(s.values[i]) - 5}" text-anchor="end">${esc(s.short || "")}</text>`;
  }).join("");
  el.innerHTML = `
    <div class="chart-h">${esc(title)}</div>
    ${sub ? `<div class="chart-sub">${esc(sub)}</div>` : ""}
    ${legend}
    <div class="plot">
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}">
        ${grid(sc, fmtPLN)}
        ${xTicks(labels, xEvery)}
        ${paths}${ends}
        <line class="crosshair" y1="${PAD.t}" y2="${H - PAD.b}" x1="-9" x2="-9"></line>
        <rect class="hover" x="${PAD.l}" y="${PAD.t}" width="${W - PAD.l - PAD.r}" height="${H - PAD.t - PAD.b}" fill="transparent"></rect>
      </svg>
      <div class="tt" hidden></div>
    </div>
    ${note ? `<div class="note">${esc(note)}</div>` : ""}
    ${dataTable(labels, visible, unit)}`;
  wireLineHover(el, labels, visible, unit);
}

function wireLineHover(el, labels, series, unit) {
  const svg = el.querySelector("svg"), tt = el.querySelector(".tt");
  const cross = el.querySelector(".crosshair");
  const x = xScale(labels.length);
  svg.addEventListener("mousemove", (ev) => {
    const box = svg.getBoundingClientRect();
    const px = (ev.clientX - box.left) * (W / box.width);
    const i = Math.max(0, Math.min(labels.length - 1,
      Math.round((px - PAD.l) / ((W - PAD.l - PAD.r) / Math.max(1, labels.length - 1)))));
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i));
    const rows = series.map((s) => s.values[i] == null ? "" :
      `<div class="tt-r"><span><span class="sw" style="background:${s.color}"></span>${esc(s.short || s.name)}</span><span>${fmtPLN(s.values[i])}${unit ? " " + unit : ""}</span></div>`).join("");
    tt.innerHTML = `<div class="tt-t">${esc(labels[i])}</div>` + (rows || `<div class="tt-r"><span>brak danych</span></div>`);
    tt.hidden = false;
    const ttw = tt.offsetWidth;
    const leftPx = (x(i) / W) * box.width;
    tt.style.left = Math.min(Math.max(4, leftPx + 10), box.width - ttw - 4) + "px";
    tt.style.top = "12px";
  });
  svg.addEventListener("mouseleave", () => { tt.hidden = true; cross.setAttribute("x1", -9); cross.setAttribute("x2", -9); });
}

function barChart(el, { title, labels, values, color, unit, xEvery, heading }) {
  const sc = yScale([0, ...values], true);
  if (!sc) { el.innerHTML = ""; return; }
  const n = labels.length;
  const bw = Math.max(2, Math.min(40, (W - PAD.l - PAD.r) / n - 2));   // 2px surface gap
  const x = (i) => PAD.l + (W - PAD.l - PAD.r) * ((i + 0.5) / n) - bw / 2;
  const y0 = sc.y(0);
  const bars = values.map((v, i) => {
    if (v == null) return "";
    const y = sc.y(v);
    const h = Math.max(0, y0 - y);
    const r = Math.min(4, bw / 2, h);       // rounded data-end, flat baseline
    return `<path data-i="${i}" fill="${color}"
      d="M${x(i)},${y0} v${-(h - r)} q0,${-r} ${r},${-r} h${bw - 2 * r} q${r},0 ${r},${r} v${h - r} z"></path>`;
  }).join("");
  el.innerHTML = `
    ${heading ? `<div class="m-h">${esc(heading)}</div>` : ""}
    ${title ? `<div class="chart-h">${esc(title)}</div>` : ""}
    <div class="plot">
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title || heading)}">
        ${grid(sc, (v) => PLN.format(v))}
        ${xTicks(labels, xEvery)}
        ${bars}
        <line class="axisline" x1="${PAD.l}" x2="${W - PAD.r}" y1="${y0}" y2="${y0}"></line>
      </svg>
      <div class="tt" hidden></div>
    </div>`;
  const svg = el.querySelector("svg"), tt = el.querySelector(".tt");
  svg.addEventListener("mousemove", (ev) => {
    const p = ev.target.closest("path[data-i]");
    if (!p) { tt.hidden = true; return; }
    const i = +p.dataset.i;
    const box = svg.getBoundingClientRect();
    tt.innerHTML = `<div class="tt-t">${esc(labels[i])}</div><div class="tt-r"><span>${esc(heading || title || "")}</span><span>${PLN.format(values[i])}${unit ? " " + unit : ""}</span></div>`;
    tt.hidden = false;
    tt.style.left = Math.min((x(i) / W) * box.width + 8, box.width - tt.offsetWidth - 4) + "px";
    tt.style.top = "10px";
  });
  svg.addEventListener("mouseleave", () => { tt.hidden = true; });
}

function dataTable(labels, series, unit) {
  const head = `<tr><th>okres</th>${series.map((s) => `<th>${esc(s.short || s.name)}${unit ? ` [${unit}]` : ""}</th>`).join("")}</tr>`;
  const rows = labels.map((l, i) =>
    `<tr><td>${esc(l)}</td>${series.map((s) => `<td>${s.values[i] != null ? PLN.format(s.values[i]) : "—"}</td>`).join("")}</tr>`).join("");
  return `<details class="dtable"><summary>tabela danych</summary>
    <div class="dtable-wrap"><table><thead>${head}</thead><tbody>${rows}</tbody></table></div></details>`;
}

// ---- page render ------------------------------------------------------------

function tiles() {
  const { s } = weeklySel();
  const rcn = rcnSel();
  const t = [];
  const scope = state.town || "całe województwo";
  const typeLabel = state.type === "flat" ? "mieszkania" : "domy";
  if (s) {
    t.push({ v: PLN.format(last(s.active) ?? 0), l: `aktywne oferty — ${typeLabel}`, d: scope });
    const med = last(s.med);
    if (med) t.push({ v: PLN.format(med) + " zł/m²", l: "mediana ceny ofertowej", d: `${typeLabel}, ${scope}` });
  }
  if (rcn.w) {
    const med = last(rcn.w.med);
    if (med) t.push({ v: PLN.format(med) + " zł/m²", l: "mediana transakcji (RCN, wtórny)", d: `mieszkania, ${scope}` });
  }
  const cs = state.data.cut_share && state.data.cut_share[state.type];
  if (cs != null) t.push({ v: (cs * 100).toFixed(0) + "%", l: "ofert z obniżką ceny", d: `${typeLabel}, całe województwo` });
  const g = state.gap && state.gap.all;
  if (g && g.n) t.push({ v: (g.med_pct > 0 ? "+" : "") + g.med_pct.toFixed(0) + "%", l: "sprzedaż vs cena ofertowa (RCN)", d: `mediana z ${PLN.format(g.n)} sprzedaży${g.med_days ? `, ~${g.med_days} dni` : ""}` });
  $("#tiles").innerHTML = t.map((x) =>
    `<div class="tile"><div class="v">${x.v}</div><div class="l">${esc(x.l)}</div><div class="d">${esc(x.d)}</div></div>`).join("");
}

function priceChart() {
  const rcn = rcnSel();
  const ask = askMonthly();
  let months = rcn.months;
  if (!months.length) months = Object.keys(ask).sort();
  if (state.range !== "all") months = months.slice(-Number(state.range));
  const series = [];
  if (state.type === "flat") {
    if (rcn.w) series.push({ name: NAME.rcnW, short: "RCN wtórny", color: COL.rcnW, values: months.map((m, i) => rcn.w.med[rcn.months.indexOf(m)] ?? null) });
    if (rcn.p) series.push({ name: NAME.rcnP, short: "RCN pierwotny", color: COL.rcnP, values: months.map((m) => rcn.p.med[rcn.months.indexOf(m)] ?? null) });
  }
  series.unshift({ name: NAME.ask, short: "oferty", color: COL.ask, values: months.map((m) => ask[m] ?? null) });
  const scope = state.town || "całe województwo";
  lineChart($("#c-prices"), {
    title: "Mediana zł/m² — ceny ofertowe vs realne transakcje",
    sub: `${scope} · transakcje: akty notarialne (RCN/GUGiK), mieszkania · oferty: mediana z tygodni miesiąca`,
    labels: months, series, unit: "zł/m²",
    xEvery: Math.max(1, Math.ceil(months.length / 8)),
    note: state.type === "house"
      ? "Linie RCN dotyczą tylko mieszkań — rejestr budynków nie niesie wiarygodnej ceny domu (fragmenty wartości większych aktów)."
      : (state.town ? "RCN pierwotny dostępny tylko dla całego województwa. Ostatnie miesiące mogą być puste — akty trafiają do rejestru z opóźnieniem." :
                      "Ostatnie miesiące mogą być puste — akty notarialne trafiają do rejestru z opóźnieniem."),
  });
}

function supplyChart() {
  const w = state.data.weekly;
  const { s } = weeklySel();
  const scope = state.town || "całe województwo";
  lineChart($("#c-supply"), {
    title: "Aktywne oferty tygodniowo",
    sub: `${scope} · ${state.type === "flat" ? "mieszkania" : "domy"} · liczba unikalnych nieruchomości widocznych w danym tygodniu`,
    labels: w.weeks, series: s ? [{ name: "aktywne oferty", short: "aktywne", color: COL.ask, values: s.active }] : [],
    unit: "", int: true, xEvery: Math.max(1, Math.ceil(w.weeks.length / 10)),
  });
}

function flowCharts() {
  const w = state.data.weekly;
  const g = w.global[state.type];
  const el = $("#c-flow");
  el.innerHTML = `
    <div class="chart-h">Ruch tygodniowy — nowe, wycofane, obniżki</div>
    <div class="chart-sub">całe województwo · ${state.type === "flat" ? "mieszkania" : "domy"}${state.town ? " (brak podziału na miejscowości)" : ""}</div>
    <div class="multi">
      <div id="f-new"></div><div id="f-gone"></div><div id="f-cuts"></div>
    </div>
    ${dataTable(w.weeks, [
      { short: "nowe", values: g.new }, { short: "wycofane", values: g.gone }, { short: "obniżki", values: g.cuts },
    ], "")}`;
  const xe = Math.max(1, Math.ceil(w.weeks.length / 5));
  barChart($("#f-new"), { heading: "nowe oferty", labels: w.weeks, values: g.new, color: COL.ask, xEvery: xe });
  barChart($("#f-gone"), { heading: "wycofane (potwierdzone)", labels: w.weeks, values: g.gone, color: COL.rcnW, xEvery: xe });
  barChart($("#f-cuts"), { heading: "obniżki ceny", labels: w.weeks, values: g.cuts, color: COL.rcnP, xEvery: xe });
}

function domChart() {
  const d = state.data.dom;
  const el = $("#c-dom");
  el.innerHTML = `
    <div class="chart-h">Ile dni na rynku przed zniknięciem</div>
    <div class="chart-sub">całe województwo · oferty potwierdzone jako wycofane/sprzedane · buduje się od startu narzędzia</div>
    <div id="dom-plot"></div>
    ${dataTable(d.buckets, [{ short: "liczba ofert", values: d.counts }], "")}`;
  barChart($("#dom-plot"), { heading: "", labels: d.buckets, values: d.counts, color: COL.ask, xEvery: 1 });
}

function render() {
  tiles();
  priceChart();
  supplyChart();
  flowCharts();
  domChart();
}

boot();
