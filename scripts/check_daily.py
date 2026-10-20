#!/usr/bin/env python3
"""Independent watchdog: inspect remote state and dispatch safe recovery via gh.
Run from any always-on host with Python 3.11+ and an authenticated GitHub CLI.
No repository write or webhook secret is needed on the watchdog host.
"""
import argparse
import base64
import datetime as dt
import json
import subprocess
import urllib.request
from zoneinfo import ZoneInfo

REPO = 'leeeway/daily-trend-radar'
SITE = 'https://leeeway.github.io/daily-trend-radar'


def gh(*args, json_output=True):
    result = subprocess.run(['gh', *args], text=True, capture_output=True, timeout=40)
    if result.returncode:
        if 'HTTP 404' in result.stderr:
            return None
        raise RuntimeError('GitHub request failed; check gh authentication and network access')
    if not json_output:
        return {}
    return json.loads(result.stdout) if result.stdout.strip() else {}


def remote_status(date):
    result = gh('api', f'repos/{REPO}/contents/data/status/{date}.json?ref=main')
    return json.loads(base64.b64decode(result['content'])) if result else {}


def inspect(date):
    status = remote_status(date)
    if status.get('date') != date or status.get('status') != 'complete':
        return False
    try:
        with urllib.request.urlopen(SITE + f'/latest.json?watchdog={date}', timeout=20) as response:
            latest = json.loads(response.read())['latest']
        return latest['date'] == date
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repair', action='store_true', help='Dispatch recovery when incomplete and no recent run is active')
    args = parser.parse_args()
    now = dt.datetime.now(ZoneInfo('Asia/Shanghai'))
    if (now.hour, now.minute) < (14, 37):
        print('Before the daily publication window; no recovery needed')
        return
    date = now.date().isoformat()
    if inspect(date):
        print(f'{date}: complete and public index is current')
        return
    runs = gh('run', 'list', '--repo', REPO, '--workflow', 'daily-sync.yml', '--limit', '30', '--json', 'databaseId,status,createdAt,url')
    for run in runs:
        created = dt.datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00'))
        age = now.astimezone(dt.timezone.utc) - created
        if run['status'] != 'completed' and age < dt.timedelta(minutes=30):
            print(f"Recovery already queued/running: {run['url']}")
            return
    if not args.repair:
        raise SystemExit(f'{date}: missing daily completion; run with --repair to recover')
    gh('workflow', 'run', 'daily-sync.yml', '--repo', REPO, '--ref', 'main', '-f', 'notify=true', '-f', 'recovery=true', json_output=False)
    print(f'{date}: recovery dispatched; only unfinished notification channels will be sent')


if __name__ == '__main__':
    main()
