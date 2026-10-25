/* Private catalogue client. Requests and associations stay in the current tab. */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RentgenKWCatalogue = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function (root) {
  'use strict';
  const norm = value => String(value || '').normalize('NFC').trim().replace(/\s+/gu, ' ').toLocaleLowerCase('pl');
  const NUMBER = /^[A-Z]{2}[0-9][A-Z]\/[0-9]{8}\/[0-9]$/;
  const bad = () => { throw Error('Nieprawidłowa odpowiedź prywatnego katalogu KW.'); };
  function fields(value, required, optional = []) {
    if (!value || typeof value !== 'object' || Array.isArray(value)
        || required.some(key => !Object.hasOwn(value, key))
        || Object.keys(value).some(key => !required.includes(key) && !optional.includes(key))) bad();
  }
  function text(value, max = 500) {
    if (typeof value !== 'string' || !value.trim() || value.length > max || /\p{C}/u.test(value)) bad();
    return value.normalize('NFC').trim().replace(/\s+/gu, ' ');
  }
  function list(value, max, convert) {
    if (!Array.isArray(value) || value.length > max) bad();
    return value.map(convert);
  }
  function number(value) { if (typeof value !== 'string' || !NUMBER.test(value)) bad(); return value; }
  function address(value) {
    fields(value, ['city', 'street', 'number', 'unit']);
    return { city: text(value.city), street: text(value.street), number: text(value.number), unit: value.unit === null ? null : text(value.unit, 30) };
  }
  function query(value) {
    fields(value, ['city', 'street', 'number', 'register_type'], ['unit']);
    if (!['unit', 'land'].includes(value.register_type)) bad();
    const result = { city: text(value.city), street: text(value.street), number: text(value.number), register_type: value.register_type };
    if (value.register_type === 'unit') result.unit = text(value.unit, 30);
    else if (value.unit !== undefined && value.unit !== null && value.unit !== '') bad();
    return result;
  }
  function sameAddress(a, b) {
    return ['city', 'street', 'number', 'unit'].every(key => norm(a[key]) === norm(b[key]));
  }
  function source(value) {
    fields(value, ['url', 'observed_at', 'document_date', 'sha256', 'proof_kind', 'register_state_time_local']);
    const url = new URL(text(value.url, 2000));
    if (url.protocol !== 'https:' || !url.hostname || url.username || url.password) bad();
    const observed = text(value.observed_at, 60);
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(observed)
        || !Number.isFinite(Date.parse(observed)) || Date.parse(observed) > Date.now() + 30000) bad();
    const date = value.document_date;
    if (date !== null && (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)
        || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date)) bad();
    if (!/^[0-9a-f]{64}$/.test(value.sha256) || !['rendered_io_projection', 'published_property_source'].includes(value.proof_kind)) bad();
    const state = value.register_state_time_local;
    if (state !== null && (typeof state !== 'string' || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(state))) bad();
    return { url: url.href, observed_at: observed, document_date: date, sha256: value.sha256,
      proof_kind: value.proof_kind, register_state_time_local: state };
  }
  function candidate(value) {
    fields(value, ['kw_number', 'register_type', 'evidence_status', 'addresses', 'sources', 'source_count'],
      ['purpose', 'area_including_attached_m2', 'cadastral_unit_id']);
    if (!['unit', 'land'].includes(value.register_type) || !['observed_own_io', 'historical_source'].includes(value.evidence_status)) bad();
    const result = { kw_number: number(value.kw_number), register_type: value.register_type, evidence_status: value.evidence_status,
      addresses: list(value.addresses, 100, address), sources: list(value.sources, 200, source), source_count: value.source_count };
    if (!result.addresses.length || !result.sources.length || result.source_count !== result.sources.length
        || result.addresses.some(a => (value.register_type === 'unit') !== (a.unit !== null))) bad();
    if ((value.evidence_status === 'observed_own_io') !== result.sources.some(s => s.proof_kind === 'rendered_io_projection')) bad();
    if (Object.hasOwn(value, 'purpose')) result.purpose = value.purpose === null ? null : text(value.purpose);
    if (Object.hasOwn(value, 'area_including_attached_m2')) {
      const area = value.area_including_attached_m2;
      if (area !== null && (typeof area !== 'string' || !/^\d+(?:\.\d+)?$/.test(area) || Number(area) <= 0)) bad();
      result.area_including_attached_m2 = area;
    }
    if (Object.hasOwn(value, 'cadastral_unit_id')) result.cadastral_unit_id = value.cadastral_unit_id === null ? null : text(value.cadastral_unit_id);
    return result;
  }
  function validateResponse(value, requested) {
    fields(value, ['schema_version', 'query', 'status', 'candidate_kw_numbers', 'observed_kw_numbers',
      'candidates', 'land_context', 'available_units', 'verified_title', 'complete_coverage']);
    if (value.schema_version !== 1 || value.verified_title !== false || value.complete_coverage !== false
        || !['ambiguous', 'observed_own_io', 'candidate_unverified', 'land_context_only', 'no_match_in_catalogue'].includes(value.status)) bad();
    const expected = query(requested), returned = query(value.query);
    if (returned.register_type !== expected.register_type || !sameAddress(returned, expected)) bad();
    const candidates = list(value.candidates, 100, candidate), context = list(value.land_context, 100, candidate);
    if (candidates.some(c => c.register_type !== expected.register_type || !c.addresses.some(a => sameAddress(a, expected)))
        || context.some(c => c.register_type !== 'land' || !c.addresses.some(a => sameAddress(a, { ...expected, unit: null })))) bad();
    const keys = list(value.candidate_kw_numbers, 100, number), observed = list(value.observed_kw_numbers, 100, number);
    if (new Set(keys).size !== keys.length || new Set(observed).size !== observed.length
        || JSON.stringify([...keys].sort()) !== JSON.stringify(candidates.map(c => c.kw_number).sort())
        || JSON.stringify([...observed].sort()) !== JSON.stringify(candidates.filter(c => c.evidence_status === 'observed_own_io').map(c => c.kw_number).sort())) bad();
    const expectedStatus = keys.length > 1 ? 'ambiguous' : keys.length ? (observed.length ? 'observed_own_io' : 'candidate_unverified')
      : context.length ? 'land_context_only' : 'no_match_in_catalogue';
    if (value.status !== expectedStatus) bad();
    return { schema_version: 1, query: returned, status: value.status, candidates, land_context: context,
      candidate_kw_numbers: keys, observed_kw_numbers: observed, available_units: list(value.available_units, 1000, value => text(value)),
      verified_title: false, complete_coverage: false };
  }
  function isLocal(location) {
    return !!location && location.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]', '::1'].includes(location.hostname);
  }
  function createClient(options = {}) {
    const location = options.location || root.location, fetcher = options.fetch || (root.fetch && root.fetch.bind(root));
    const document = options.document || root.document;
    const marker = document && document.querySelector('meta[name="rentgen-kw-origin"]');
    // Only the private server inserts this marker. Public build assets contain
    // no deployment origin and make no discovery request on HTTPS Pages.
    const privateOrigin = !!location && location.protocol === 'https:' && !!location.origin
      && !!marker && marker.getAttribute('content') === location.origin;
    const available = (isLocal(location) || privateOrigin) && typeof fetcher === 'function';
    async function request(path, payload) {
      if (!available) throw Error('Prywatny katalog jest dostępny w prywatnej wersji Rentgena.');
      try {
        const response = await fetcher(path, { method: payload ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
          referrerPolicy: 'no-referrer', redirect: 'error', ...(payload ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } : {}) });
        if (!response.ok) throw Error('unavailable');
        const body = await response.text();
        if (body.length > 2 * 1024 * 1024) throw Error('oversize');
        return JSON.parse(body);
      } catch { throw Error('Nie udało się odczytać prywatnego katalogu. Sprawdź, czy lokalna usługa działa.'); }
    }
    return { available,
      async status() {
        const value = await request('/api/kw/status');
        fields(value, ['schema_version', 'service', 'catalogue'], ['verified_title', 'complete_coverage']);
        fields(value.catalogue, ['registers', 'observations', 'own_io_observations'], ['historical_observations', 'complete_unit_addresses',
          'pending_jobs', 'successful_jobs', 'source_paused', 'pause_reason']);
        if (value.schema_version !== 1 || value.service !== 'sprawdz-kw'
            || value.verified_title !== undefined && value.verified_title !== false
            || value.complete_coverage !== undefined && value.complete_coverage !== false) bad();
        for (const key of ['registers', 'observations', 'own_io_observations']) if (!Number.isSafeInteger(value.catalogue[key]) || value.catalogue[key] < 0) bad();
        if (value.catalogue.source_paused !== undefined && typeof value.catalogue.source_paused !== 'boolean') bad();
        if (value.catalogue.pause_reason != null && (typeof value.catalogue.pause_reason !== 'string' || !/^[a-z0-9_]{1,80}$/.test(value.catalogue.pause_reason))) bad();
        return { schema_version: 1, service: 'sprawdz-kw', catalogue: {
          registers: value.catalogue.registers, observations: value.catalogue.observations, own_io_observations: value.catalogue.own_io_observations,
          source_paused: value.catalogue.source_paused === true, pause_reason: value.catalogue.pause_reason || null } };
      },
      async search(value) { const input = query(value); return validateResponse(await request('/api/kw/search', input), input); },
    };
  }
  const evidenceLabel = value => value === 'observed_own_io' ? 'Odczyt własnego działu I-O' : 'Historyczne źródło · do sprawdzenia';
  const api = { query, validateResponse, createClient, isLocal, norm, sameAddress, evidenceLabel };
  return api;
});
