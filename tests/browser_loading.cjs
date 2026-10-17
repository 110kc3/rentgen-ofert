// Exercise the actual app loaders and their UI handlers with offline DOM/fetch fixtures.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../site/app.js'), 'utf8');
const loaders = source.slice(source.indexOf('let archiveRequest ='), source.indexOf('// Chunked rendering:'));
const rendering = source.slice(source.indexOf('function render()'), source.indexOf('function priceLabel('));
const settle = () => new Promise(resolve => setImmediate(resolve));
const ok = value => ({ ok: true, json: async () => value });
const columns = (fields, rows) => ({ schema: 1, fields, rows });

function fixture(fetch) {
  const elements = new Map();
  const element = () => ({ innerHTML: '', textContent: '', onclick: null });
  const context = vm.createContext({
    fetch, RentgenPayload: require('../site/payload.js'),
    DATA: '/data/slaskie', state: { archive: null, shards: 1, v: '?v=current', all: [] },
    archiveMode: true,
    $: selector => { if (!elements.has(selector)) elements.set(selector, element()); return elements.get(selector); },
    inArchive: () => context.archiveMode,
    currentFilters: () => ({}), sorters: { newest: () => 0 }, passes: () => true,
    PLN: new Intl.NumberFormat('pl-PL'), emptyMessage: () => 'empty',
    appendChunk() {}, watchSentinel() {}, syncLocalityLabel() {}, renderChips() {}, updateSegCounts() {}, syncKWButton() {},
    offersRows: l => JSON.stringify(l.offers), tlBody: l => JSON.stringify(l.timeline),
  });
  vm.runInContext('let view = [], rendered = 0, moreObserver = null;\n' + loaders + rendering, context);
  return { context, elements };
}

test('column decoding preserves false/zero and rejects malformed or unsafe fields', () => {
  const { decode } = require('../site/payload.js');
  assert.deepEqual(decode(columns(['url', 'price', 'is_private'], [['a', 0, false], ['b']])),
    [{ url: 'a', price: 0, is_private: false }, { url: 'b' }]);
  for (const fields of [['url', 'url'], ['__proto__'], ['constructor']])
    assert.throws(() => decode(columns(fields, [])));
  assert.throws(() => decode(columns(['url'], [['a', 'extra']])));
  assert.throws(() => decode({ schema: 9, fields: [], rows: [] }));
});

test('compact archives load faces only and keep equal-URL timelines separate', async () => {
  const urls = [];
  const { context: c } = fixture(async url => {
    urls.push(url);
    if (url.includes('/archive.json')) return ok(columns(['url', 'detail_key', 'tl_n'],
      [['shared-url', 'first', 1], ['shared-url', 'second', 1]]));
    return ok({ first: { timeline: [{ date: '2026-01-01' }] },
                second: { timeline: [{ date: '2026-02-01' }] } });
  });
  c.state.archiveInfo = { count: 2, shards: 1 };
  const rows = await c.loadArchive();
  assert.equal(urls.length, 1);
  assert.equal(rows[0].timeline, undefined);
  await Promise.all(rows.map(row => c.loadDetails(row)));
  assert.equal(urls.length, 2);
  assert.ok(urls[1].includes('/a/00.json'));
  assert.equal(rows[0].timeline[0].date, '2026-01-01');
  assert.equal(rows[1].timeline[0].date, '2026-02-01');
});

test('archive and current detail caches are isolated and archive failures retry', async () => {
  let failures = 1;
  const urls = [];
  const { context: c } = fixture(async url => {
    urls.push(url);
    if (url.includes('/a/') && failures--) throw Error('offline');
    return ok(url.includes('/a/') ? { archived: { timeline: ['archive'] } }
      : { same: { timeline: ['current'] } });
  });
  const current = { url: 'same' }, archived = { url: 'same', detail_key: 'archived' };
  await c.loadDetails(current);
  await assert.rejects(c.loadDetails(archived));
  assert.equal(archived._full, undefined);
  await c.loadDetails(archived);
  assert.equal(archived.timeline[0], 'archive');
  assert.equal(current.timeline[0], 'current');
  assert.equal(urls.length, 3);
});

