/* Explicit, tab-local listing associations. A street or an RCN match is insufficient. */
(function (root, factory) {
  const api = factory(typeof module === 'object' && module.exports ? require('./kw.js') : root.RentgenKW,
    typeof module === 'object' && module.exports ? require('./kw-catalogue.js') : root.RentgenKWCatalogue);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RentgenKWLinks = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function (evidence, catalogue) {
  'use strict';
  const norm = s => String(s || '').normalize('NFC').trim().replace(/\s+/gu, ' ').toLocaleLowerCase('pl');
  function create() {
    let groups = new Map(), bindings = new Map(), count = 0;
    function eligible(listing, group) {
      const record = group.records[0];
      return !group.conflict && typeof listing.url === 'string' && /^https:\/\//.test(listing.url)
        && ((listing.type === 'flat' && record.register_type === 'unit') || (listing.type === 'house' && record.register_type === 'land'))
        && (!listing.locality || norm(listing.locality) === norm(record.address.city));
    }
    return {
      load(manifest) {
        const records = evidence.validate(manifest), conflicting = evidence.conflicts(records), next = new Map();
        for (const record of records) {
          const scope = evidence.scope(record), id = scope + '|' + record.kw_number;
          if (!next.has(id)) next.set(id, { id, records: [], conflict: conflicting.has(scope) });
          next.get(id).records.push(record);
        }
        groups = next; bindings = new Map(); count = records.length;
      },
      addCatalogue(response) {
        const validated = catalogue.validateResponse(response, response.query), added = [];
        for (const candidate of validated.candidates) {
          const address = candidate.addresses.find(a => catalogue.sameAddress(a, validated.query));
          const records = candidate.sources.map(source => ({ address, register_type: candidate.register_type,
            kw_number: candidate.kw_number, source, evidence_locator: 'Katalog źródłowy',
            evidence_status: source.proof_kind === 'rendered_io_projection' ? 'observed_own_io' : 'historical_source' }));
          const id = evidence.scope(records[0]) + '|' + candidate.kw_number;
          const previous = groups.get(id), combined = [...(previous ? previous.records : []), ...records];
          const seen = new Set(), retained = combined.filter(record => {
            const key = JSON.stringify([record.source.url, record.source.sha256, record.source.observed_at]);
            if (seen.has(key)) return false; seen.add(key); return true;
          });
          const group = { id, records: retained, conflict: validated.status === 'ambiguous', evidence_status: candidate.evidence_status,
            catalogue: true, area_including_attached_m2: candidate.area_including_attached_m2 };
          groups.set(id, group); added.push(group);
        }
        const conflicts = evidence.conflicts([...groups.values()].flatMap(group => group.records));
        for (const group of groups.values()) group.conflict = conflicts.has(evidence.scope(group.records[0]));
        count = [...groups.values()].reduce((total, group) => total + group.records.length, 0);
        return added;
      },
      clear() { groups.clear(); bindings.clear(); count = 0; },
      get size() { return count; },
      get linked() { return bindings.size; },
      choices(listing) { return [...groups.values()].filter(group => eligible(listing, group)); },
      get(listing) {
        const binding = bindings.get(listing.url), group = binding && groups.get(binding.id);
        return group && binding.type === listing.type && eligible(listing, group) ? group : null;
      },
      attach(listing, id, confirmed) {
        const group = groups.get(id);
        if (confirmed !== true || !group || !eligible(listing, group)) throw Error('Najpierw potwierdź pełny adres i właściwy rodzaj księgi.');
        bindings.set(listing.url, { id, type: listing.type });
      },
      remove(listing) { bindings.delete(listing.url); },
    };
  }
  return { create };
});
