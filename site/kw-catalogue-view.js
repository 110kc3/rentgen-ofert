/* Address search in the user's local private catalogue; no persistent state. */
(function (root) {
  'use strict';
  if (!root.document || !root.document.getElementById('catalogue-form')) return;
  const $ = id => root.document.getElementById(id), client = root.RentgenKWCatalogue.createClient();
  const form = $('catalogue-form'), message = $('catalogue-result-status'), button = $('catalogue-search');
  let generation = 0;
  function el(tag, value, className) {
    const node = root.document.createElement(tag);
    if (value !== undefined) node.textContent = value;
    if (className) node.className = className;
    return node;
  }
  function reset() {
    generation++; $('catalogue-results').replaceChildren(); $('catalogue-land-context').replaceChildren();
    $('catalogue-land-context').hidden = true; message.textContent = ''; button.disabled = false;
  }
  function card(candidate) {
    const node = el('article', undefined, 'record'), address = candidate.addresses[0];
    node.append(el('span', root.RentgenKWCatalogue.evidenceLabel(candidate.evidence_status), 'badge ' + candidate.register_type));
    node.append(el('h2', `${address.street} ${address.number}${address.unit ? '/' + address.unit : ''}`), el('p', address.city, 'city'));
    node.append(el('p', candidate.register_type === 'unit' ? 'Księga lokalu' : 'Księga gruntu · nie zastępuje KW mieszkania'));
    const value = el('div', undefined, 'kw'), copy = el('button', 'Kopiuj numer'); copy.type = 'button';
    copy.addEventListener('click', async () => {
      try { await root.navigator.clipboard.writeText(candidate.kw_number); copy.textContent = 'Skopiowano'; }
      catch { copy.textContent = 'Zaznacz i skopiuj numer'; }
    });
    value.append(el('code', candidate.kw_number), copy); node.append(value);
    if (candidate.area_including_attached_m2) node.append(el('p', `Powierzchnia z pomieszczeniami przynależnymi: ${candidate.area_including_attached_m2} m²`, 'parent'));
    if (candidate.cadastral_unit_id) node.append(el('p', 'Identyfikator lokalu: ' + candidate.cadastral_unit_id, 'parent'));
    for (const source of candidate.sources) {
      const link = el('a', source.proof_kind === 'rendered_io_projection' ? 'Źródło: własny dział I-O ↗' : 'Ogłoszenie źródłowe ↗');
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; node.append(link);
      node.append(el('p', `Odczyt: ${source.observed_at}${source.register_state_time_local ? ' · Stan I-O: ' + source.register_state_time_local : ''}${source.document_date ? ' · Publikacja: ' + source.document_date : ''}`, 'dates'));
    }
    return node;
  }
  async function connect() {
    if (!client.available) return;
    $('catalogue-connect').disabled = true; $('catalogue-status').textContent = 'Łączenie z prywatnym katalogiem…';
    try {
      const status = await client.status();
      $('catalogue-status').textContent = `Połączono prywatny katalog: ${status.catalogue.registers} ksiąg, ${status.catalogue.observations} obserwacji.${status.catalogue.source_paused ? ' Pozyskiwanie nowych odczytów jest wstrzymane; zapisane dane można przeszukiwać.' : ''}`;
      form.hidden = false;
    } catch (error) { form.hidden = true; $('catalogue-status').textContent = error.message; }
    finally { $('catalogue-connect').disabled = false; }
  }
  $('catalogue-connect').hidden = !client.available;
  $('catalogue-connect').addEventListener('click', connect);
  if (client.available) connect();
  form.addEventListener('input', reset);
  $('catalogue-kind').addEventListener('change', () => {
    const unit = $('catalogue-kind').value === 'unit';
    $('catalogue-unit').required = unit; $('catalogue-unit').disabled = !unit;
    $('catalogue-unit-label').hidden = !unit; if (!unit) $('catalogue-unit').value = ''; reset();
  });
  $('catalogue-clear').addEventListener('click', () => {
    reset(); for (const field of ['city', 'street', 'number', 'unit']) $('catalogue-' + field).value = '';
    message.textContent = 'Wyszukiwanie i wyniki usunięte z tej karty.';
  });
  form.addEventListener('submit', async event => {
    event.preventDefault(); reset(); const current = generation; button.disabled = true;
    message.textContent = 'Szukanie po pełnym adresie…';
    try {
      const request = { city: $('catalogue-city').value, street: $('catalogue-street').value,
        number: $('catalogue-number').value, register_type: $('catalogue-kind').value };
      if (request.register_type === 'unit') request.unit = $('catalogue-unit').value;
      const response = await client.search(request); if (current !== generation) return;
      $('catalogue-results').replaceChildren(...response.candidates.map(card));
      message.textContent = response.status === 'ambiguous' ? 'Różne numery KW dla tego adresu. Porównaj wszystkie źródła.'
        : response.candidates.length ? `${response.candidates.length} księga dla pełnego adresu. Daty i źródła są poniżej.`
        : 'Brak rekordu dla tego pełnego adresu. To nie oznacza, że nieruchomość nie ma KW.';
      if (response.land_context.length) {
        const context = $('catalogue-land-context'); context.hidden = false; context.className = 'catalogue-context';
        context.append(el('h2', 'Kontekst gruntu — nie KW wybranego mieszkania'), ...response.land_context.map(card));
      }
    } catch (error) { if (current === generation) message.textContent = error.message; }
    finally { if (current === generation) button.disabled = false; }
  });
})(typeof globalThis === 'undefined' ? this : globalThis);
