const { test } = require('node:test');
const assert = require('node:assert/strict');
const { select } = require('../site/explore-core.js');
const entries = [
  { id: 'repo', kind: 'repos', title: 'Owner/Radar', description: '交互式技术手记', language: 'Python', url: 'https://example.com/repo', dates: ['2026-10-18', '2026-10-20'], first_seen: '2026-10-18', last_seen: '2026-10-20' },
  { id: 'story', kind: 'stories', title: 'Python in production', url: 'https://example.com/story', dates: ['2026-10-19'], first_seen: '2026-10-19', last_seen: '2026-10-19' },
  { id: 'security', kind: 'advisories', title: 'GHSA-test', cve: 'CVE-2026-1', severity: 'CRITICAL', url: 'https://example.com/advisory', dates: ['2026-10-21'], first_seen: '2026-10-21', last_seen: '2026-10-21' },
];
const ids = (filters, saved = new Set()) => select(entries, filters, saved).map(e => e.id);
test('keyword search normalizes case and width and requires every word', () => {
  assert.deepEqual(ids({q: 'ＰＹＴＨＯＮ radar'}), ['repo']);
  assert.deepEqual(ids({q: '技术'}), ['repo']);
  assert.deepEqual(ids({q: 'cve-2026-1'}), ['security']);
  assert.deepEqual(ids({q: 'critical'}), ['security']);
  assert.deepEqual(ids({q: '<script>'}), []);
});
test('date ranges match actual observations, not the gap between first and last', () => {
  assert.deepEqual(ids({from: '2026-10-19', to: '2026-10-19'}), ['story']);
  assert.deepEqual(ids({from: '2026-10-20', to: '2026-10-20'}), ['repo']);
  assert.deepEqual(ids({from: '2026-10-21', to: '2026-10-18'}), []);
});
test('category and saved filters combine, including an empty saved list', () => {
  assert.deepEqual(ids({saved: true}), []);
  assert.deepEqual(ids({saved: true, source: 'repos'}, new Set(['repo', 'story'])), ['repo']);
  assert.deepEqual(ids({source: 'stories'}), ['story']);
});
test('sort is deterministic and leaves the source array unchanged', () => {
  assert.deepEqual(ids({}), ['security', 'repo', 'story']);
  assert.deepEqual(ids({sort: 'oldest'}), ['repo', 'story', 'security']);
  assert.deepEqual(entries.map(e => e.id), ['repo', 'story', 'security']);
});

test('growth ranking uses a real seven-day baseline in the latest issue, preserves zero and negative changes', () => {
  const dated = (id, value, date = '2026-11-11') => ({...entries[0], id, last_seen: date,
    star_history: [{date}], star_trend: {week_delta: value}});
  const rows = [dated('winner', 500), dated('flat', 0), dated('decline', -10), dated('short', null), dated('stale', 1000, '2026-11-10'), entries[1]];
  assert.deepEqual(select(rows, {sort: 'growth', asOf: '2026-11-11'}, new Set()).map(e => e.id), ['winner', 'flat', 'decline']);
  assert.deepEqual(select(rows, {sort: 'growth', asOf: '2026-11-11', source: 'stories'}, new Set()), []);
});
test('sparkline spaces samples by actual dates and handles flat and missing data', () => {
  const {chartPoints} = require('../site/explore-core.js');
  const points = chartPoints([{date:'2026-11-01',stars:10},{date:'2026-11-02',stars:10},{date:'2026-11-05',stars:10}]);
  assert.equal(points[0].y, points[2].y);
  assert.equal((points[1].x - points[0].x) / (points[2].x - points[0].x), .25);
  assert.deepEqual(chartPoints([]), []);
  assert.deepEqual(chartPoints([{date:'2026-11-01',stars:10}]), []);
  assert.deepEqual(chartPoints([{date:'2026-11-01',stars:10},{date:'2026-11-01',stars:20}]), []);
});

test('unread and latest-first-seen filters combine without treating reappearances as new', () => {
  assert.deepEqual(select(entries, {unread:true}, new Set(), new Set(['repo', 'security'])).map(e=>e.id), ['story']);
  assert.deepEqual(select(entries, {unread:true,saved:true}, new Set(['repo','story']), new Set(['repo'])).map(e=>e.id), ['story']);
  assert.deepEqual(select(entries, {fresh:true,asOf:'2026-10-20'}, new Set()), []);
  assert.deepEqual(select(entries, {fresh:true,asOf:'2026-10-21'}, new Set()).map(e=>e.id), ['security']);
  assert.deepEqual(select(entries, {fresh:true,asOf:'2026-10-21',to:'2026-10-20'}, new Set()), []);
});
test('reading state migrates legacy bookmarks and prefers the current atomic state', () => {
  const {loadReading,readingType} = require('../site/explore-core.js');
  const first = 'a'.repeat(20), second = 'b'.repeat(20);
  assert.deepEqual(loadReading(null, JSON.stringify([first,first])), {type:readingType,version:1,bookmarks:[first],read:[]});
  const current = {type:readingType,version:1,bookmarks:[second],read:[first]};
  assert.deepEqual(loadReading(JSON.stringify(current), JSON.stringify([first])), current);
  assert.deepEqual(loadReading(null, null).bookmarks, []);
});
test('backup round-trip preserves and merges both lists without mutating existing data', () => {
  const {parseBackup,mergeReading,readingType} = require('../site/explore-core.js');
  const first='a'.repeat(20), second='b'.repeat(20), third='c'.repeat(20);
  const current={type:readingType,version:1,bookmarks:[first],read:[second]};
  const incoming=parseBackup(JSON.stringify({type:readingType,version:1,bookmarks:[third,first],read:[first,first],created_at:'2026-11-11T00:00:00Z'}));
  assert.deepEqual(mergeReading(current,incoming), {type:readingType,version:1,bookmarks:[first,third],read:[first,second]});
  assert.deepEqual(current.read,[second]);
  assert.deepEqual(current.bookmarks,[first]);
});
test('rejects foreign, malformed, oversized or executable-looking backups before merging', () => {
  const {parseBackup,mergeReading,readingType} = require('../site/explore-core.js');
  const current={type:readingType,version:1,bookmarks:['a'.repeat(20)],read:[]};
  const invalid=[{},null,{...current,version:2},{...current,type:'other-app'},
    {...current,bookmarks:['<script>alert(1)</script>']}, {...current,read:{}},
    {...current,read:Array(20001).fill('a'.repeat(20))}];
  for(const value of invalid) assert.throws(()=>parseBackup(JSON.stringify(value)));
  assert.throws(()=>parseBackup('{bad json'));
  assert.throws(()=>parseBackup(' '.repeat(1048577)));
  assert.throws(()=>mergeReading(current, {...current,read:['invalid']}));
  assert.deepEqual(current.read,[]);
});
