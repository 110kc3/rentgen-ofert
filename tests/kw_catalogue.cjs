const { test } = require('node:test');
const assert = require('node:assert/strict');
const catalogue = require('../site/kw-catalogue.js');
const { create } = require('../site/kw-links.js');

// Fictional property fixtures; no private catalogue observations are shipped.
const request = { city: 'Gliwice', street: 'Testowa', number: '16A', unit: '05', register_type: 'unit' };
const flat = { url: 'https://example.invalid/offer', locality: 'Gliwice', type: 'flat' };
function fixture() {
  const source = { url: 'https://example.invalid/property', observed_at: '2025-01-02T10:00:00Z', document_date: null,
    sha256: 'a'.repeat(64), proof_kind: 'rendered_io_projection', register_state_time_local: '2025-01-02 11:00' };
  return { schema_version: 1, query: { ...request }, status: 'observed_own_io',
    candidate_kw_numbers: ['GL1G/00000002/0'], observed_kw_numbers: ['GL1G/00000002/0'],
    candidates: [{ kw_number: 'GL1G/00000002/0', register_type: 'unit', evidence_status: 'observed_own_io',
      addresses: [{ city: request.city, street: request.street, number: request.number, unit: request.unit }],
      sources: [source], source_count: 1, purpose: 'LOKAL MIESZKALNY', area_including_attached_m2: '51.5000' }],
    land_context: [], available_units: ['05'], verified_title: false, complete_coverage: false };
}
const clone = value => JSON.parse(JSON.stringify(value));

test('public Pages and non-loopback origins never request private catalogue endpoints', async () => {
  let calls = 0;
  for (const location of [{ protocol: 'https:', hostname: '110kc3.github.io' }, { protocol: 'http:', hostname: 'localhost.evil.invalid' },
    { protocol: 'file:', hostname: '' }, { protocol: 'https:', hostname: 'localhost' }]) {
    const client = catalogue.createClient({ location, fetch: async () => { calls++; } });
    assert.equal(client.available, false);
    await assert.rejects(client.status()); await assert.rejects(client.search(request));
  }
  assert.equal(calls, 0);
});

test('loopback client uses relative same-origin JSON requests with no cache or address URL', async () => {
  const calls = [], client = catalogue.createClient({ location: { protocol: 'http:', hostname: '127.0.0.1' },
    fetch: async (...args) => { calls.push(args); return { ok: true, text: async () => JSON.stringify(fixture()) }; } });
  const result = await client.search(request);
  assert.equal(result.candidates[0].area_including_attached_m2, '51.5000');
  assert.equal(calls[0][0], '/api/kw/search');
  assert.deepEqual(JSON.parse(calls[0][1].body), request);
  assert.equal(calls[0][1].method, 'POST'); assert.equal(calls[0][1].cache, 'no-store');
  assert.equal(calls[0][1].credentials, 'same-origin'); assert.equal(calls[0][1].referrerPolicy, 'no-referrer');
  assert.equal(calls[0][1].redirect, 'error');
});

test('HTTPS catalogue discovery needs a private server marker matching this exact origin', async () => {
  const location = { protocol: 'https:', hostname: 'private.example.test', origin: 'https://private.example.test:8443' };
  let calls = 0;
  const fetch = async (path, options) => {
    calls++;
    assert.equal(path, '/api/kw/search');
    assert.equal(options.redirect, 'error');
    return { ok: true, text: async () => JSON.stringify(fixture()) };
  };
  for (const content of [null, '', 'https://private.example.test', 'https://other.example.test',
    'http://private.example.test:8443', 'https://private.example.test:8443/']) {
    const document = { querySelector: () => content === null ? null : { getAttribute: () => content } };
    const client = catalogue.createClient({ location, document, fetch });
    assert.equal(client.available, false);
    await assert.rejects(client.search(request));
  }
  assert.equal(calls, 0);
  const document = { querySelector: selector => {
    assert.equal(selector, 'meta[name="rentgen-kw-origin"]');
    return { getAttribute: key => { assert.equal(key, 'content'); return location.origin; } };
  } };
  const client = catalogue.createClient({ location, document, fetch });
  assert.equal(client.available, true);
  assert.equal((await client.search(request)).candidates.length, 1);
  assert.equal(calls, 1);
});

