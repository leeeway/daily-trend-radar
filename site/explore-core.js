/* Shared by the browser and Node's dependency-free tests. */
(function (root) {
  'use strict';
  function select(entries, filters, saved) {
    const words = (filters.q || '').normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    return entries.filter(entry => {
      if (filters.source && entry.kind !== filters.source) return false;
      if (filters.sort === 'growth' && (entry.kind !== 'repos' || entry.star_history?.at(-1)?.date !== filters.asOf ||
        !Number.isFinite(entry.star_trend?.week_delta))) return false;
      if (filters.saved && !saved.has(entry.id)) return false;
      // A repeated entry matches only if it was actually collected within the range.
      if ((filters.from || filters.to) && !entry.dates.some(date =>
        (!filters.from || date >= filters.from) && (!filters.to || date <= filters.to))) return false;
      const content = [entry.title, entry.description, entry.language, entry.cve, entry.severity, entry.url]
        .join(' ').normalize('NFKC').toLocaleLowerCase();
      return words.every(word => content.includes(word));
    }).sort((a, b) => {
      if (filters.sort === 'growth') return b.star_trend.week_delta - a.star_trend.week_delta || a.id.localeCompare(b.id);
      const field = filters.sort === 'oldest' ? 'first_seen' : 'last_seen';
      const order = a[field].localeCompare(b[field]) || a.id.localeCompare(b.id);
      return filters.sort === 'oldest' ? order : -order;
    });
  }
  function chartPoints(history, width = 300, height = 60) {
    if (history.length < 2) return [];
    const start = Date.parse(history[0].date + 'T00:00:00Z');
    const span = Date.parse(history[history.length - 1].date + 'T00:00:00Z') - start;
    if (!Number.isFinite(span) || span <= 0) return [];
    const values = history.map(sample => sample.stars);
    const min = Math.min(...values), max = Math.max(...values);
    return history.map(sample => ({
      x: 4 + (Date.parse(sample.date + 'T00:00:00Z') - start) / span * (width - 8),
      y: max === min ? height / 2 : height - 4 - (sample.stars - min) / (max - min) * (height - 8),
    }));
  }
  const api = { select, chartPoints };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RadarExplore = api;
})(globalThis);
