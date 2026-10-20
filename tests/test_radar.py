import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

site = module('build_site')
notify = module('notify')
fetch = module('fetch_radar')
state = module('daily_state')
watchdog = module('check_daily')

class RadarTests(unittest.TestCase):
    def test_build_nested_pages_feeds_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'archives').mkdir()
            (root / 'site').mkdir()
            text = '# Daily\n\n## Repos\n\n| [a](https://example.com/a) | Python | 1 | 0 | hello |\n\n## HN\n\n1. **[Topic](https://example.com/b)**\n\n## Security\n\n| [GHSA](https://example.com/c) | CRITICAL | CVE | desc |\n'
            for day in ['2026-10-17', '2026-10-18']:
                (root / 'archives' / f'{day}.md').write_text(text)
            with patch.object(site, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                site.build(root / 'dist', 'https://example.com/radar')
            out = root / 'dist'
            weekly = (out / 'weekly/2026-W42.md').read_text()
            self.assertEqual(weekly.count('https://example.com/a'), 1)
            self.assertIn('../daily/2026-10-18.html', weekly)
            self.assertIn('../assets/style.css', (out / 'daily/2026-10-18.html').read_text())
            self.assertEqual(json.loads((out / 'latest.json').read_text())['latest']['date'], '2026-10-18')
            self.assertEqual(len(ET.parse(out / 'feed.xml').findall('./channel/item')), 2)

    def test_sanitizes_untrusted_html_and_links(self):
        rendered = site.render('<script>alert(1)</script> [x](javascript:alert(1)) <img src=x onerror=evil()>')
        self.assertNotIn('<script', rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertNotIn('<img', rendered)

    def test_all_source_failure_preserves_files(self):
        with patch.object(fetch, 'get_github_trending', return_value=[]), patch.object(fetch, 'get_hackernews_top', return_value=[]), patch.object(fetch, 'get_security_advisories', return_value=[]), patch('builtins.open') as write:
            with self.assertRaises(RuntimeError), contextlib.redirect_stdout(io.StringIO()):
                fetch.main()
            write.assert_not_called()

    def test_channel_signatures_and_optional_channels(self):
        digest = {'title':'技术雷达', 'text':'Hello'}
        self.assertEqual(notify.deliveries(digest, {}), [])
        env = {'DINGTALK_WEBHOOK':'https://example.com/?access_token=fake', 'DINGTALK_SECRET':'secret', 'FEISHU_WEBHOOK':'https://example.com/hook', 'FEISHU_SECRET':'secret', 'WECHAT_WEBHOOK':'https://example.com/wechat', 'TELEGRAM_BOT_TOKEN':'fake', 'TELEGRAM_CHAT_ID':'1', 'SERVERCHAN_SENDKEY':'fake'}
        with patch.object(notify.time, 'time', return_value=1700000000):
            jobs = notify.deliveries(digest, env)
        self.assertEqual(len(jobs), 5)
        self.assertIn('timestamp=1700000000000&sign=', jobs[1][1])
        self.assertEqual(jobs[2][2]['timestamp'], '1700000000')
        self.assertTrue(jobs[2][2]['sign'])

    def test_wechat_brief_has_sections_metrics_and_links(self):
        digest = {'title': '技术雷达', 'text': 'legacy', 'brief': {
            'date': '2026-10-18', 'url': 'https://example.com/daily.html',
            'counts': [8, 8, 6],
            'repos': [{'name': 'owner/repo', 'url': 'https://github.com/owner/repo', 'description': 'Create interactive illustrations of complex systems.', 'language': 'JavaScript', 'stars': 15526, 'forks': 1188}],
            'stories': [{'title': 'A developer story', 'url': 'https://example.com/story', 'score': 193, 'comments': 92, 'discuss_url': 'https://news.ycombinator.com/item?id=1'}],
            'advisories': [{'ghsa_id': 'GHSA-test', 'cve_id': 'CVE-2026-1234', 'summary': 'Authentication bypass in a package.', 'url': 'https://github.com/advisories/test'}]}}
        text = notify.wechat_markdown(digest)
        for item in ['开源发现', '开发者在聊', '安全提醒', '15,526', '92 条评论', 'CVE-2026-1234', '修复建议', 'https://example.com/daily.html']:
            self.assertIn(item, text)
        payload = notify.deliveries(digest, {'WECHAT_WEBHOOK': 'https://example.com/hook'})[0][2]
        self.assertEqual(payload['markdown']['content'], text)
        self.assertLessEqual(len(text.encode('utf-8')), 4096)

    def test_wechat_budget_handles_chinese_and_long_urls(self):
        digest = {'text': 'legacy', 'brief': {'date': '2026-10-18', 'url': 'https://example.com/daily', 'counts': [8, 8, 6], 'repos': [{'name': '<script>**项目**', 'url': 'https://example.com/' + 'x' * 5000, 'description': '中文简介' * 500, 'stars': 1, 'forks': 0}]}}
        text = notify.wechat_markdown(digest)
        self.assertLessEqual(len(text.encode('utf-8')), 4096)
        self.assertIn('阅读完整早报', text)
        self.assertNotIn('<script>', text)
        self.assertEqual(notify.wechat_markdown({'text': 'old artifact'}), 'old artifact')
        self.assertEqual(notify.safe_link('text', 'javascript:alert(1)'), 'text')

    def test_excerpt_keeps_sentence_and_word_boundaries(self):
        self.assertEqual(notify.excerpt('First sentence. Another very long sentence after it.', 25), 'First sentence.')
        self.assertEqual(notify.excerpt('An agent skill for creating detailed illustrations', 24), 'An agent skill for…')
        self.assertEqual(notify.excerpt('短句。第二句内容比较长。继续长。', 8), '短句。第二句内…')

    def test_fetch_recovery_reuses_durable_payload(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp), patch.dict(os.environ, {'RADAR_DATE': '2026-10-20', 'RECOVERY': 'true', 'FORCE_REFRESH': 'false'}):
            Path('README.md').write_text('<!-- radar:start -->old<!-- radar:end -->')
            Path('archives').mkdir()
            # A legacy archive alone must not block recovery; create its missing payload.
            Path('archives/2026-10-20.md').write_text('legacy')
            repo = {'name':'owner/repo', 'url':'https://example.com/repo', 'description':'desc', 'stars':1, 'forks':0, 'language':'Python'}
            with patch.object(fetch, 'get_github_trending', return_value=[repo]), patch.object(fetch, 'get_hackernews_top', return_value=[]), patch.object(fetch, 'get_security_advisories', return_value=[]), contextlib.redirect_stdout(io.StringIO()):
                fetch.main()
            stored = Path('data/digests/2026-10-20.json').read_text()
            self.assertEqual(json.loads(stored)['brief']['date'], '2026-10-20')
            Path('notification.json').unlink()
            with patch.object(fetch, 'get_github_trending', side_effect=AssertionError('must not refetch')), contextlib.redirect_stdout(io.StringIO()):
                fetch.main()
            self.assertEqual(Path('notification.json').read_text(), stored)
            self.assertTrue(Path('commit_summary.txt').is_file())

    def test_receipts_retry_only_failed_channels(self):
        class Response:
            def __init__(self, code): self.code = code
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'errcode':self.code}).encode()
        env = {'WECHAT_WEBHOOK':'https://example.com/wechat', 'FEISHU_WEBHOOK':'https://example.com/feishu'}
        digest = {'title':'test', 'text':'test'}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            receipt = Path(tmp) / 'receipt.json'
            with patch.object(notify.urllib.request, 'urlopen', side_effect=[Response(0), Response(1)]) as request:
                self.assertEqual(notify.send(digest, env, receipt), ['飞书'])
                self.assertEqual(request.call_count, 2)
            self.assertIn('企业微信', json.loads(receipt.read_text())['delivered'])
            with patch.object(notify.urllib.request, 'urlopen', return_value=Response(0)) as request:
                self.assertEqual(notify.send(digest, env, receipt), [])
                self.assertEqual(request.call_count, 1)
                self.assertEqual(request.call_args[0][0].full_url, env['FEISHU_WEBHOOK'])
            with patch.object(notify.urllib.request, 'urlopen') as request:
                self.assertEqual(notify.send(digest, env, receipt), [])
                request.assert_not_called()

    def test_completion_requires_more_than_markdown(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'RADAR_DATE':'2026-10-20'}):
            root = Path(tmp)
            (root / 'archives').mkdir()
            (root / 'archives/2026-10-20.md').touch()
            self.assertFalse(state.is_complete(root))
            state.complete(root)
            self.assertFalse(state.is_complete(root))
            (root / 'data/digests').mkdir()
            (root / 'data/digests/2026-10-20.json').write_text('{}')
            self.assertTrue(state.is_complete(root))
            self.assertFalse(state.is_complete(root, '2026-10-21'))

    def test_publication_check_rejects_stale_index(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"latest":{"date":"2026-10-19"}}'
        with patch.object(state.urllib.request, 'urlopen', return_value=Response()), self.assertRaises(RuntimeError):
            state.verify_site('https://example.com', '2026-10-20', attempts=1)

    def test_source_transient_failure_retries(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"items":[]}'
        with patch.object(fetch.urllib.request, 'urlopen', side_effect=[TimeoutError(), Response()]) as request, patch.object(fetch.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fetch.fetch_json('https://example.com'), {'items':[]})
            self.assertEqual(request.call_count, 2)

    def test_provider_failure_does_not_stop_other_channels_or_leak_secrets(self):
        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(self.data).encode()
        output = io.StringIO()
        with patch.object(notify.urllib.request, 'urlopen', side_effect=[Response({'errcode':1}), Response({'code':0})]) as send, contextlib.redirect_stdout(output):
            failures = notify.send({'title':'技术雷达', 'text':'Hi'}, {'WECHAT_WEBHOOK':'https://example.com/SECRET', 'FEISHU_WEBHOOK':'https://example.com/SECRET2'})
        self.assertEqual(failures, ['企业微信'])
        self.assertEqual(send.call_count, 2)
        self.assertNotIn('SECRET', output.getvalue())

if __name__ == '__main__':
    unittest.main()
