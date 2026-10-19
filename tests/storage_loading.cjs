const { test } = require('node:test');
const assert = require('node:assert/strict');
const { resolve } = require('../site/storage.js');
const base = 'https://ui.example/rentgen-ofert/';
const version = 'a'.repeat(64), newer = 'b'.repeat(64);
const manifest = { schema: 3, v: 'payload', shards: 64, count: 1, archive: { count: 2, shards: 64 } };
const ok = value => ({ ok: true, json: async () => value });

test('legacy regions make no storage requests and keep their Pages path', async () => {
  const result = await resolve({ slug: 'opolskie' }, base, () => { throw Error('unexpected'); });
  assert.deepEqual(result, { data: 'data/opolskie', manifest: null, pinned: false });
});

test('one pointer read pins a version even after the publisher switches it', async () => {
  const requests = [];
  let current = version;
  const entry = { slug: 'slaskie', storage: { pointer_url: 'https://objects.example/slaskie/current.json' } };
  const fetcher = async (url, options) => {
    requests.push([url, options]);
    return ok(url.endsWith('/current.json') ? { schema: 1, version: current } : manifest);
  };
  const oldTab = await resolve(entry, base, fetcher);
  current = newer;
  const newTab = await resolve(entry, base, fetcher);
  assert.equal(oldTab.data, `https://objects.example/slaskie/versions/${version}`);
  assert.equal(newTab.data, `https://objects.example/slaskie/versions/${newer}`);
  assert.deepEqual(oldTab.manifest, manifest);
  assert.equal(requests[0][1].cache, 'no-store');
  assert.equal(requests[0][1].credentials, 'omit');
  assert.equal(requests.length, 4);
});

test('relative and loopback URLs support a local two-origin rehearsal', async () => {
  for (const pointer_url of ['objects/slaskie/current.json', 'http://127.0.0.1:8001/slaskie/current.json']) {
    const result = await resolve({ slug: 'slaskie', storage: { pointer_url } }, base,
      async url => ok(url.endsWith('/current.json') ? { schema: 1, version } : manifest));
    assert.ok(result.pinned);
    assert.ok(result.data.endsWith(`/versions/${version}`));
  }
});

test('deployment catalogs pin verified versions without following the mutable pointer', async () => {
  const urls = [];
  const entry = { slug: 'slaskie', storage: {
    pointer_url: 'https://objects.example/slaskie/current.json', version,
  } };
  const result = await resolve(entry, base, async url => { urls.push(url); return ok(manifest); });
  assert.equal(result.data, `https://objects.example/slaskie/versions/${version}`);
  assert.deepEqual(urls, [`${result.data}/manifest.json`]);
  for (const invalid of [null, '', '../escape', 123, [version]])
    await assert.rejects(resolve({ ...entry, storage: { ...entry.storage, version: invalid } }, base), /version/);
});

test('configured storage errors fail closed instead of falling back to another snapshot', async () => {
  const entry = { slug: 'slaskie', storage: { pointer_url: 'https://objects.example/slaskie/current.json' } };
  for (const pointer of [{ schema: 2, version }, { schema: 1, version: '../escape' }, {}, null])
    await assert.rejects(resolve(entry, base, async () => ok(pointer)), /pointer/);
  await assert.rejects(resolve(entry, base, async () => ({ ok: false, status: 503 })), /503/);
  await assert.rejects(resolve(entry, base, async () => { throw Error('offline'); }), /offline/);
  await assert.rejects(resolve(entry, base, async url => url.endsWith('/current.json')
    ? ok({ schema: 1, version }) : ok({ schema: 99 })), /Unsupported/);
  for (const pointer_url of ['http://remote.example/current.json', 'javascript:alert(1)',
    'https://user:secret@example.test/current.json', 'https://example.test/current.json?secret=x'])
    await assert.rejects(resolve({ ...entry, storage: { pointer_url } }, base), /URL/);
  await assert.rejects(resolve({ ...entry, storage: null }, base), /configuration/);
});
