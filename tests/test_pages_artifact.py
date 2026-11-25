import contextlib
import http.client
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import wait_pages_artifact as pages


class Response:
    def __init__(self, artifacts):
        self.body = json.dumps({'artifacts': artifacts}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.body


class PagesArtifactTests(unittest.TestCase):
    def setUp(self):
        self.artifact = {'id': 123, 'name': 'github-pages', 'expired': False, 'size_in_bytes': 100}

    def wait(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return pages.wait_for_artifact('owner/repo', '456', '123', 'test-token', **kwargs)

    def test_waits_until_this_upload_is_visible(self):
        with patch.object(pages.urllib.request, 'urlopen', side_effect=[Response([]), Response([self.artifact])]) as request, patch.object(pages.time, 'sleep') as sleep:
            self.wait()
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_refuses_other_expired_or_empty_artifacts(self):
        invalid = [{**self.artifact, 'id': 999}, {**self.artifact, 'expired': True},
                   {**self.artifact, 'size_in_bytes': 0}, {**self.artifact, 'name': 'other'}]
        with patch.object(pages.urllib.request, 'urlopen', return_value=Response(invalid)), self.assertRaisesRegex(RuntimeError, 'unavailable after 1 checks'):
            self.wait(attempts=1)

    def test_retries_interrupted_api_responses(self):
        with patch.object(pages.urllib.request, 'urlopen', side_effect=[http.client.IncompleteRead(b''), Response([self.artifact])]) as request, patch.object(pages.time, 'sleep'):
            self.wait()
        self.assertEqual(request.call_count, 2)

    def test_permanent_auth_error_fails_without_retry_or_token(self):
        error = urllib.error.HTTPError('https://example.com', 403, 'test-token', {}, None)
        with patch.object(pages.urllib.request, 'urlopen', side_effect=error) as request, patch.object(pages.time, 'sleep') as sleep, self.assertRaisesRegex(RuntimeError, 'HTTP 403') as raised:
            self.wait()
        self.assertNotIn('test-token', str(raised.exception))
        request.assert_called_once()
        sleep.assert_not_called()

    def test_empty_api_results_stop_after_bounded_retries(self):
        with patch.object(pages.urllib.request, 'urlopen', return_value=Response([])) as request, patch.object(pages.time, 'sleep') as sleep, self.assertRaises(RuntimeError):
            self.wait(attempts=3)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
