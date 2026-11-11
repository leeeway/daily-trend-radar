#!/usr/bin/env python3
"""Compile archived Markdown into a portable blog, weekly digests and feeds."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from email.utils import format_datetime
import markdown
import bleach
from radar_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = 'https://leeeway.github.io/daily-trend-radar'
TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {'p','h1','h2','h3','h4','hr','br','table','thead','tbody','tr','th','td','pre'}


def render(source):
    return bleach.clean(markdown.markdown(source, extensions=['tables', 'fenced_code']), tags=TAGS,
                        attributes={'a': ['href', 'title'], 'code': ['class']}, strip=True)


def page(title, body, base, canonical, compact=False):
    esc = html.escape
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · leeway 技术雷达</title>
<meta name="description" content="leeway 的技术日报与每周回顾：开源项目、开发者话题与安全动态。">
<link rel="canonical" href="{esc(canonical)}"><link rel="alternate" type="application/rss+xml" title="技术雷达" href="{base}/feed.xml">
<link rel="stylesheet" href="{base}/assets/style.css"></head><body class="{'compact' if compact else ''}">
<header><a class="brand" href="{base}/">leeway<span> / RADAR</span></a><nav><a href="{base}/">日报与周报</a><a href="{base}/explore.html">发现与收藏</a><a href="{base}/feed.xml">RSS ↗</a><a href="https://lwblog.cn/" target="_top">个人主页 ↗</a></nav></header>
<main>{body}</main><footer>持续学习，保持好奇。<span>GitHub & Hacker News · 自动汇编，原始来源见各条链接</span></footer></body></html>'''


def build(output=None, site_url=None):
    out = Path(output or ROOT / 'dist')
    url = (site_url or os.getenv('SITE_URL') or DEFAULT_URL).rstrip('/')
    if not url.startswith('https://'):
        raise ValueError('SITE_URL must start with https://')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'site', out / 'assets', dirs_exist_ok=True)
    posts = []
    weeks = {}
    for path in sorted((ROOT / 'archives').glob('*.md'), reverse=True):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', path.stem):
            continue
        date = dt.date.fromisoformat(path.stem)
        source = path.read_text(encoding='utf-8')
        post = {'date': path.stem, 'title': f'{path.stem} 技术早报', 'url': f'{url}/daily/{path.stem}.html', 'markdown': source}
        posts.append(post)
        year, week, _ = date.isocalendar()
        weeks.setdefault(f'{year}-W{week:02d}', []).append(post)
        target = out / 'daily' / f'{path.stem}.html'
        target.parent.mkdir(exist_ok=True)
        target.write_text(page(post['title'], f'<article>{render(source)}</article>', '..', post['url']), encoding='utf-8')
    if not posts:
        raise ValueError('No daily archives to publish')
    catalog = build_catalog(ROOT, posts)
    discoveries = {kind: sum(entry['first_seen'] == posts[0]['date'] and entry['kind'] == kind for entry in catalog)
                   for kind in ('repos', 'stories', 'advisories')}
    discoveries.update(date=posts[0]['date'], total=sum(discoveries.values()))
    (out / 'search-index.json').write_text(json.dumps({'version': 1, 'latest_date': posts[0]['date'], 'entries': catalog}, ensure_ascii=False, indent=2), encoding='utf-8')
    explore = '''<section class="explore-heading"><p class="eyebrow">YOUR GROWING TECH LIBRARY</p><h1>发现，留存，<em>再回来看。</em></h1><p class="intro">搜索历期资讯，把值得细读的内容收进自己的书签。</p></section>
<form id="explore-form" class="filter-panel" role="search">
<label class="search-label" for="query">搜索资讯</label><input id="query" name="q" type="search" placeholder="项目、技术关键词、语言或 CVE 编号…" autocomplete="off">
<div class="filters"><label>来源<select id="source" name="source"><option value="">全部来源</option><option value="repos">开源项目</option><option value="stories">开发者热议</option><option value="advisories">安全公告</option></select></label>
<label>收录起始日期<input id="from-date" name="from" type="date"></label><label>收录结束日期<input id="to-date" name="to" type="date"></label>
<label>排序<select id="sort" name="sort"><option value="newest">最近收录</option><option value="oldest">最早收录</option><option value="growth">最新一期 7 日 Star 增长</option></select></label></div>
<div class="filter-actions"><div class="reading-filters"><label class="saved-filter"><input type="checkbox" id="saved-only" name="saved" value="1"> 只看收藏 <span id="saved-count">0</span></label>
<label class="saved-filter"><input type="checkbox" id="unread-only" name="unread" value="1"> 只看未读</label>
<label class="saved-filter"><input type="checkbox" id="fresh-only" name="fresh" value="1"> 最新一期首次收录</label></div><button type="reset" class="text-button">重置筛选</button></div></form>
<div class="results-heading"><p id="result-count" role="status" aria-live="polite">正在加载资讯库…</p><span>相同来源链接合并展示</span></div>
<p class="storage-note">日期按实际收录时间筛选；指标为收录快照。7 日增长排序只比较最新一期、且具备相隔 7 天采样的项目。</p>
<div class="reading-toolbar"><p id="storage-note" class="storage-note">收藏和已读记录仅保存在此浏览器，可备份后在其他设备恢复。</p>
<div><button id="export-reading" class="text-button" type="button">备份阅读记录</button><button id="import-reading" class="text-button" type="button">恢复记录</button>
<input id="reading-file" type="file" accept=".json,application/json" hidden></div></div>
<p id="reading-status" class="storage-note" role="status" aria-live="polite"></p>
<div id="results" class="results-grid"></div><button id="load-more" class="button" hidden>加载更多</button><button id="retry-load" class="text-button" hidden>重新加载</button>
<noscript><p>搜索和收藏需要 JavaScript。你仍可<a href="./">浏览全部日报与周报</a>。</p></noscript>
<script src="./assets/explore-core.js" defer></script><script src="./assets/explore.js" defer></script>'''
    (out / 'explore.html').write_text(page('发现与收藏', explore, '.', url + '/explore.html'), encoding='utf-8')
    weekly_cards = []
    for week, days in weeks.items():
        # Deduplicate source entries by primary URL, preserving the newest snapshot.
        sections = [[], [], []]
        seen = set()
        for post in days:
            section = -1
            for line in post['markdown'].splitlines():
                if line.startswith('## '):
                    section += 1
                link = re.search(r'\]\((https?://[^)]+)\)', line)
                if 0 <= section < 3 and link and link[1] not in seen:
                    seen.add(link[1])
                    sections[section].append(line)
        md = f'# {week} 技术周报\n\n> 本周持续更新 · 已收录 {len(days)} 天，按来源链接去重。这里是资讯汇编，尚未加入人工点评。\n\n'
        headings = ['开源项目', '开发者热议', '安全公告']
        for i, lines in enumerate(sections):
            md += f'## {headings[i]}\n\n'
            if i in (0, 2) and lines:
                md += ('| 项目 | 语言 | Stars | Forks | 简介 |\n| --- | --- | --- | --- | --- |\n' if i == 0 else '| 公告 | 等级 | CVE | 简介 |\n| --- | --- | --- | --- |\n')
            md += '\n'.join(lines) + '\n\n'
        md += '## 本周日报\n\n' + '\n'.join(f"- [{p['title']}](../daily/{p['date']}.html)" for p in days)
        (out / 'weekly').mkdir(exist_ok=True)
        (out / 'weekly' / f'{week}.html').write_text(page(week + ' 技术周报', f'<article>{render(md)}</article>', '..', f'{url}/weekly/{week}.html'), encoding='utf-8')
        (out / 'weekly' / f'{week}.md').write_text(md, encoding='utf-8')
        weekly_cards.append(f'<a class="card weekly" href="weekly/{week}.html"><span>WEEKLY / {len(days)} DAYS</span><h3>{week} 周报</h3><p>一周技术动态，去重归档。</p><b>阅读周报 ↗</b></a>')
    latest = posts[0]
    daily_cards = ''.join(f'<a class="card" href="daily/{p["date"]}.html"><span>DAILY BRIEF</span><h3>{p["date"]}</h3><p>开源 · 热议 · 安全动态</p><b>阅读早报 ↗</b></a>' for p in posts)
    hero = f'''<section class="hero"><p class="eyebrow">LEEWAY’S FIELD NOTES / TECH & IDEAS</p><h1>每天一点新知。<br><em>每周一次回望。</em></h1><p class="intro">把值得关注的开源项目、开发者话题与安全动态，<br>收进一份持续生长的技术手记。</p><a class="button" href="daily/{latest['date']}.html">阅读最新一期 <span>↗</span></a><p class="meta">最近更新 {latest['date']} · {len(posts)} 份早报已归档</p></section>'''
    library = f'<a class="library-banner" href="explore.html"><div><span class="eyebrow">EXPLORE YOUR ARCHIVE</span><h2>{len(catalog)} 条资讯，一个随时可查的技术库。</h2><p>搜索关键词 · 按来源筛选 · 收藏以后读</p></div><b>打开资讯库 ↗</b></a>'
    discovery_cards = ''.join(f'<a href="explore.html?fresh=1&amp;source={kind}"><strong>{discoveries[kind]}</strong><span>{label}</span></a>' for kind, label in [('repos', '开源项目'), ('stories', '开发者热议'), ('advisories', '安全公告')])
    discovery_panel = f'<section class="discovery-summary" aria-label="最新一期新增发现"><div><p class="eyebrow">{latest["date"]} / NEW IN THE ARCHIVE</p><h2>这一期，有 {discoveries["total"]} 条新发现。</h2><p>本站首次收录，点选分类查看未曾出现的内容。</p></div><div class="discovery-counts">{discovery_cards}</div></section>'
    body = hero + library + discovery_panel + '<section><div class="section-title"><h2>每周回顾</h2><span>THE BIGGER PICTURE</span></div><div class="grid">' + ''.join(weekly_cards) + '</div></section><section><div class="section-title"><h2>每日雷达</h2><span>STAY CURIOUS</span></div><div class="grid">' + daily_cards + '</div></section>'
    (out / 'index.html').write_text(page('技术早报与每周回顾', body, '.', url + '/'), encoding='utf-8')
    widget = f'<a class="card weekly" target="_top" href="{latest["url"]}"><span>LEEWAY / TECH RADAR</span><h2>技术雷达 · {latest["date"]}</h2><p>今天值得关注的开源项目、开发者热议与安全动态。</p><b>阅读最新一期 ↗</b></a>'
    (out / 'embed.html').write_text(page('最新技术早报', widget, '.', url + '/embed.html', True), encoding='utf-8')
    public = [{k: v for k, v in p.items() if k != 'markdown'} for p in posts]
    (out / 'latest.json').write_text(json.dumps({'latest': public[0], 'posts': public[:30], 'site_url': url, 'explore_url': url + '/explore.html', 'catalog_url': url + '/search-index.json', 'entry_count': len(catalog), 'latest_discoveries': discoveries}, ensure_ascii=False, indent=2), encoding='utf-8')
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'leeway 技术雷达'), ('link', url + '/'), ('description', '每日技术早报与每周回顾')]:
        ET.SubElement(channel, key).text = value
    for p in posts[:30]:
        item = ET.SubElement(channel, 'item')
        for key, value in [('title', p['title']), ('link', p['url']), ('guid', p['url']), ('description', render(p['markdown'])), ('pubDate', format_datetime(dt.datetime.fromisoformat(p['date']).replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))) )]:
            ET.SubElement(item, key).text = value
    ET.ElementTree(rss).write(out / 'feed.xml', encoding='utf-8', xml_declaration=True)
    (out / '.nojekyll').touch()
    print(f'Built {len(posts)} daily posts and {len(weeks)} weekly digests into {out}')

if __name__ == '__main__':
    build()
