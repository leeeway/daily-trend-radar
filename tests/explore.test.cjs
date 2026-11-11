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
