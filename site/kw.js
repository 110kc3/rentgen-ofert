/* Local-only evidence viewer. No fetch, storage, telemetry or automatic KW assignment. */
(function (root) {
  'use strict';
  const MAX_BYTES = 4 * 1024 * 1024;
  const KW = /^[A-Z]{2}[0-9][A-Z]\/[0-9]{8}\/[0-9]$/;
  const norm = value => value.normalize('NFC').trim().replace(/\s+/gu, ' ').toLocaleLowerCase('pl');
  function fields(value, required, optional = []) {
    if (!value || typeof value !== 'object' || Array.isArray(value)
        || required.some(k => !Object.hasOwn(value, k))
        || Object.keys(value).some(k => !required.includes(k) && !optional.includes(k))) throw Error('Nieobsługiwane pola pliku.');
  }
  function text(value, max = 200) {
    if (typeof value !== 'string' || !value.trim() || value.length > max || /\p{C}/u.test(value)) throw Error('Nieprawidłowe pole tekstowe.');
    return value.normalize('NFC').trim().replace(/\s+/gu, ' ');
  }
  function kw(value) {
    if (typeof value !== 'string' || !KW.test(value)) throw Error('Nieprawidłowy format KW.');
    return value;
  }
  function calendarDate(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  }
  function validate(manifest) {
    fields(manifest, ['schema_version', 'records']);
    if (manifest.schema_version !== 1 || !Array.isArray(manifest.records) || manifest.records.length > 1000) throw Error('Wymagany plik records.json w wersji 1, do 1000 obserwacji.');
    return manifest.records.map(r => {
      fields(r, ['address', 'register_type', 'kw_number', 'source', 'evidence_locator'], ['parcel', 'parent_kw']);
      fields(r.address, ['city', 'street', 'number', 'unit']);
      const a = r.address, address = { city: text(a.city), street: text(a.street), number: text(a.number), unit: a.unit === null ? null : text(a.unit, 30) };
      if (norm(address.city) !== 'gliwice') throw Error('Ten pilotaż obsługuje Gliwice.');
      if (!['land', 'unit'].includes(r.register_type) || (r.register_type === 'land') !== (address.unit === null)) throw Error('Rodzaj księgi nie zgadza się z adresem lokalu.');
      fields(r.source, ['url', 'observed_at', 'document_date', 'sha256']);
      const s = r.source, url = new URL(text(s.url, 2000));
      if (url.protocol !== 'https:' || !url.hostname || url.username || url.password) throw Error('Źródło musi być adresem HTTPS bez danych logowania.');
      const observed = text(s.observed_at, 50), date = s.document_date;
      if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(observed)
          || !calendarDate(observed.slice(0, 10)) || !Number.isFinite(Date.parse(observed)) || Date.parse(observed) > Date.now()) throw Error('Nieprawidłowa data odczytu.');
      if (date !== null && (typeof date !== 'string' || !calendarDate(date) || date > observed.slice(0, 10))) throw Error('Nieprawidłowa data publikacji.');
      if (typeof s.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(s.sha256)) throw Error('Brak prawidłowego skrótu źródła.');
      const result = { address, register_type: r.register_type, kw_number: kw(r.kw_number), evidence_locator: text(r.evidence_locator, 500),
        source: { url: url.href, observed_at: observed, document_date: date, sha256: s.sha256 } };
      if (r.parent_kw != null) {
        result.parent_kw = kw(r.parent_kw);
        if (r.register_type !== 'unit' || result.parent_kw === result.kw_number) throw Error('Nieprawidłowa księga macierzysta.');
      }
      if (r.parcel != null) {
        fields(r.parcel, ['number', 'precinct']);
        result.parcel = { number: text(r.parcel.number), precinct: text(r.parcel.precinct) };
      }
      return result;
    });
  }
  const scope = r => JSON.stringify([r.register_type, ...['city', 'street', 'number', 'unit'].map(k => norm(r.address[k] || ''))]);
  function conflicts(records) {
    const scopes = new Map();
    for (const r of records) {
      const key = scope(r);
      if (!scopes.has(key)) scopes.set(key, new Set());
      scopes.get(key).add(r.kw_number);
    }
    return new Set([...scopes].filter(([, numbers]) => numbers.size > 1).map(([key]) => key));
  }
  function matches(r, f) {
    const a = r.address;
    return (!f.kind || r.register_type === f.kind)
      && (!norm(f.number || '') || norm(a.number) === norm(f.number))
      && (!norm(f.unit || '') || (a.unit !== null && norm(a.unit) === norm(f.unit)))
      && norm([a.city, a.street, a.number, a.unit || '', r.kw_number, r.parent_kw || ''].join(' ')).includes(norm(f.query || ''));
  }
  const api = { validate, conflicts, scope, matches, MAX_BYTES };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (!root.document) return;
  const $ = id => root.document.getElementById(id);
  let records = [], conflictScopes = new Set(), generation = 0;
  const el = (tag, content, className) => {
    const node = root.document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (className) node.className = className;
    return node;
  };
  function card(r) {
    const a = r.address, s = r.source, node = el('article', undefined, 'record');
    node.append(el('span', r.register_type === 'unit' ? 'KW LOKALU · DO SPRAWDZENIA' : 'KW GRUNTU · NIE KW LOKALU', 'badge ' + r.register_type));
    node.append(el('h2', `${a.street} ${a.number}${a.unit ? '/' + a.unit : ''}`), el('p', a.city, 'city'));
    if (conflictScopes.has(scope(r))) node.append(el('p', 'Źródła podają różne KW dla tego adresu. Sprawdź wszystkie obserwacje.', 'conflict'));
    const value = el('div', undefined, 'kw'), copy = el('button', 'Kopiuj numer');
    copy.type = 'button'; copy.setAttribute('aria-label', `Kopiuj ${r.kw_number}`);
    copy.addEventListener('click', async () => {
      try { await root.navigator.clipboard.writeText(r.kw_number); copy.textContent = 'Skopiowano'; }
      catch { copy.textContent = 'Zaznacz i skopiuj numer'; }
    });
    value.append(el('code', r.kw_number), copy); node.append(value);
    if (r.parent_kw) node.append(el('p', 'Księga macierzysta: ' + r.parent_kw, 'parent'));
    if (r.parcel) node.append(el('p', `Działka ${r.parcel.number}, obręb ${r.parcel.precinct}`, 'parent'));
    const link = el('a', 'Otwórz ogłoszenie źródłowe ↗', 'source-link');
    link.href = s.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; node.append(link);
    node.append(el('p', `Publikacja: ${s.document_date || 'brak daty'} · Odczyt: ${s.observed_at.slice(0, 10)}`, 'dates'));
    const details = el('details'); details.append(el('summary', 'Pochodzenie rekordu'), el('p', r.evidence_locator), el('p', 'SHA-256: ' + s.sha256)); node.append(details);
    return node;
  }
  function render() {
    const filters = Object.fromEntries(['query', 'number', 'unit', 'kind'].map(k => [k, $(k).value]));
    const visible = records.filter(r => matches(r, filters));
    $('records').replaceChildren(...visible.map(card));
    const units = new Set(records.filter(r => r.register_type === 'unit').map(r => r.kw_number)).size;
    const lands = new Set(records.filter(r => r.register_type === 'land').map(r => r.kw_number)).size;
    $('count').textContent = `${visible.length} / ${records.length} obserwacji · w pliku: ${units} ksiąg lokali, ${lands} ksiąg gruntów`;
    $('empty').hidden = visible.length !== 0;
  }
  function reset() {
    records = []; conflictScopes = new Set(); $('records').replaceChildren(); $('browser').hidden = true; $('clear').disabled = true;
    for (const k of ['query', 'number', 'unit', 'kind']) $(k).value = '';
  }
  $('file').addEventListener('change', async () => {
    const file = $('file').files[0], current = ++generation;
    reset(); if (!file) return;
    $('clear').disabled = false; $('message').textContent = 'Odczytywanie pliku…';
    try {
      if (file.size > MAX_BYTES) throw Error('Plik przekracza 4 MiB.');
      const body = await file.text(); if (current !== generation) return;
      records = validate(JSON.parse(body));
      records.sort((x, y) => [x.address.street, x.address.number, x.address.unit || '', x.kw_number].join(' ').localeCompare(
        [y.address.street, y.address.number, y.address.unit || '', y.kw_number].join(' '), 'pl', { numeric: true }));
      conflictScopes = conflicts(records); $('browser').hidden = false;
      $('message').textContent = `Wczytano ${records.length} obserwacji. Dane pozostają w tej karcie.`; render();
    } catch (error) {
      if (current !== generation) return;
      reset(); $('message').textContent = `Nie wczytano pliku. ${error instanceof SyntaxError ? 'Nieprawidłowy JSON.' : error.message}`;
    } finally { if (current === generation) $('file').value = ''; }
  });
  $('clear').addEventListener('click', () => { generation++; reset(); $('file').value = ''; $('message').textContent = 'Dane usunięte z tej karty.'; });
  for (const k of ['query', 'number', 'unit', 'kind']) $(k).addEventListener('input', render);
})(typeof globalThis === 'undefined' ? this : globalThis);
