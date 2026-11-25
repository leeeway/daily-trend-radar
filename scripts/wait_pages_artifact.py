#!/usr/bin/env python3
"""Wait for the uploaded Pages artifact to appear in this run's artifact API."""
import http.client
import json
import os
import time
import urllib.error
import urllib.request


def wait_for_artifact(repository, run_id, artifact_id, token, attempts=6, delay=5):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?name=github-pages&per_page=100',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'DailyTrendRadar/1.0'},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                artifacts = json.loads(response.read()).get('artifacts', [])
            for artifact in artifacts:
                if (str(artifact.get('id')) == str(artifact_id)
                        and artifact.get('name') == 'github-pages'
                        and not artifact.get('expired', True)
                        and artifact.get('size_in_bytes', 0) > 0):
                    print(f'Pages artifact {artifact_id} is ready for deployment')
                    return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise RuntimeError(f'Cannot inspect Pages artifact (HTTP {exc.code}); check Actions read permission') from None
        except (OSError, http.client.HTTPException, ValueError):
            pass  # Retry interrupted responses without logging credentials or response bodies.
        if attempt < attempts - 1:
            print(f'Pages artifact not available yet; retry {attempt + 1}/{attempts}')
            time.sleep(delay)
    raise RuntimeError(f'Uploaded Pages artifact {artifact_id} is unavailable after {attempts} checks')


if __name__ == '__main__':
    wait_for_artifact(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_RUN_ID'],
                      os.environ['PAGES_ARTIFACT_ID'], os.environ['GH_TOKEN'])
