"""Select from the entire daily snapshot; preferences never become public site content."""
import copy
import datetime as dt
import json
from pathlib import Path
import re
import unicodedata

from radar_catalog import KINDS, daily_items

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    return unicodedata.normalize('NFKC', str(value or '')).casefold()


def keywords(value):
    if isinstance(value, str):
        if value.strip().startswith('['):
            try:
                value = json.loads(value)
            except ValueError:
                raise ValueError('Keyword configuration must be a valid JSON list or comma-separated text') from None
        else:
            value = re.split(r'[,，;；\n]', value)
    if not isinstance(value, list) or any(not isinstance(word, str) for word in value):
        raise ValueError('Keyword configuration must contain only strings')
    result = list(dict.fromkeys(normalize(word).strip() for word in value if word.strip()))
    if len(result) > 50 or any(len(word) > 100 for word in result):
        raise ValueError('Use at most 50 keywords of at most 100 characters each')
    return result


def preferences(env, root=ROOT):
    path = Path(root) / 'config/notifications.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('Notification configuration must be an object')
    def setting(env_key, key):
        override = env.get(env_key, '').strip()
        return keywords(override if override else config.get(key, []))
    return setting('RADAR_KEYWORDS', 'keywords'), setting('RADAR_EXCLUDE_KEYWORDS', 'exclude_keywords')


def select_digest(digest, env, root=ROOT):
    include, exclude = preferences(env, root)
    if not include and not exclude:
        return copy.deepcopy(digest)
    brief = digest.get('brief', {})
    date = dt.date.fromisoformat(brief['date']).isoformat()
    if isinstance(digest.get('items'), dict):
        items = digest['items']
    else:
        # Older digests contain only 2/2/1 selections: recover all archive entries.
        archive = Path(root) / 'archives' / f'{date}.md'
        if not archive.exists():
            raise ValueError('Keyword filtering requires full daily items or the matching archive')
        items = daily_items(root, {'date': date, 'markdown': archive.read_text(encoding='utf-8')})
    selected = {}
    fields = ('name', 'title', 'description', 'language', 'ghsa_id', 'cve_id', 'summary', 'url')
    for kind in KINDS:
        selected[kind] = []
        seen = set()
        for item in items.get(kind, []):
            content = normalize(' '.join(str(item.get(field) or '') for field in fields))
            if (include and not any(word in content for word in include)) or any(word in content for word in exclude):
                continue
            if item.get('url') not in seen:
                selected[kind].append(item)
                seen.add(item.get('url'))
    if not any(selected.values()):
        return None
    result = copy.deepcopy(digest)
    result.pop('items', None)
    result['brief'] = {**brief, **{kind: selected[kind][:limit] for kind, limit in zip(KINDS, (2, 2, 1))},
                       'counts': [len(selected[kind]) for kind in KINDS], 'personalized': True}
    return result
