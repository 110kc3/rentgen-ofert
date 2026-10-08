/* Explicit, tab-local listing associations. A street or an RCN match is insufficient. */
(function (root, factory) {
  const api = factory(typeof module === 'object' && module.exports ? require('./kw.js') : root.RentgenKW);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RentgenKWLinks = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function (evidence) {
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
