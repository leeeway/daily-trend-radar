"""Build a searchable, deduplicated catalogue from full snapshots and legacy Markdown."""
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import markdown

KINDS = ('repos', 'stories', 'advisories')


def safe_url(value):
    value = str(value or '').strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ''
    return value if parsed.scheme in ('https', 'http') and parsed.netloc else ''


class ArchiveParser(HTMLParser):
    """Read the three historical sections without depending on Markdown link regexes."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = -1
        self.cells = None
        self.cell = None
        self.story = None
        self.link = None
        self.items = {kind: [] for kind in KINDS}

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.section += 1
        if tag == 'tr':
            self.cells = []
        if tag == 'td':
            self.cell = {'text': '', 'links': []}
        if tag == 'li' and self.section == 1:
            self.story = {'text': '', 'links': []}
        if tag == 'a':
            self.link = {'url': dict(attrs).get('href', ''), 'text': ''}
        if tag in ('br', 'p'):
            self.handle_data(' ')

    def handle_data(self, data):
        for target in (self.cell, self.story, self.link):
            if target is not None:
                target['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.link is not None:
            for target in (self.cell, self.story):
                if target is not None:
                    target['links'].append(self.link)
            self.link = None
        if tag == 'td' and self.cell is not None:
            self.cells.append(self.cell)
            self.cell = None
        if tag == 'tr' and self.cells:
            cells = self.cells
            if cells[0]['links']:
                first = cells[0]['links'][0]
                values = [' '.join(c['text'].split()) for c in cells]
                if self.section == 0 and len(cells) >= 5:
                    self.items['repos'].append(dict(name=first['text'], url=first['url'], language=values[1], stars=values[2], forks=values[3], description=values[4]))
                if self.section == 2 and len(cells) >= 4:
                    self.items['advisories'].append(dict(ghsa_id=first['text'], url=first['url'], severity=values[1], cve_id=values[2], summary=values[3]))
            self.cells = None
        if tag == 'li' and self.story is not None:
            links = self.story['links']
            if links:
                story = dict(title=links[0]['text'], url=links[0]['url'], discuss_url=links[1]['url'] if len(links) > 1 else '')
                metrics = re.search(r'👍\s*([\d,]+)\s*points\s*·\s*💬\s*([\d,]+)', self.story['text'])
                if metrics:
                    story.update(score=metrics[1], comments=metrics[2])
                self.items['stories'].append(story)
            self.story = None


def daily_items(root, post):
    parser = ArchiveParser()
    parser.feed(markdown.markdown(post['markdown'], extensions=['tables']))
    combined = parser.items
    path = Path(root) / 'data' / 'digests' / f"{post['date']}.json"
    if path.exists():
        # Full snapshots are additive. Old brief-only payloads enrich the legacy archive.
        payload = json.loads(path.read_text(encoding='utf-8'))
        snapshot = payload.get('items', payload.get('brief', {}))
        for kind in KINDS:
            by_url = {item['url']: item for item in combined[kind]}
            for item in snapshot.get(kind, []):
                if isinstance(item, dict) and safe_url(item.get('url')):
                    by_url[item['url']] = {**by_url.get(item['url'], {}), **item}
            combined[kind] = list(by_url.values())
    return combined


def build_catalog(root, posts):
    entries = {}
    for post in sorted(posts, key=lambda p: p['date']):
        for kind, items in daily_items(root, post).items():
            for item in items:
                url = safe_url(item.get('url'))
                title = item.get('name') or item.get('title') or item.get('ghsa_id')
                if not url or not title:
                    continue
                key = kind + ':' + url
                previous = entries.get(key, {})
                dates = sorted(set(previous.get('dates', []) + [post['date']]))
                entry = {
                    'id': hashlib.sha256(key.encode()).hexdigest()[:20],
                    'kind': kind, 'title': str(title), 'url': url,
                    'description': str(item.get('description') or item.get('summary') or ''),
                    'language': str(item.get('language') or ''),
                    'cve': str(item.get('cve_id') or ''),
                    'severity': str(item.get('severity') or ''),
                    'discuss_url': safe_url(item.get('discuss_url')),
                    'dates': dates, 'first_seen': dates[0], 'last_seen': dates[-1],
                    'daily_url': post['url'],
                }
                for metric in ('stars', 'forks', 'score', 'comments'):
                    try:
                        entry[metric] = int(str(item[metric]).replace(',', ''))
                    except (KeyError, ValueError, TypeError):
                        pass
                entries[key] = entry
    return sorted(entries.values(), key=lambda e: (e['last_seen'], e['id']), reverse=True)