test('compact archive count errors leave the old view retryable', async () => {
  const { context: c } = fixture(async () => ok(columns(['detail_key'], [['a']])));
  c.state.archiveInfo = { count: 2, shards: 1 };
  await assert.rejects(c.loadArchive(), /count mismatch/);
  assert.equal(c.state.archive, null);
});

for (const [name, fail] of [
  ['network', () => Promise.reject(new Error('offline'))],
  ['HTTP', () => Promise.resolve({ ok: false, status: 503 })],
  ['JSON', () => Promise.resolve({ ok: true, json: async () => { throw Error('invalid JSON'); } })],
  ['missing record', () => Promise.resolve(ok({}))],
]) {
  test(`detail ${name} failure can be retried and never marks a listing complete`, async () => {
    let calls = 0;
    const { context: c } = fixture(async url => {
      assert.ok(url.endsWith('?v=current'));
      return ++calls === 1 ? fail() : ok({ a: { street: 'Lipowa' }, b: { street: 'Polna' } });
    });
    const a = { url: 'a' }, b = { url: 'b' };
    await assert.rejects(c.loadDetails(a));
    assert.equal(a._full, undefined);
    await Promise.all([c.loadDetails(a), c.loadDetails(b)]);
    assert.equal(calls, 2); // same shard request shared by both cards
    assert.equal(a.street, 'Lipowa');
    assert.equal(b.street, 'Polna');
    assert.equal(a._full, true);
    await c.loadDetails(a);
    assert.equal(calls, 2);
  });
}

test('archive errors remain distinct from a successfully empty archive', async () => {
  for (const response of [{ ok: false, status: 503 }, ok({}), ok([null])]) {
    let calls = 0;
    const { context: c } = fixture(async () => ++calls === 1 ? response : ok([]));
    await assert.rejects(c.loadArchive());
    assert.equal(c.state.archive, null);
    await Promise.all([c.loadArchive(), c.loadArchive()]);
    assert.equal(c.state.archive.length, 0);
    await c.loadArchive();
    assert.equal(calls, 2);
  }
});

test('archive error UI provides a retry that restores results', async () => {
  let calls = 0;
  const { context: c, elements } = fixture(async () => {
    if (++calls === 1) throw Error('offline');
    return ok([{ url: 'a' }]);
  });
  c.render();
  await settle();
  assert.match(elements.get('#grid').innerHTML, /Spróbuj ponownie/);
  assert.equal(c.state.archive, null);
  elements.get('#retry-archive').onclick();
  await settle();
  assert.equal(calls, 2);
  assert.equal(c.state.archive[0]._full, true);
  assert.match(elements.get('#count').textContent, /1 wynik/);
});

test('late archive failure cannot replace a current-listings view', async () => {
  let reject;
  const { context: c, elements } = fixture(() => new Promise((_, fail) => { reject = fail; }));
  c.render();
  c.archiveMode = false;
  c.render();
  const current = elements.get('#grid').innerHTML;
  reject(Error('offline'));
  await settle();
  assert.equal(elements.get('#grid').innerHTML, current);
});

test('card detail error UI retries successfully without reloading the page', async () => {
  let calls = 0, status;
  const { context: c } = fixture(async () => {
    if (++calls === 1) throw Error('offline');
    return ok({ a: { offers: [{ price: 350000 }], timeline: [{ kind: 'listed' }], street: 'Polna' } });
  });
  const button = {}, offers = {}, timeline = {}, street = { value: '' };
  c.document = { createElement: () => ({ setAttribute() {}, querySelector: () => button,
    remove() { status = null; } }) };
  const card = { dataset: { href: 'a' }, appendChild: el => { status = el; },
    querySelector: selector => selector === '.detail-load-status' ? status : street,
    querySelectorAll: selector => selector.includes('offers') ? [offers] : [timeline] };
  c.state.byUrl = new Map([['a', { url: 'a' }]]);
  await c.fillCardDetails(card);
  assert.match(status.innerHTML, /Spróbuj ponownie/);
  button.onclick({ stopPropagation() {} });
  await settle();
  assert.equal(status, null);
  assert.equal(c.state.byUrl.get('a')._full, true);
  assert.match(offers.innerHTML, /350000/);
  assert.match(timeline.innerHTML, /listed/);
  assert.equal(street.value, 'Polna');
});
