// Usage: node scripts/benchmark_payload.mjs LEGACY_DIR COMPACT_DIR
// Offline CPU/byte comparison; browser/network timings belong in the dated audit.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';
import { performance } from 'node:perf_hooks';
import { createRequire } from 'node:module';
const { decode } = createRequire(import.meta.url)('../site/payload.js');
const roots = process.argv.slice(2);
if (roots.length !== 2) throw Error('Usage: node scripts/benchmark_payload.mjs LEGACY_DIR COMPACT_DIR');
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const results = [];
for (const root of roots) {
  const manifest = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8'));
  const files = ['index.json', 'archive.json', 'manifest.json'];
  for (const namespace of ['d', ...(manifest.archive ? ['a'] : [])]) {
    for (const name of readdirSync(join(root, namespace)).filter(name => name.endsWith('.json')))
      files.push(`${namespace}/${name}`);
  }
  const faces = {};
  for (const file of ['index.json', 'archive.json']) {
    const raw = readFileSync(join(root, file)), text = raw.toString('utf8'), times = [];
    let rows;
    for (let i = 0; i < 8; i++) {
      const start = performance.now(); rows = decode(JSON.parse(text));
      if (i >= 3) times.push(performance.now() - start);
    }
    faces[file] = { rows: rows.length, bytes: raw.length, gzip_bytes: gzipSync(raw).length,
      median_parse_decode_ms: Number(median(times).toFixed(1)) };
  }
  results.push({ root, node: process.version, schema: manifest.schema || 1, faces,
    payload_bytes: files.reduce((sum, name) => sum + statSync(join(root, name)).size, 0),
    largest_archive_shard_bytes: manifest.archive
      ? Math.max(...files.filter(name => name.startsWith('a/')).map(name => statSync(join(root, name)).size)) : null });
}
if (results[0].faces['index.json'].rows !== results[1].faces['index.json'].rows
    || results[0].faces['archive.json'].rows !== results[1].faces['archive.json'].rows)
  throw Error('Benchmark row counts differ');
console.log(JSON.stringify(results, null, 2));
