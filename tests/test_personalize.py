import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import personalize
import notify
import daily_state


def digest():
    repos = [dict(name='owner/other', url='https://example.com/other', description='unrelated'),
             dict(name='owner/other2', url='https://example.com/other2', description='unrelated'),
             dict(name='owner/tool', url='https://example.com/tool', language='Python', stars=12, forks=1, description='A useful 中文工具.')]
    return {'title': '技术雷达 · 2026-11-11', 'text': 'legacy summary',
            'items': {'repos': repos, 'stories': [], 'advisories': []},
            'brief': {'date': '2026-11-11', 'url': 'https://example.com/daily', 'repos': repos[:2], 'stories': [], 'advisories': [], 'counts': [3, 0, 0]}}


class Response:
    def __init__(self, code=0): self.code = code
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps({'errcode': self.code}).encode()


class PersonalizeTests(unittest.TestCase):
    def test_filters_full_snapshot_not_only_original_push_picks(self):
        with tempfile.TemporaryDirectory() as root:
            selected = personalize.select_digest(digest(), {'RADAR_KEYWORDS': 'ＰＹＴＨＯＮ，PYTHON,其他词'}, root)
            self.assertEqual(selected['brief']['repos'][0]['name'], 'owner/tool')
            self.assertEqual(selected['brief']['counts'], [1, 0, 0])
            self.assertTrue(selected['brief']['personalized'])
            self.assertEqual(len(digest()['brief']['repos']), 2)
            self.assertEqual(len(personalize.select_digest(digest(), {}, root)['brief']['repos']), 2)
            self.assertIsNone(personalize.select_digest(digest(), {'RADAR_KEYWORDS': 'Python', 'RADAR_EXCLUDE_KEYWORDS': '中文工具'}, root))
            selected = personalize.select_digest(digest(), {'RADAR_EXCLUDE_KEYWORDS': 'unrelated'}, root)
            self.assertEqual(selected['brief']['counts'], [1, 0, 0])

    def test_preferences_support_phrases_unicode_json_and_overrides(self):
        self.assertEqual(personalize.keywords('AI Agent，Python\nＰＹＴＨＯＮ;中文'), ['ai agent', 'python', '中文'])
        for invalid in ('[invalid', '[1]', ['x' * 101], ['x'] * 51 + [str(n) for n in range(51)]):
            with self.assertRaises(ValueError): personalize.keywords(invalid)
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / 'config').mkdir()
            (Path(root) / 'config/notifications.json').write_text('{"keywords":["Rust"],"exclude_keywords":[]}')
            self.assertEqual(personalize.preferences({}, root)[0], ['rust'])
            self.assertEqual(personalize.preferences({'RADAR_KEYWORDS': '[]'}, root)[0], [])

    def test_legacy_archive_recovers_non_pick_items_and_missing_archive_fails(self):
        legacy = digest()
        legacy.pop('items')
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                personalize.select_digest(legacy, {'RADAR_KEYWORDS': 'Python'}, root)
            archive = Path(root) / 'archives'
            archive.mkdir()
            (archive / '2026-11-11.md').write_text('## Repos\n\n| Project | Language | Stars | Forks | Description |\n| --- | --- | --- | --- | --- |\n| [old/tool](https://example.com/tool) | Python | 11 | 0 | Archived tool |\n')
            selected = personalize.select_digest(legacy, {'RADAR_KEYWORDS': 'Python'}, root)
            self.assertEqual(selected['brief']['repos'][0]['name'], 'old/tool')
            self.assertIn('★ 11', notify.wechat_markdown(selected))

    def test_no_matches_is_durable_skip_not_delivery_and_completes_day(self):
        env = {'WECHAT_WEBHOOK': 'https://example.com/secret1', 'FEISHU_WEBHOOK': 'https://example.com/secret2', 'RADAR_KEYWORDS': 'no-match'}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            receipt = root / 'data/delivery/2026-11-11.json'
            with patch.object(notify.urllib.request, 'urlopen') as request:
                self.assertEqual(notify.send(digest(), env, receipt, root), [])
                # Changing keywords in a recovery must not undo the recorded decision.
                self.assertEqual(notify.send(digest(), {**env, 'RADAR_KEYWORDS': 'Python'}, receipt, root), [])
                request.assert_not_called()
            state = json.loads(receipt.read_text())
            self.assertEqual(state['delivered'], {})
            self.assertEqual(state['skipped'], {'企业微信': 'no_keyword_match', '飞书': 'no_keyword_match'})
            self.assertNotIn('secret', receipt.read_text())
            with patch.dict('os.environ', {'RADAR_DATE': '2026-11-11'}):
                daily_state.complete(root)
            marker = json.loads((root / 'data/status/2026-11-11.json').read_text())
            self.assertEqual(marker['status'], 'complete')
            self.assertEqual(marker['delivered_channels'], [])
            self.assertEqual(marker['skipped_channels'], state['skipped'])

    def test_partial_failure_retries_frozen_selection_even_after_preference_change(self):
        env = {'WECHAT_WEBHOOK': 'https://example.com/secret1', 'FEISHU_WEBHOOK': 'https://example.com/secret2', 'RADAR_KEYWORDS': 'Python'}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            receipt = Path(tmp) / 'receipt.json'
            with patch.object(notify.urllib.request, 'urlopen', side_effect=[Response(), Response(1)]):
                self.assertEqual(notify.send(digest(), env, receipt, tmp), ['飞书'])
            selection = json.loads(receipt.read_text())['selection']
            self.assertIn('owner/tool', selection['text'])
            self.assertNotIn('owner/other', selection['text'])
            with patch.object(notify.urllib.request, 'urlopen', return_value=Response()) as request:
                self.assertEqual(notify.send(digest(), {**env, 'RADAR_KEYWORDS': 'no-match'}, receipt, tmp), [])
                self.assertEqual(request.call_count, 1)
                self.assertEqual(json.loads(request.call_args[0][0].data)['content']['text'], selection['text'])
            self.assertNotIn('RADAR_KEYWORDS', receipt.read_text())
            self.assertNotIn('secret', receipt.read_text())

    def test_keyword_rendering_obeys_wecom_budget(self):
        selected = digest()
        selected['items']['repos'][2]['description'] = '中文' * 3000
        with tempfile.TemporaryDirectory() as root:
            filtered = personalize.select_digest(selected, {'RADAR_KEYWORDS': 'python'}, root)
        message = notify.wechat_markdown(filtered)
        self.assertIn('关注精选命中', message)
        self.assertIn('阅读完整早报', message)
        self.assertLessEqual(len(message.encode()), 4000)
        self.assertIn('owner/tool', notify.plain_brief(filtered))

    def test_pre_upgrade_partial_receipt_preserves_original_message(self):
        env = {'WECHAT_WEBHOOK': 'https://example.com/wechat', 'FEISHU_WEBHOOK': 'https://example.com/feishu', 'RADAR_KEYWORDS': 'no-match'}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            receipt = Path(tmp) / 'receipt.json'
            receipt.write_text(json.dumps({'date': '2026-11-11', 'delivered': {'企业微信': '2026-11-11T00:00:00Z'}}))
            with patch.object(notify.urllib.request, 'urlopen', return_value=Response()) as request:
                self.assertEqual(notify.send(digest(), env, receipt, tmp), [])
                self.assertEqual(request.call_count, 1)
                self.assertEqual(json.loads(request.call_args[0][0].data)['content']['text'], 'legacy summary')
