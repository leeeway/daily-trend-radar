/* Shared by the browser and Node's dependency-free tests. */
(function (root) {
  'use strict';
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase();
  const contentOf = entry => normalize([entry.title, entry.description, entry.language, entry.cve, entry.severity, entry.url].join(' '));
  function terms(value = []) {
    if (typeof value === 'string') {
      if (value.length > 8192) throw new Error('关注词输入过长');
      value = value.split(/[,，;；\r\n]+/);
    }
    if (!Array.isArray(value) || value.length > 200 || value.some(word => typeof word !== 'string')) throw new Error('关注词格式无效');
    const seen = new Set(), result = [];
    for (const word of value) {
      const label = word.normalize('NFKC').trim();
      if (label.length > 80) throw new Error('每个词最多 80 个字符');
      if (label && !seen.has(normalize(label))) { seen.add(normalize(label)); result.push(label); }
    }
    if (result.length > 40) throw new Error('关注词和排除词各最多 40 个');
    return result;
  }
  function parseInterests(value = {}) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('关注设置无效');
    return {include: terms(value.include), exclude: terms(value.exclude)};
  }
  function interestMatch(entry, interests) {
    const content = contentOf(entry);
    const included = interests.include.filter(word => content.includes(normalize(word)));
    const excluded = interests.exclude.filter(word => content.includes(normalize(word)));
    return {included, excluded, matches: !!(interests.include.length || interests.exclude.length) &&
      (!interests.include.length || included.length > 0) && excluded.length === 0};
  }
  function select(entries, filters, saved, read = new Set(), interests = {include:[], exclude:[]}) {
    const words = (filters.q || '').normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    return entries.filter(entry => {
      if (filters.source && entry.kind !== filters.source) return false;
      if (filters.sort === 'growth' && (entry.kind !== 'repos' || entry.star_history?.at(-1)?.date !== filters.asOf ||
        !Number.isFinite(entry.star_trend?.week_delta))) return false;
      if (filters.saved && !saved.has(entry.id)) return false;
      if (filters.unread && read.has(entry.id)) return false;
      if (filters.fresh && entry.first_seen !== filters.asOf) return false;
      if (filters.following && !interestMatch(entry, interests).matches) return false;
      // A repeated entry matches only if it was actually collected within the range.
      if ((filters.from || filters.to) && !entry.dates.some(date =>
        (!filters.from || date >= filters.from) && (!filters.to || date <= filters.to))) return false;
      const content = contentOf(entry);
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
    return {type: readingType, version: 1, bookmarks: ids(value.bookmarks), read: ids(value.read),
      interests: parseInterests(value.interests)};
  }
  function loadReading(text, legacy) {
    if (text !== null) return parseBackup(text);
    return {type: readingType, version: 1, bookmarks: ids(JSON.parse(legacy || '[]')), read: [], interests: parseInterests()};
  }
  function mergeReading(current, incoming) {
    // Validate before returning anything: a rejected import cannot partly overwrite local state.
    const left = parseBackup(JSON.stringify(current));
    const right = parseBackup(JSON.stringify(incoming));
    return {type: readingType, version: 1,
      bookmarks: ids([...new Set([...left.bookmarks, ...right.bookmarks])]),
      read: ids([...new Set([...left.read, ...right.read])]),
      interests: parseInterests({include:[...left.interests.include, ...right.interests.include],
        exclude:[...left.interests.exclude, ...right.interests.exclude]})};
  }
  const api = { select, chartPoints, parseBackup, loadReading, mergeReading, readingType, parseInterests, interestMatch };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RadarExplore = api;
})(globalThis);
