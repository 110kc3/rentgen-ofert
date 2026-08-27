#!/usr/bin/env node
// Build the national picker, regional pages and discovery files from the one
// canonical catalog plus whichever site/data/<region>/ trees deploy.yml has
// overlaid. Plain Node, no dependencies.

import {
  existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = resolve(process.env.RENTGEN_ROOT || HERE);
const SITE = join(ROOT, 'site');
const DATA_ROOT = join(SITE, 'data');
const TEMPLATES = join(ROOT, 'scripts', 'templates');
const BASE = 'https://110kc3.github.io/rentgen-ofert';

const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'));
const catalog = readJson(join(SITE, 'regions.json'));
if (catalog.schema !== 1 || !Array.isArray(catalog.regions)
    || catalog.regions.length !== 16) {
  throw new Error('site/regions.json is not a schema-1 16-region catalog');
}
if (existsSync(DATA_ROOT)) {
  const configured = new Set(catalog.regions.map((region) => region.slug));
  const unknown = readdirSync(DATA_ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !configured.has(entry.name))
    .map((entry) => entry.name);
  if (unknown.length) {
    throw new Error(`deployed data contains region(s) outside the catalog: ${unknown.join(', ')}`);
  }
}

const nf = (n) => Number(n ?? 0).toLocaleString('pl-PL');
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));
const MONTHS_GEN = [
  'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
  'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia',
];

function datePl(value) {
  const iso = String(value || '').slice(0, 10);
  const [year, month, day] = iso.split('-').map(Number);
  return month ? `${day} ${MONTHS_GEN[month - 1]} ${year}` : (iso || 'brak daty');
}

function directoryBytes(path) {
  if (!existsSync(path)) return 0;
  let total = 0;
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) total += directoryBytes(child);
    else if (entry.isFile() && entry.name !== 'history.json.gz') {
      total += statSync(child).size;
    }
  }
  return total;
}

function humanBytes(bytes) {
  let value = Number(bytes || 0);
  const units = ['B', 'KB', 'MB', 'GB'];
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}

const SOURCE_LABEL = {
  otodom: 'Otodom', olx: 'OLX', gratka: 'Gratka', morizon: 'Morizon',
  'nieruchomosci-online': 'n-online',
};

function publication(region) {
  const directory = join(DATA_ROOT, region.slug);
  const metaPath = join(directory, 'meta.json');
  // `enabled` is the catalog kill switch for both refresh and publication.
  // Remove only the artifact copy: the recoverable data branch is untouched
  // and a later re-enable/deploy can overlay it again.
  if (!region.enabled) {
    rmSync(directory, { recursive: true, force: true });
    return { ...region, published: false, data: null };
  }
  if (!existsSync(metaPath)) {
    if (existsSync(directory) && readdirSync(directory).length) {
      throw new Error(`incomplete data for ${region.slug}: missing meta.json`);
    }
    return { ...region, published: false, data: null };
  }
  const required = [
    'manifest.json', 'index.json', 'stats.json', 'rcnstats.json', 'archive.json',
  ];
  const missing = required.filter((file) => !existsSync(join(directory, file)));
  if (missing.length) {
    throw new Error(`incomplete data for ${region.slug}: missing ${missing.join(', ')}`);
  }
  const meta = readJson(metaPath);
  const sources = Object.entries(meta.by_source || {})
    .filter(([, count]) => Number(count) > 0)
    .map(([source]) => SOURCE_LABEL[source] || source);
  return {
    ...region,
    published: true,
    data: {
      count: Number(meta.count || 0),
      updated: meta.updated || null,
      health: meta.health || meta.coverage?.status || 'unknown',
      bytes: directoryBytes(directory),
      sources,
      by_type: meta.by_type || {},
      relisted: Number(meta.relisted || 0),
      archive: Number(meta.archive || 0),
      rcn: meta.rcn || null,
      rcn_stats: meta.rcn_stats || null,
    },
    _meta: meta,
    _directory: directory,
  };
}

const regions = catalog.regions.map(publication);
const published = regions.filter((region) => region.published);
mkdirSync(DATA_ROOT, { recursive: true });

// Browser-facing derivative. It retains all configured regions so a valid but
// unpublished stable path can explain itself. Scraper-only portal slugs and
// TERYT stay solely in the canonical source file.
const browserCatalog = {
  schema: 1,
  generated: new Date().toISOString(),
  default: catalog.default,
  regions: regions.map((region) => ({
    slug: region.slug,
    label: region.label,
    adjective: region.adjective,
    locative: region.locative,
    enabled: region.enabled,
    cadence: region.cadence,
    ...(region.anchor ? { anchor: region.anchor } : {}),
    ...(region.districts ? { districts: region.districts } : {}),
    published: region.published,
    data: region.data,
  })),
};
writeFileSync(join(DATA_ROOT, 'regions.json'),
  `${JSON.stringify(browserCatalog, null, 2)}\n`);

