#!/usr/bin/env node
// Injects a no-JS summary (crawlers/agents see real numbers instead of empty
// divs) plus fresh Dataset JSON-LD into site/index.html and site/stats.html,
// and regenerates site/sitemap.xml + site/llms.txt — all from the region data
// under site/data/<region>/ (overlaid from the orphan `data` branch).
//
// Runs in deploy.yml right after the data overlay, so the Pages artifact
// carries fresh numbers without any commit to main. Content is replaced
// between marker comments, so the HTML stays hand-editable everywhere else.
// Fail-soft: with no data present (plain main checkout) it leaves the
// committed HTML as-is and exits 0 — a deploy must never die here.
// Plain Node, no deps: `node scripts/update-summary.mjs`.

import { readFileSync, writeFileSync, statSync, readdirSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SITE = join(ROOT, 'site');
const BASE = 'https://110kc3.github.io/rentgen-ofert';

// The dashboard is Śląskie-first; prefer it, else the first region dir that
// has a meta.json (future regions land as siblings under site/data/).
function findRegion() {
  const dataDir = join(SITE, 'data');
  if (!existsSync(dataDir)) return null;
  const regions = readdirSync(dataDir, { withFileTypes: true })
    .filter(e => e.isDirectory() && existsSync(join(dataDir, e.name, 'meta.json')))
    .map(e => e.name)
    .sort((a, b) => (a === 'slaskie' ? -1 : b === 'slaskie' ? 1 : a.localeCompare(b)));
  return regions[0] ?? null;
}

const region = findRegion();
if (!region) {
  console.error('summary: no site/data/<region>/meta.json found — leaving committed HTML untouched');
  process.exit(0);
}
const DATA = join(SITE, 'data', region);
const DATA_URL = `${BASE}/data/${region}`;
const meta = JSON.parse(readFileSync(join(DATA, 'meta.json'), 'utf8'));

const nf = (n) => Number(n ?? 0).toLocaleString('pl-PL');
const MONTHS_GEN = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
  'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];
const updatedIso = String(meta.updated || '').slice(0, 10);
const [uy, um, ud] = updatedIso.split('-').map(Number);
const updatedPl = um ? `${ud} ${MONTHS_GEN[um - 1]} ${uy}` : updatedIso;
const mb = (file) => {
  try { return Math.round(statSync(join(DATA, file)).size / 1e6); }
  catch { return null; }
};
const sizeNote = (file) => {
  const m = mb(file);
  return m && m >= 5 ? ` (duży plik, ~${m} MB)` : '';
};

function replaceBetween(html, startMark, endMark, replacement, file) {
  const start = html.indexOf(startMark);
  const end = html.indexOf(endMark);
  if (start === -1 || end === -1) throw new Error(`markers ${startMark} missing in ${file}`);
  return html.slice(0, start + startMark.length) + '\n' + replacement + '\n' + html.slice(end);
}

function inject(file, blocks) {
  const path = join(SITE, file);
  let html = readFileSync(path, 'utf8');
  for (const [name, replacement] of Object.entries(blocks)) {
    html = replaceBetween(html, `<!-- ${name}:start -->`, `<!-- ${name}:end -->`, replacement, file);
  }
  writeFileSync(path, html);
  console.error(`summary: injected ${Object.keys(blocks).join(' + ')} into ${file}`);
}

// ---------- index.html ----------

const sources = Object.keys(meta.by_source || {}).length || 5;
const indexSummary =
`    <p class="sub" id="data-summary">W bazie: <b>${nf(meta.count)}</b> ofert
    (${nf(meta.by_type?.flat)} mieszkań, ${nf(meta.by_type?.house)} domów) z ${sources} portali,
    ${nf(meta.relisted)} wystawionych ponownie, ${nf(meta.rcn?.matched)} dopasowanych do
    transakcji notarialnych (RCN). Aktualizacja: ${updatedPl}.</p>
    <noscript><p class="sub">Lista ofert wymaga JavaScriptu. Surowe dane (JSON):
    <a href="data/${region}/meta.json">meta.json</a>, <a href="data/${region}/stats.json">stats.json</a>,
    <a href="data/${region}/rcnstats.json">rcnstats.json</a> — pełny katalog w <a href="llms.txt">llms.txt</a>.</p></noscript>`;

const indexJsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      name: 'Rentgen ofert — woj. śląskie',
      url: `${BASE}/`,
      inLanguage: 'pl',
      description: 'Wszystkie oferty sprzedaży domów i mieszkań w województwie śląskim (Otodom, OLX, Gratka, Morizon, n-online) w jednym miejscu, bez duplikatów, z historią cen i cenami transakcyjnymi RCN.',
    },
    {
      '@type': 'Dataset',
      name: 'Oferty sprzedaży domów i mieszkań — woj. śląskie',
      description: `${nf(meta.count)} aktualnych ofert z ${sources} portali, odświeżane dwa razy dziennie; historia cen i dopasowania do transakcji notarialnych (RCN).`,
      url: `${BASE}/`,
      inLanguage: 'pl',
      dateModified: meta.updated,
      isAccessibleForFree: true,
      distribution: ['meta.json', 'stats.json', 'rcnstats.json', 'index.json', 'manifest.json', 'archive.json']
        .map((f) => ({
          '@type': 'DataDownload',
          encodingFormat: 'application/json',
          contentUrl: `${DATA_URL}/${f}`,
          ...(mb(f) ? { contentSize: `${mb(f)} MB` } : {}),
        })),
    },
  ],
};

