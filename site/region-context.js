"use strict";

// Small UMD helper so regional URL/state behavior is identical in app.js and
// stats.js and can be exercised by Node without a browser DOM.
(function expose(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RentgenRegion = api;
}(typeof globalThis !== "undefined" ? globalThis : this, () => {
  const validSlug = (value) => /^[a-z]+(?:-[a-z]+)*$/.test(value || "");

  function fromLocation(locationLike, page = "listings") {
    const path = String(locationLike.pathname || "").replace(/\/+$/, "");
    const pattern = page === "stats"
      ? /\/region\/([a-z]+(?:-[a-z]+)*)\/stats(?:\/index\.html)?$/
      : /\/region\/([a-z]+(?:-[a-z]+)*)(?:\/index\.html)?$/;
    const match = path.match(pattern);
    if (match) return match[1];
    const legacy = new URLSearchParams(locationLike.search || "").get("region");
    return validSlug(legacy) ? legacy : "slaskie";
  }

  const storageKey = (base, slug) => `${base}.${slug}`;

  function withFilter(href, snapshot, useDefault) {
    const url = new URL(href);
    if (useDefault) url.searchParams.delete("f");
    else url.searchParams.set("f", JSON.stringify(snapshot));
    return url.pathname + url.search + url.hash;
  }

  function pageHref(slug, page = "listings") {
    if (!validSlug(slug)) throw new Error(`invalid region slug: ${slug}`);
    return page === "stats" ? `region/${slug}/stats/` : `region/${slug}/`;
  }

  function pageUrl(slug, page, base) {
    return new URL(pageHref(slug, page), base).href;
  }

  const DISTANCES = new Set(["all", "5", "10", "15", "20", "30", "40"]);
  function distanceForRegion(value, hasAnchor) {
    const normalized = String(value ?? "all");
    return hasAnchor && DISTANCES.has(normalized) ? normalized : "all";
  }

  return Object.freeze({
    distanceForRegion, fromLocation, pageHref, pageUrl, storageKey, validSlug,
    withFilter,
  });
}));