function replaceBetween(html, startMark, endMark, replacement, file) {
  const start = html.indexOf(startMark);
  const end = html.indexOf(endMark);
  if (start === -1 || end === -1 || end < start) {
    throw new Error(`markers ${startMark} / ${endMark} missing in ${file}`);
  }
  return html.slice(0, start + startMark.length) + '\n' + replacement + '\n'
    + html.slice(end);
}

function tokens(html, values, file) {
  const rendered = html.replace(/\{\{([A-Z_]+)\}\}/g, (_, name) => {
    if (!(name in values)) throw new Error(`missing token ${name} for ${file}`);
    return values[name];
  });
  const leftover = rendered.match(/\{\{[A-Z_]+\}\}/);
  if (leftover) throw new Error(`unresolved token ${leftover[0]} in ${file}`);
  return rendered;
}

function fileMb(directory, file) {
  const path = join(directory, file);
  return existsSync(path) ? Math.round(statSync(path).size / 1e6) : null;
}

function regionalSummary(region) {
  if (!region.published) {
    return `    <p class="sub" id="data-summary">Ten region jest skonfigurowany, ale dane nie zostały jeszcze opublikowane.</p>
    <noscript><p class="sub">Wróć do <a href="./">katalogu województw</a>, aby wybrać dostępną bazę.</p></noscript>`;
  }
  const meta = region._meta;
  const sourceCount = region.data.sources.length;
  const sourceWord = sourceCount === 1 ? 'portalu' : 'portali';
  return `    <p class="sub" id="data-summary">W bazie: <b>${nf(meta.count)}</b> ofert
    (${nf(meta.by_type?.flat)} mieszkań, ${nf(meta.by_type?.house)} domów) z ${sourceCount} ${sourceWord},
    ${nf(meta.relisted)} wystawionych ponownie, ${nf(meta.rcn?.matched)} dopasowanych do
    transakcji notarialnych (RCN). Aktualizacja: ${datePl(meta.updated)}.</p>
    <noscript><p class="sub">Lista ofert wymaga JavaScriptu. Surowe dane (JSON):
    <a href="data/${region.slug}/meta.json">meta.json</a>, <a href="data/${region.slug}/stats.json">stats.json</a>,
    <a href="data/${region.slug}/rcnstats.json">rcnstats.json</a> — pełny katalog w <a href="llms.txt">llms.txt</a>.</p></noscript>`;
}

function statsSummary(region) {
  if (!region.published) {
    return '    <p class="sub" id="data-summary">Statystyki dla tego regionu nie zostały jeszcze opublikowane.</p>';
  }
  const meta = region._meta;
  return `    <p class="sub" id="data-summary">Baza RCN: <b>${nf(meta.rcn?.records)}</b> rekordów transakcji,
    ${nf(meta.rcn?.matched)} dopasowanych do ofert, benchmarki dla ${nf(meta.rcn_stats?.towns)} miejscowości.
    Aktualizacja: ${datePl(meta.updated)}.</p>
    <noscript><p class="sub">Wykresy wymagają JavaScriptu. Surowe dane (JSON):
    <a href="data/${region.slug}/stats.json">stats.json</a>, <a href="data/${region.slug}/rcnstats.json">rcnstats.json</a>,
    <a href="data/${region.slug}/meta.json">meta.json</a>.</p></noscript>`;
}

function datasetJsonLd(region, listingUrl, description) {
  const graph = [{
    '@type': 'WebPage', name: `Rentgen ofert — ${region.label}`,
    url: listingUrl, inLanguage: 'pl', description,
  }];
  if (region.published) {
    const files = [
      'meta.json', 'stats.json', 'rcnstats.json', 'index.json',
      'manifest.json', 'archive.json',
    ];
    graph.push({
      '@type': 'Dataset',
      name: `Oferty sprzedaży domów i mieszkań — ${region.label}`,
      description: `${nf(region.data.count)} aktualnych ofert z ${region.data.sources.length} portali; historia cen i dopasowania do transakcji notarialnych (RCN).`,
      url: listingUrl,
      inLanguage: 'pl',
      spatialCoverage: region.label,
      dateModified: region.data.updated,
      isAccessibleForFree: true,
      distribution: files.filter((file) => existsSync(join(region._directory, file)))
        .map((file) => ({
          '@type': 'DataDownload',
          encodingFormat: 'application/json',
          contentUrl: `${BASE}/data/${region.slug}/${file}`,
          ...(fileMb(region._directory, file)
            ? { contentSize: `${fileMb(region._directory, file)} MB` } : {}),
        })),
    });
  }
  return { '@context': 'https://schema.org', '@graph': graph };
}

