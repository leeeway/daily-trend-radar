/* Shared by the browser and Node's dependency-free tests. */
(function (root) {
  'use strict';
  function select(entries, filters, saved) {
    const words = (filters.q || '').normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    return entries.filter(entry => {
      if (filters.source && entry.kind !== filters.source) return false;
      if (filters.saved && !saved.has(entry.id)) return false;
      // A repeated entry matches only if it was actually collected within the range.
      if ((filters.from || filters.to) && !entry.dates.some(date =>
        (!filters.from || date >= filters.from) && (!filters.to || date <= filters.to))) return false;
      const content = [entry.title, entry.description, entry.language, entry.cve, entry.severity, entry.url]
        .join(' ').normalize('NFKC').toLocaleLowerCase();
      return words.every(word => content.includes(word));
    }).sort((a, b) => {
      const field = filters.sort === 'oldest' ? 'first_seen' : 'last_seen';
      const order = a[field].localeCompare(b[field]) || a.id.localeCompare(b.id);
      return filters.sort === 'oldest' ? order : -order;
    });
  }
  const api = { select };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RadarExplore = api;
})(globalThis);
