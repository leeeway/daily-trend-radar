import importlib.util
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from radar_catalog import build_catalog, safe_url, star_trend


class CatalogTests(unittest.TestCase):
    def test_legacy_archive_covers_all_sources_and_story_metrics(self):
        spec = importlib.util.spec_from_file_location('fetch', ROOT / 'scripts/fetch_radar.py')
        fetch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fetch)
        source = fetch.generate_markdown('2026-10-18',
            [dict(name='a/repo', url='https://example.com/repo', language='C++', stars=1234, forks=10, description='Build & learn')],
            [dict(title='A [useful] topic', url='https://example.com/story', score=17, comments=5, discuss_url='https://news.ycombinator.com/item?id=1')],
            [dict(ghsa_id='GHSA-test', url='https://example.com/advisory', severity='CRITICAL', cve_id='CVE-2026-1', summary='Fix now')])
        with tempfile.TemporaryDirectory() as tmp:
            entries = build_catalog(tmp, [dict(date='2026-10-18', url='https://example.com/daily', markdown=source)])
        self.assertEqual({e['kind'] for e in entries}, {'repos', 'stories', 'advisories'})
        story = next(e for e in entries if e['kind'] == 'stories')
        self.assertEqual(story['title'], 'A [useful] topic')
        self.assertEqual((story['score'], story['comments']), (17, 5))
        self.assertEqual(story['discuss_url'], 'https://news.ycombinator.com/item?id=1')
        repo = next(e for e in entries if e['kind'] == 'repos')
        self.assertEqual(repo['stars'], 1234)
        self.assertEqual(repo['description'], 'Build & learn')

    def test_full_snapshot_and_legacy_brief_merge_by_url_and_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data/digests'
            data.mkdir(parents=True)
            old = dict(name='a/repo', url='https://example.com/repo', description='first', stars=1)
            new = {**old, 'description': 'Full description, not a truncated table', 'stars': 99, 'unexpected': 'do not publish'}
            (data / '2026-10-18.json').write_text(json.dumps({'brief': {'repos': [old]}}))
            (data / '2026-10-20.json').write_text(json.dumps({'items': {'repos': [new], 'stories': [dict(title='snapshot only', url='https://example.com/story')]}}))
            posts = [dict(date=d, url=f'https://example.com/{d}', markdown='') for d in ('2026-10-20', '2026-10-18')]
            entries = build_catalog(tmp, posts)
            repo = next(e for e in entries if e['kind'] == 'repos')
            self.assertEqual(len(entries), 2)
            self.assertEqual(repo['dates'], ['2026-10-18', '2026-10-20'])
            self.assertEqual((repo['first_seen'], repo['last_seen']), ('2026-10-18', '2026-10-20'))
            self.assertEqual(repo['stars'], 99)
            self.assertEqual(repo['description'], new['description'])
            self.assertEqual(repo['star_history'], [{'date': '2026-10-18', 'stars': 1}, {'date': '2026-10-20', 'stars': 99}])
            self.assertEqual(repo['star_trend']['previous_delta'], 98)
            self.assertEqual(repo['star_trend']['previous_days'], 2)
            self.assertIsNone(repo['star_trend']['week_delta'])
            self.assertNotIn('unexpected', repo)
            self.assertEqual(repo['id'], next(e for e in build_catalog(tmp, posts[:1]) if e['kind'] == 'repos')['id'])

    def test_rejects_unsafe_links_without_breaking_build(self):
        for value in ('javascript:alert(1)', 'data:text/html,foo', '//example.com/', 'http://[bad'):
            self.assertEqual(safe_url(value), '')
        self.assertEqual(safe_url('https://example.com/a?b=c'), 'https://example.com/a?b=c')
        source = '## Repos\n\n| [Unsafe](javascript:alert) | Python | 1 | 2 | X |\n| --- | --- | --- | --- | --- |\n'
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build_catalog(tmp, [dict(date='2026-10-18', url='https://example.com/daily', markdown=source)]), [])

    def test_star_trend_requires_exact_seven_day_sample_and_keeps_negative_changes(self):
        history = [{'date': '2026-11-01', 'stars': 100}, {'date': '2026-11-05', 'stars': 120}, {'date': '2026-11-08', 'stars': 115}]
        trend = star_trend(history)
        self.assertEqual(trend['week_delta'], 15)
        self.assertEqual(trend['previous_delta'], -5)
        self.assertEqual(trend['previous_days'], 3)
        self.assertIsNone(star_trend(history[1:])['week_delta'])
        self.assertIsNone(star_trend(history[:1])['previous_delta'])
        self.assertIsNone(star_trend([])['week_delta'])
        self.assertEqual(star_trend([{'date': '2026-11-01', 'stars': 0}, {'date': '2026-11-08', 'stars': 0}])['week_delta'], 0)

    def test_missing_metric_is_not_a_zero_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'data/digests'
            directory.mkdir(parents=True)
            for date, stars in [('2026-11-01', 100), ('2026-11-02', None), ('2026-11-04', 120)]:
                (directory / f'{date}.json').write_text(json.dumps({'items': {'repos': [{'name': 'a/repo', 'url': 'https://example.com/repo', 'stars': stars}]}}))
            entries = build_catalog(tmp, [dict(date=date, url='https://example.com/daily', markdown='') for date in ('2026-11-01', '2026-11-02', '2026-11-04')])
            self.assertEqual(len(entries[0]['star_history']), 2)
            self.assertEqual(entries[0]['star_trend']['previous_delta'], 20)
            self.assertEqual(entries[0]['star_trend']['previous_days'], 3)
