/* Shared by the browser and Node's dependency-free tests. */
(function (root) {
  'use strict';
  function select(entries, filters, saved, read = new Set()) {
    const words = (filters.q || '').normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    return entries.filter(entry => {
      if (filters.source && entry.kind !== filters.source) return false;
      if (filters.sort === 'growth' && (entry.kind !== 'repos' || entry.star_history?.at(-1)?.date !== filters.asOf ||
        !Number.isFinite(entry.star_trend?.week_delta))) return false;
      if (filters.saved && !saved.has(entry.id)) return false;
      if (filters.unread && read.has(entry.id)) return false;
      if (filters.fresh && entry.first_seen !== filters.asOf) return false;
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
  const readingType = 'leeway-radar-reading';
  function ids(value) {
    if (!Array.isArray(value) || value.length > 20000 ||
      value.some(id => typeof id !== 'string' || !/^[a-f0-9]{20}$/.test(id))) throw new Error('Invalid reading records');
    return [...new Set(value)].sort();
  }
  function parseBackup(text) {
    if (typeof text !== 'string' || text.length > 1048576) throw new Error('Backup is too large');
    const value = JSON.parse(text);
    if (!value || value.type !== readingType || value.version !== 1) throw new Error('Unsupported backup');
    return {type: readingType, version: 1, bookmarks: ids(value.bookmarks), read: ids(value.read)};
  }
  function loadReading(text, legacy) {
    if (text !== null) return parseBackup(text);
    return {type: readingType, version: 1, bookmarks: ids(JSON.parse(legacy || '[]')), read: []};
  }
  function mergeReading(current, incoming) {
    // Validate before returning anything: a rejected import cannot partly overwrite local state.
    const left = parseBackup(JSON.stringify(current));
    const right = parseBackup(JSON.stringify(incoming));
    return {type: readingType, version: 1,
      bookmarks: ids([...new Set([...left.bookmarks, ...right.bookmarks])]),
      read: ids([...new Set([...left.read, ...right.read])])};
  }
  const api = { select, chartPoints, parseBackup, loadReading, mergeReading, readingType };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RadarExplore = api;
})(globalThis);