inject('index.html', {
  summary: indexSummary,
  jsonld: `  <script type="application/ld+json">${JSON.stringify(indexJsonLd).replace(/</g, '\\u003c')}</script>`,
});

// ---------- stats.html ----------

const statsSummary =
`    <p class="sub" id="data-summary">Baza RCN: <b>${nf(meta.rcn?.records)}</b> rekordów transakcji,
    ${nf(meta.rcn?.matched)} dopasowanych do ofert, benchmarki dla ${nf(meta.rcn_stats?.towns)} miejscowości.
    Aktualizacja: ${updatedPl}.</p>
    <noscript><p class="sub">Wykresy wymagają JavaScriptu. Surowe dane (JSON):
    <a href="data/${region}/stats.json">stats.json</a>, <a href="data/${region}/rcnstats.json">rcnstats.json</a>,
    <a href="data/${region}/meta.json">meta.json</a>.</p></noscript>`;

inject('stats.html', { summary: statsSummary });

// ---------- sitemap.xml ----------

writeFileSync(join(SITE, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${BASE}/</loc><lastmod>${updatedIso}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>${BASE}/stats.html</loc><lastmod>${updatedIso}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>
</urlset>
`);
console.error('summary: wrote sitemap.xml');

// ---------- llms.txt ----------

let shardsLine = '';
try {
  const manifest = JSON.parse(readFileSync(join(DATA, 'manifest.json'), 'utf8'));
  shardsLine = `- ${DATA_URL}/d/00.json … d/${String(manifest.shards - 1).padStart(2, '0')}.json — lazy detail shards (${manifest.shards} files; shard = listing id hash, see manifest.json)\n`;
} catch { /* no manifest — skip the shard line */ }

writeFileSync(join(SITE, 'llms.txt'), `# Rentgen ofert — woj. śląskie

> Aggregated dashboard of every house/flat sale listing in the Śląskie voivodeship,
> Poland — scraped twice daily from five portals (Otodom, OLX, Gratka, Morizon,
> nieruchomości-online), de-duplicated by photo hash, with price history and real
> notarial transaction prices (RCN). Personal, non-commercial project; listings link
> back to the source portals. Page content is in Polish.

## Pages

- ${BASE}/ — listing browser (JavaScript app; the served HTML carries a no-JS data summary)
- ${BASE}/stats.html — market statistics: asking vs notarial (RCN) prices, supply, discounts

## Machine-readable data (JSON, refreshed twice daily at ~06:00 and ~18:00 UTC)

Start with meta.json — counts and freshness in one small file.

- ${DATA_URL}/meta.json — dataset counts, per-source/per-type breakdown, last update
- ${DATA_URL}/stats.json — market statistics feeding stats.html
- ${DATA_URL}/rcnstats.json — notarial-transaction (RCN) benchmarks per town
- ${DATA_URL}/index.json — slim grid index of every current listing${sizeNote('index.json')}
- ${DATA_URL}/manifest.json — data version + shard count
${shardsLine}- ${DATA_URL}/archive.json — delisted offers${sizeNote('archive.json')}
- Sitemap: ${BASE}/sitemap.xml

Current: ${nf(meta.count)} listings (${nf(meta.by_type?.flat)} flats, ${nf(meta.by_type?.house)} houses), updated ${updatedIso}.

## Notes

- Source & pipeline: https://github.com/110kc3/rentgen-ofert
- Data has informational character; the source portals and notarial registers are authoritative.
`);
console.error(`summary: wrote llms.txt (region: ${region})`);
