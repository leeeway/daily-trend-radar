#!/usr/bin/env python3
"""Durable daily completion checks, separate from the mere existence of Markdown."""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo


def today():
    value = os.getenv('RADAR_DATE') or dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    return dt.date.fromisoformat(value).isoformat()


def is_complete(root=Path('.'), date=None):
    date = date or today()
    marker = root / 'data/status' / f'{date}.json'
    if not marker.exists():
        return False
    data = json.loads(marker.read_text(encoding='utf-8'))
    return (data.get('date') == date and data.get('status') == 'complete'
            and (root / 'archives' / f'{date}.md').is_file()
            and (root / 'data/digests' / f'{date}.json').is_file())


def verify_site(url, date, attempts=6):
    """A successful deployment API call alone is not proof that today's post is live."""
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url.rstrip('/') + f'/latest.json?radar={date}-{time.time_ns()}', headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=20) as response:
                latest = json.loads(response.read())['latest']
            if latest['date'] != date:
                raise ValueError('Published latest.json is stale')
            with urllib.request.urlopen(url.rstrip('/') + f'/daily/{date}.html', timeout=20) as response:
                if date.encode() not in response.read():
                    raise ValueError('Published article is stale')
            print(f'Published digest verified: {date}')
            return
        except Exception:
            if attempt == attempts - 1:
                raise RuntimeError(f'Today\'s digest is not live after {attempts} checks') from None
            time.sleep(10)


def complete(root=Path('.')):
    date = today()
    receipt = root / 'data/delivery' / f'{date}.json'
    delivered = json.loads(receipt.read_text(encoding='utf-8')).get('delivered', {}) if receipt.exists() else {}
    marker = root / 'data/status' / f'{date}.json'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({'date': date, 'status': 'complete',
        'completed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'run_url': f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'leeeway/daily-trend-radar')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}",
        'delivered_channels': sorted(delivered)}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'check':
        automatic = os.getenv('GITHUB_EVENT_NAME') in ('schedule', 'repository_dispatch') or os.getenv('RECOVERY') == 'true'
        force = os.getenv('FORCE_REFRESH') == 'true'
        run = not (automatic and is_complete() and not force)
        if not run:
            try:
                verify_site(os.getenv('SITE_URL', 'https://leeeway.github.io/daily-trend-radar'), today(), attempts=1)
            except RuntimeError:
                run = True  # Completion marker exists, but the published site needs repair.
        output = f'run={str(run).lower()}\ndate={today()}\n'
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as handle:
                handle.write(output)
        print(output, end='')
    elif command == 'verify':
        verify_site(os.environ['SITE_URL'], today())
    elif command == 'complete':
        complete()
    else:
        raise SystemExit('Expected check, verify or complete')
