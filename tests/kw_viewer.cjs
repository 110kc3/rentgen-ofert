const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validate, conflicts, scope, matches } = require('../site/kw.js');

// Fictional identifiers only: no real private address/KW evidence in this repository.
function fixture() {
  return { schema_version: 1, records: [{ address: { city: 'Gliwice', street: 'Testowa', number: '16A', unit: '05' },
    register_type: 'unit', kw_number: 'GL1G/00000002/0', parent_kw: 'GL1G/00000001/0',
    source: { url: 'https://example.invalid/notice/', observed_at: '2025-02-28T12:00:00+00:00', document_date: '2025-02-27', sha256: 'a'.repeat(64) },
    evidence_locator: 'Synthetic labelled flat and parent record' }] };
}
test('imports provenance and keeps flat and parent numbers separate', () => {
  const [r] = validate(fixture());
  assert.equal(r.kw_number, 'GL1G/00000002/0');
  assert.equal(r.parent_kw, 'GL1G/00000001/0');
  assert.equal(r.address.unit, '05');
  assert.equal(r.source.document_date, '2025-02-27');
  assert.equal(r.verified, undefined);
  assert.deepEqual(validate({ schema_version: 1, records: [] }), []);
});
test('rejects personal fields, claimed verification and malformed or unsafe provenance', () => {
  const changes = [
    r => r.owner = 'private', r => r.verified = true, r => r.address.extra = 'private',
    r => r.source.url = 'javascript:alert(1)', r => r.source.url = 'https://user:pass@example.invalid/',
    r => r.source.url = 'http://example.invalid/', r => r.source.sha256 = 'bad',
    r => r.source.observed_at = '2025-02-28', r => r.source.observed_at = '2999-01-01T00:00:00Z',
    r => r.source.observed_at = '2025-02-30T12:00:00Z', r => r.source.document_date = '2025-02-29',
    r => r.source.document_date = '2025-03-01', r => r.source.document_date = 123,
    r => r.address.city = 'Warszawa', r => r.address.street = '\u202ehidden',
    r => r.register_type = 'land', r => r.address.unit = null, r => r.kw_number = 'GL1G/x/0',
    r => r.parent_kw = r.kw_number, r => r.parcel = { number: '1', precinct: 'Test', owner: 'hidden' },
  ];
  for (const change of changes) { const m = fixture(); change(m.records[0]); assert.throws(() => validate(m)); }
  for (const m of [null, [], { ...fixture(), schema_version: true }, { ...fixture(), records: Array(1001).fill(fixture().records[0]) }]) assert.throws(() => validate(m));
});
test('exact building/unit filters preserve suffixes, leading zeros and land scope', () => {
  const [r] = validate(fixture());
  assert.ok(matches(r, { query: ' testowa ', number: '16a', unit: '05' }));
  for (const filters of [{ number: '16' }, { unit: '5' }, { query: 'Testówa' }, { kind: 'land' }]) assert.equal(matches(r, filters), false);
  const land = { ...r, register_type: 'land', address: { ...r.address, unit: null } };
  assert.equal(matches(land, { unit: '05' }), false);
  assert.ok(matches(r, { query: 'GL1G/00000001/0' })); // explicit parent reference is searchable
});
test('conflicts retain every source and are scoped to the exact address and type', () => {
  const [r] = validate(fixture()), second = { ...r, kw_number: 'GL1G/00000003/0' };
  assert.equal(conflicts([r, r]).size, 0);
  assert.ok(conflicts([r, second]).has(scope(r)));
  assert.equal(conflicts([r, { ...second, address: { ...r.address, unit: '5' } }]).size, 0);
  assert.equal(conflicts([r, { ...second, address: { ...r.address, number: '16' } }]).size, 0);
});

test('clear and a newer import invalidate outstanding file reads', async () => {
  const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
  function element() {
    return { value: '', files: [], hidden: false, disabled: false, handlers: {}, children: [],
      addEventListener(event, callback) { this.handlers[event] = callback; },
      append(...nodes) { this.children.push(...nodes); },
      replaceChildren(...nodes) { this.children = nodes; }, setAttribute() {} };
  }
  const elements = new Map(), context = vm.createContext({ URL, document: {
    getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
    createElement: element,
  } });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../site/kw.js'), 'utf8'), context);
  const get = id => elements.get(id), pending = () => {
    let resolve;
    get('file').files = [{ size: 100, text: () => new Promise(r => { resolve = r; }) }];
    const work = get('file').handlers.change();
    return { work, finish: () => resolve(JSON.stringify(fixture())) };
  };
  let old = pending();
  get('clear').handlers.click(); old.finish(); await old.work;
  assert.equal(get('browser').hidden, true);
  assert.equal(get('records').children.length, 0);
  old = pending();
  const latest = fixture(); latest.records[0].address.street = 'Nowsza';
  get('file').files = [{ size: 100, text: async () => JSON.stringify(latest) }];
  await get('file').handlers.change(); old.finish(); await old.work;
  assert.equal(get('records').children.length, 1);
  assert.equal(get('records').children[0].children[1].textContent, 'Nowsza 16A/05');
  assert.equal(get('browser').hidden, false);
});