const listingTemplate = readFileSync(join(TEMPLATES, 'listings.html'), 'utf8');
const statsTemplate = readFileSync(join(TEMPLATES, 'stats.html'), 'utf8');
const regionalRoot = join(SITE, 'region');
rmSync(regionalRoot, { recursive: true, force: true });

for (const region of regions) {
  const listingUrl = `${BASE}/region/${region.slug}/`;
  const statsUrl = `${listingUrl}stats/`;
  const listingTitle = `Rentgen ofert — ${region.label}`;
  const listingDescription = `Domy i mieszkania na sprzedaż w województwie ${region.locative}, bez duplikatów, z historią cen i cenami transakcyjnymi RCN.`;
  const statsTitle = `Statystyki rynku — Rentgen ofert, ${region.label}`;
  const statsDescription = `Ceny ofertowe i transakcyjne RCN, podaż, obniżki i czas sprzedaży domów i mieszkań w województwie ${region.locative}.`;
  const common = {
    REGION_SLUG: escapeHtml(region.slug),
    REGION_LABEL: escapeHtml(region.label),
    ANCHOR_GENITIVE: escapeHtml(region.anchor?.genitive || 'centrum regionu'),
    ROBOTS_META: region.published ? '' : '<meta name="robots" content="noindex">',
  };

  let listing = tokens(listingTemplate, {
    ...common,
    LISTING_TITLE: escapeHtml(listingTitle),
    LISTING_DESCRIPTION: escapeHtml(listingDescription),
    LISTING_URL: escapeHtml(listingUrl),
    DATA_URL: escapeHtml(`${BASE}/data/${region.slug}`),
  }, `region/${region.slug}/index.html`);
  listing = replaceBetween(
    listing, '<!-- summary:start -->', '<!-- summary:end -->',
    regionalSummary(region), `region/${region.slug}/index.html`);
  listing = replaceBetween(
    listing, '<!-- jsonld:start -->', '<!-- jsonld:end -->',
    `  <script type="application/ld+json">${JSON.stringify(datasetJsonLd(region, listingUrl, listingDescription)).replace(/</g, '\\u003c')}</script>`,
    `region/${region.slug}/index.html`);

  let stats = tokens(statsTemplate, {
    ...common,
    STATS_TITLE: escapeHtml(statsTitle),
    STATS_DESCRIPTION: escapeHtml(statsDescription),
    STATS_URL: escapeHtml(statsUrl),
  }, `region/${region.slug}/stats/index.html`);
  stats = replaceBetween(
    stats, '<!-- summary:start -->', '<!-- summary:end -->',
    statsSummary(region), `region/${region.slug}/stats/index.html`);

  const listingDirectory = join(regionalRoot, region.slug);
  const statsDirectory = join(listingDirectory, 'stats');
  mkdirSync(statsDirectory, { recursive: true });
  writeFileSync(join(listingDirectory, 'index.html'), listing);
  writeFileSync(join(statsDirectory, 'index.html'), stats);
}

const HEALTH_LABEL = {
  healthy: 'źródła bez wykrytej regresji',
  partial: 'częściowe pokrycie źródeł',
  blocked: 'źródła zablokowane',
  unknown: 'stan źródeł nieznany',
};
const CADENCE_LABEL = {
  manual: 'ręczny', twice_daily: '2× dziennie', daily: 'codzienny', weekly: 'tygodniowy',
};

function publishedCard(region) {
  const data = region.data;
  return `      <a class="region-card" href="region/${escapeHtml(region.slug)}/">
        <h3>${escapeHtml(region.label)}</h3>
        <div class="region-count">${nf(data.count)} ofert</div>
        <div class="region-meta">Aktualizacja: ${escapeHtml(datePl(data.updated))} · <span class="region-size">${humanBytes(data.bytes)}</span></div>
        <div class="region-meta">${escapeHtml(data.sources.join(', ') || 'brak aktywnych źródeł')}</div>
        <div class="region-health ${escapeHtml(data.health)}">${escapeHtml(HEALTH_LABEL[data.health] || HEALTH_LABEL.unknown)}</div>
      </a>`;
}

function unpublishedCard(region) {
  const state = region.enabled
    ? 'oczekuje na pierwszą publikację' : 'jeszcze nieuruchomione';
  return `      <a class="region-card unpublished" href="region/${escapeHtml(region.slug)}/">
        <h3>${escapeHtml(region.label)}</h3>
        <div class="region-meta">${state} · harmonogram: ${escapeHtml(CADENCE_LABEL[region.cadence] || region.cadence)}</div>
      </a>`;
}