test('only complete exact addresses are queried and supplied listing data is rejected', async () => {
  let calls = 0;
  const client = catalogue.createClient({ location: { protocol: 'http:', hostname: 'localhost' },
    fetch: async () => { calls++; return { ok: true, text: async () => JSON.stringify(fixture()) }; } });
  for (const invalid of [{ ...request, unit: '' }, { ...request, unit: 'x'.repeat(31) }, { ...request, number: '' }, { ...request, area: 51.5 },
    { ...request, owner: 'not accepted' }, { ...request, url: flat.url }, { ...request, register_type: 'land' }]) {
    await assert.rejects(client.search(invalid));
  }
  assert.equal(calls, 0);
  assert.deepEqual(catalogue.query({ city: 'Gliwice', street: 'Testowa', number: '16A', register_type: 'land', unit: null }),
    { city: 'Gliwice', street: 'Testowa', number: '16A', register_type: 'land' });
});

test('response validation preserves exact suffixes, leading zeros and provenance', () => {
  const data = fixture(), valid = catalogue.validateResponse(data, { ...request, city: ' GLIWICE ', street: 'testowa' });
  assert.equal(valid.candidates[0].addresses[0].unit, '05');
  assert.equal(valid.candidates[0].sources[0].register_state_time_local, '2025-01-02 11:00');
  for (const changes of [{ unit: '5' }, { number: '16' }, { street: 'Testówa' }, { city: 'Zabrze' }]) {
    assert.throws(() => catalogue.validateResponse(data, { ...request, ...changes }));
  }
});

test('personal fields, hostile source URLs and unsupported verification cannot enter the UI', () => {
  for (const change of [data => data.owner = 'private', data => data.verified_title = true,
    data => data.complete_coverage = true, data => data.candidates[0].owner = 'private',
    data => data.candidates[0].addresses[0].owner = 'private', data => data.candidates[0].sources[0].cookie = 'private',
    data => data.candidates[0].sources[0].url = 'javascript:alert(1)',
    data => data.candidates[0].sources[0].url = 'https://user:password@example.invalid/',
    data => data.candidates[0].source_count = 2, data => data.candidates[0].addresses[0].unit = null,
    data => data.observed_kw_numbers = [], data => data.status = 'ambiguous',
    data => data.candidates[0].sources[0].proof_kind = 'published_property_source']) {
    const data = fixture(); change(data); assert.throws(() => catalogue.validateResponse(data, request));
  }
});

test('catalogue associations need explicit confirmation and cannot attach land to a flat', () => {
  const links = create(), response = fixture(), choices = links.addCatalogue(response);
  assert.equal(links.get(flat), null); assert.equal(links.size, 1);
  assert.throws(() => links.attach(flat, choices[0].id, false));
  links.attach(flat, choices[0].id, true);
  assert.equal(links.get(flat).evidence_status, 'observed_own_io');
  assert.equal(links.get({ ...flat, url: flat.url + '-neighbor' }), null);
  assert.equal(links.get({ ...flat, type: 'house' }), null);
  links.addCatalogue(response); assert.equal(links.size, 1); assert.equal(links.linked, 1);
  links.clear(); assert.equal(links.get(flat), null); assert.equal(links.linked, 0);
});

test('ambiguous catalogue records retain every candidate and cannot be attached', () => {
  const response = fixture(), other = clone(response.candidates[0]); other.kw_number = 'GL1G/00000003/0';
  response.candidates.push(other); response.candidate_kw_numbers.push(other.kw_number);
  response.observed_kw_numbers.push(other.kw_number); response.status = 'ambiguous';
  const links = create(), groups = links.addCatalogue(response);
  assert.equal(groups.length, 2); assert.equal(links.choices(flat).length, 0);
  assert.throws(() => links.attach(flat, groups[0].id, true));
});

test('local transport failure returns a bounded message, never a raw server error', async () => {
  const client = catalogue.createClient({ location: { protocol: 'http:', hostname: 'localhost' },
    fetch: async () => { throw Error('PRIVATE PATH and COOKIE'); } });
  await assert.rejects(client.search(request), error => !error.message.includes('PRIVATE') && !error.message.includes('COOKIE'));
});
