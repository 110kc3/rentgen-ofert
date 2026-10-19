/* Optional regional storage: resolve once, then pin every request to a version. */
(function (root) {
  "use strict";
  async function json(url, fetcher, options = {}) {
    const response = await fetcher(url, { credentials: "omit", ...options });
    if (!response.ok) throw Error(`Storage HTTP ${response.status}`);
    return response.json();
  }

  async function resolve(entry, base, fetcher = root.fetch.bind(root)) {
    const fallback = `data/${entry.slug}`;
    if (entry.storage === undefined) return { data: fallback, manifest: null, pinned: false };
    const config = entry.storage;
    if (!config || typeof config.pointer_url !== "string" || !config.pointer_url)
      throw Error("Invalid regional storage configuration");
    const pointerURL = new URL(config.pointer_url, base);
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(pointerURL.hostname);
    if ((pointerURL.protocol !== "https:" && !(local && pointerURL.protocol === "http:"))
        || pointerURL.username || pointerURL.password || pointerURL.search || pointerURL.hash
        || !pointerURL.pathname.endsWith("/current.json"))
      throw Error("Invalid regional storage URL");
    // A generated deployment can seal the catalog to a verified version. It
    // must not follow a newer pointer before its summaries/catalog are rebuilt.
    if (config.version !== undefined && (typeof config.version !== "string"
        || !/^[a-f0-9]{64}$/.test(config.version)))
      throw Error("Invalid regional storage version");
    const pointer = config.version !== undefined ? { schema: 1, version: config.version }
      : await json(pointerURL.href, fetcher, { cache: "no-store" });
    if (!pointer || pointer.schema !== 1 || typeof pointer.version !== "string"
        || !/^[a-f0-9]{64}$/.test(pointer.version))
      throw Error("Invalid regional storage pointer");
    const data = new URL(`versions/${pointer.version}/`, pointerURL).href.replace(/\/$/, "");
    const manifest = await json(`${data}/manifest.json`, fetcher);
    if (!manifest || ![1, 2, 3].includes(manifest.schema || 1))
      throw Error("Unsupported stored payload");
    return { data, manifest, pinned: true };
  }

  root.RentgenStorage = { resolve };
  if (typeof module !== "undefined" && module.exports) module.exports = root.RentgenStorage;
})(typeof globalThis !== "undefined" ? globalThis : this);
