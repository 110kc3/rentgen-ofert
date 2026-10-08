const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const { create } = require('../site/kw-links.js');
const source = fs.readFileSync(path.join(__dirname, '../site/app.js'), 'utf8');
const flat = { url: 'https://example.invalid/flat', type: 'flat', locality: 'Gliwice', price: 400000, area: 50 };
const house = { ...flat, url: 'https://example.invalid/house', type: 'house' };
function manifest() {
  const record = { address: { city: 'Gliwice', street: 'Testowa', number: '16', unit: '5' }, register_type: 'unit',
    kw_number: 'GL1G/00000002/0', parent_kw: 'GL1G/00000001/0', evidence_locator: 'Synthetic fixture',
    source: { url: 'https://example.invalid/notice', observed_at: '2025-01-02T10:00:00Z', document_date: '2025-01-01', sha256: 'a'.repeat(64) } };
  const land = { ...record, register_type: 'land', address: { ...record.address, unit: null }, kw_number: record.parent_kw };
  delete land.parent_kw;
  return { schema_version: 1, records: [record, land] };
}
test('only an explicit confirmed link marks the exact offer URL as having a KW', () => {
  const links = create(); links.load(manifest());
  assert.equal(links.get(flat), null);
  const choice = links.choices(flat)[0];
  assert.throws(() => links.attach(flat, choice.id, false));
  assert.equal(links.get(flat), null);
  links.attach(flat, choice.id, true);
  assert.equal(links.get(flat).records[0].kw_number, 'GL1G/00000002/0');
  assert.equal(links.get({ ...flat, url: flat.url + '-neighbor' }), null);
  assert.equal(links.get({ ...flat, type: 'house' }), null);
  assert.equal(links.get({ ...flat, locality: 'Zabrze' }), null);
  links.remove(flat); assert.equal(links.get(flat), null);
});
test('flat cannot use land KW; house can link its land, with incompatible city rejected', () => {
  const links = create(); links.load(manifest());
  assert.equal(links.choices(flat).length, 1);
  assert.equal(links.choices(house).length, 1);
  const land = links.choices(house)[0];
  assert.throws(() => links.attach(flat, land.id, true));
  links.attach(house, land.id, true);
  assert.equal(links.get(house).records[0].register_type, 'land');
  assert.equal(links.choices({ ...flat, locality: 'Zabrze' }).length, 0);
  assert.equal(links.choices({ ...flat, url: 'javascript:alert(1)' }).length, 0);
});
test('conflicting flat KWs cannot be chosen; repeated sources retain provenance', () => {
  const links = create(), data = manifest();
  data.records.push({ ...data.records[0], source: { ...data.records[0].source, url: 'https://example.invalid/second' } });
  links.load(data); assert.equal(links.choices(flat)[0].records.length, 2);
  data.records.push({ ...data.records[0], kw_number: 'GL1G/00000003/0' });
  links.load(data); assert.equal(links.choices(flat).length, 0);
  assert.equal(links.choices(house).length, 1);
});
test('clear and successful replacement discard every association', () => {
  const links = create(); links.load(manifest());
  links.attach(flat, links.choices(flat)[0].id, true);
  links.load(manifest()); assert.equal(links.get(flat), null);
  links.attach(flat, links.choices(flat)[0].id, true);
  links.clear(); assert.equal(links.size, 0); assert.equal(links.linked, 0); assert.equal(links.get(flat), null);
});
function appContext() {
  const links = create(); links.load(manifest()); links.attach(flat, links.choices(flat)[0].id, true);
  const empty = { value: '' }, state = { type: 'all', source: 'all', owner: 'all', history: 'all', market: 'all', distance: 'all', localities: [], sort: 'newest', kwOnly: true };
  const c = vm.createContext({ state, kwOf: l => links.get(l), inArchive: () => ['sold', 'sold_rcn'].includes(state.history),
    normLoc: s => s, $: () => empty, setSeg() {}, apply() {}, renderLocalityList() {},
    TYPE_LABEL: {}, SRC_LABEL: {}, OWNER_LABEL: {}, HIST_LABEL: {}, MARKET_LABEL: {}, label: s => s });
  for (const [start, end] of [
    ['function passes(', '// ---- "cena vs'], ['function countWithout(', 'function topTowns('],
    ['function snapshot()', 'function isDefault('], ['function clearFilter(', 'function wireChips('],
    ['function resetAll()', '// ---- active-filter'], ['function activeFilters()', '// ---- empty state'],
  ]) vm.runInContext(source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))), c);
  return c;
}
test('the actual filter combines KW, property type, price and archive rules', () => {
  const c = appContext();
  assert.equal(c.passes(flat, {}), true);
  assert.equal(c.passes(house, {}), false);
  assert.equal(c.passes(flat, { minPrice: 500000 }), false);
  c.state.type = 'house'; assert.equal(c.passes(flat, {}), false);
  c.state.type = 'all'; c.state.history = 'sold';
  assert.equal(c.passes({ ...flat, delisted: '2025-02-01' }, {}), true);
  c.state.history = 'sold_rcn'; assert.equal(c.passes(flat, {}), false);
  assert.equal(c.passes({ ...flat, sold: true }, {}), true);
});
test('KW chip, relaxed counts and reset restore the filter without leaking private state', () => {
  const c = appContext();
  assert.ok(c.activeFilters().some(f => f.k === 'kw'));
  assert.equal(c.countWithout([flat, house], {}, 'kw'), 2);
  assert.equal(c.state.kwOnly, true);
  const snapshot = JSON.stringify(c.snapshot());
  assert.equal(snapshot.includes('kw'), false);
  assert.equal(snapshot.includes('GL1G'), false);
  c.clearFilter('kw'); assert.equal(c.state.kwOnly, false);
  c.state.kwOnly = true; c.resetAll(); assert.equal(c.state.kwOnly, false);
});

test('the listing import handler cannot restore a cleared or superseded file', async () => {
  const nodes = new Map(), links = create(), state = { kwOnly: false };
  const node = () => ({ files: [], value: '', handlers: {}, disabled: false,
    addEventListener(event, handler) { this.handlers[event] = handler; }, close() {} });
  const get = id => { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); };
  const context = vm.createContext({ $: get, state, kwLinks: links, RentgenKW: require('../site/kw.js'), render() {} });
  vm.runInContext(source.slice(source.indexOf('function wireKW()'), source.indexOf('// ---- persistence')), context);
  context.wireKW();
  function pending() {
    let resolve;
    get('#kw-file').files = [{ size: 10, text: () => new Promise(r => { resolve = r; }) }];
    const work = get('#kw-file').handlers.change();
    return { work, resolve: text => resolve(text) };
  }
  const first = pending(); get('#kw-clear').handlers.click(); first.resolve(JSON.stringify(manifest())); await first.work;
  assert.equal(links.size, 0); assert.equal(state.kwOnly, false);
  const older = pending(), newer = pending();
  newer.resolve(JSON.stringify(manifest())); await newer.work;
  const message = get('#kw-status').textContent;
  older.resolve('invalid JSON'); await older.work;
  assert.equal(links.size, 2); assert.equal(get('#kw-status').textContent, message);
});