const availableSection = published.length ? `<section class="region-section">
    <h2>Dostępne województwa</h2>
    <div class="region-grid">
${published.map(publishedCard).join('\n')}
    </div>
  </section>` : `<section class="region-section"><h2>Dostępne województwa</h2>
    <p class="empty-warn">Żadna regionalna baza nie została jeszcze opublikowana.</p></section>`;
const pending = regions.filter((region) => !region.published);
const pendingSection = pending.length ? `<section class="region-section">
    <h2>Kolejne województwa</h2>
    <div class="region-grid">
${pending.map(unpublishedCard).join('\n')}
    </div>
  </section>` : '';

const rootPath = join(SITE, 'index.html');
let rootHtml = readFileSync(rootPath, 'utf8');
rootHtml = replaceBetween(
  rootHtml, '<!-- regions:start -->', '<!-- regions:end -->',
  `${availableSection}\n  ${pendingSection}`, 'index.html');
const rootJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'CollectionPage',
  name: 'Rentgen ofert — domy i mieszkania w Polsce',
  url: `${BASE}/`,
  inLanguage: 'pl',
  mainEntity: {
    '@type': 'ItemList',
    itemListElement: published.map((region, index) => ({
      '@type': 'ListItem', position: index + 1,
      name: region.label, url: `${BASE}/region/${region.slug}/`,
    })),
  },
};
rootHtml = replaceBetween(
  rootHtml, '<!-- jsonld:start -->', '<!-- jsonld:end -->',
  `  <script type="application/ld+json">${JSON.stringify(rootJsonLd).replace(/</g, '\\u003c')}</script>`,
  'index.html');
writeFileSync(rootPath, rootHtml);

const updatedDates = published
  .map((region) => String(region.data.updated || '').slice(0, 10))
  .filter(Boolean).sort();
const latestDate = updatedDates.at(-1) || new Date().toISOString().slice(0, 10);
const sitemapRows = [
  `  <url><loc>${BASE}/</loc><lastmod>${latestDate}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>`,
  ...published.flatMap((region) => {
    const date = String(region.data.updated || latestDate).slice(0, 10);
    return [
      `  <url><loc>${BASE}/region/${region.slug}/</loc><lastmod>${date}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>`,
      `  <url><loc>${BASE}/region/${region.slug}/stats/</loc><lastmod>${date}</lastmod><changefreq>daily</changefreq><priority>0.7</priority></url>`,
    ];
  }),
];
writeFileSync(join(SITE, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapRows.join('\n')}
</urlset>
`);

const llmsRegions = published.length ? published.map((region) => {
  const dataUrl = `${BASE}/data/${region.slug}`;
  let shards = '';
  try {
    const manifest = readJson(join(region._directory, 'manifest.json'));
    shards = `\n  - ${dataUrl}/d/00.json … d/${String(manifest.shards - 1).padStart(2, '0')}.json — detail shards (${manifest.shards})`;
  } catch { /* a legacy payload may have no manifest */ }
  return `### ${region.label}

- Pages: ${BASE}/region/${region.slug}/ and ${BASE}/region/${region.slug}/stats/
- Current: ${nf(region.data.count)} listings; updated ${String(region.data.updated || '').slice(0, 10)}; health ${region.data.health}; ${humanBytes(region.data.bytes)}
- Data:
  - ${dataUrl}/meta.json — counts, freshness, runtime and source health
  - ${dataUrl}/stats.json — market series
  - ${dataUrl}/rcnstats.json — RCN transaction benchmarks
  - ${dataUrl}/index.json — slim current-listing index
  - ${dataUrl}/manifest.json — data version and shard count${shards}
  - ${dataUrl}/archive.json — delisted offers`;
}).join('\n\n') : 'No regional dataset is currently published.';

writeFileSync(join(SITE, 'llms.txt'), `# Rentgen ofert — Poland regional property data

> Regional dashboards aggregating house and flat sale listings in Poland. Listings
> are de-duplicated, carry price history, and may be matched to notarial RCN sale
> prices. Page content is in Polish. The source portals and public registers remain
> authoritative.

## Start here

- ${BASE}/ — national region picker
- ${BASE}/data/regions.json — configured and published region catalog with counts, freshness, health and byte size
- ${BASE}/sitemap.xml — published regional pages

## Published regions

${llmsRegions}

## Notes

- Source and pipeline: https://github.com/110kc3/rentgen-ofert
- Data has informational character; source portals and notarial registers are authoritative.
`);

console.error(`summary: ${published.length} published / ${regions.length} configured regions; wrote picker, regional pages, regions.json, sitemap.xml and llms.txt`);
