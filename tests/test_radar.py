import contextlib
import datetime as dt
import importlib.util
import io
import json
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
