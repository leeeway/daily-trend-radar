#!/usr/bin/env python3
"""Optional, independent delivery adapters. Never log webhook URLs or API responses."""
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import html
from pathlib import Path
import time
import urllib.parse
import urllib.request


def signed_dingtalk(url, secret, timestamp):
    if not secret:
        return url
    sign = base64.b64encode(hmac.new(secret.encode(), f'{timestamp}\n{secret}'.encode(), hashlib.sha256).digest()).decode()
    return url + ('&' if '?' in url else '?') + urllib.parse.urlencode({'timestamp': timestamp, 'sign': sign})


def excerpt(value, limit):
    """Prefer a complete first sentence; never leave half an English word."""
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(text) <= limit:
        return text
    sentence = re.match(r'.+?[。！？](?:\s|$)|.+?[.!?](?:\s|$)', text)
    if sentence and len(sentence[0]) <= limit:
        return sentence[0].strip()
    part = text[:limit - 1]
    if re.search(r'[A-Za-z0-9]$', part) and re.match(r'[A-Za-z0-9]', text[limit - 1:]):
        part = re.sub(r'[A-Za-z0-9_-]+$', '', part)
    return part.rstrip(' ,;:，；：') + '…'


def label(value, limit):
    # Provider markdown accepts a subset of HTML; escape source text and syntax.
    text = excerpt(value, limit)
    for char in ('*', '[', ']', '`', '_'):
        text = text.replace(char, {'*':'＊', '[':'［', ']':'］', '`':'′', '_':'＿'}[char])
    return html.escape(text, quote=False)


def safe_link(title, url):
    parsed = urllib.parse.urlsplit(str(url or ''))
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return title
    url = urllib.parse.quote(str(url), safe=":/?&=%#@+;,-._~")
    return f'[{title}]({url})'


def wechat_markdown(digest):
    brief = digest.get('brief')
    if not brief:  # Allow artifacts generated before the structured brief format.
        return digest['text']
    counts = brief['counts']
    lines = [f"## ☀️ 技术雷达 · {label(brief['date'], 10)}",
             f"> 今日收录：{counts[0]} 个开源项目 · {counts[1]} 条热议 · {counts[2]} 条严重漏洞公告"]
    # Bound both individual fields and the final UTF-8 payload. Long URLs are
    # omitted from selections rather than truncating a link or markdown syntax.
    sections = []
    for index, repo in enumerate(brief.get('repos', [])[:2], 1):
        name = safe_link(label(repo.get('name'), 65), repo.get('url'))
        sections.append(('### 🧩 开源发现' if index == 1 else '', [
            f"**{index}. {name}**",
            f"{label(repo.get('language', 'Other'), 20)} · ★ {repo.get('stars', 0):,} · Forks {repo.get('forks', 0):,}",
            f"> {label(repo.get('description'), 170)}"]))
    for index, story in enumerate(brief.get('stories', [])[:2], 1):
        title = safe_link(label(story.get('title'), 130), story.get('url'))
        discussion = safe_link('查看讨论', story.get('discuss_url'))
        sections.append(('### 💬 开发者在聊' if index == 1 else '', [
            f"**{index}. {title}**",
            f"{story.get('score', 0):,} 热度积分 · {story.get('comments', 0):,} 条评论 · {discussion}"]))
    for advisory in brief.get('advisories', [])[:1]:
        ident = advisory.get('cve_id')
        if not ident or ident == 'N/A':
            ident = advisory.get('ghsa_id')
        sections.append(('### 🛡 安全提醒', [
            f"**严重 / {label(ident, 40)}**",
            f"> {label(advisory.get('summary'), 190)}",
            safe_link('查看受影响版本与修复建议', advisory.get('url'))]))
    footer = '\n\n' + safe_link('📖 阅读完整早报 →', brief.get('url')) + '\n> 来源：GitHub / Hacker News · 描述保留来源原文'
    if len(('\n'.join(lines) + footer).encode('utf-8')) > 4000:
        raise ValueError('Notification footer exceeds WeCom message budget')
    for heading, content in sections:
        block = '\n\n' + (heading + '\n' if heading else '') + '\n'.join(content)
        candidate = '\n'.join(lines) + block + footer
        if len(candidate.encode('utf-8')) <= 4000:
            lines.append(block)
    return '\n'.join(lines) + footer


def deliveries(digest, env):
    title, text = digest['title'], digest['text']
    jobs = []
    if env.get('WECHAT_WEBHOOK'):
        jobs.append(('企业微信', env['WECHAT_WEBHOOK'], {'msgtype':'markdown', 'markdown':{'content':wechat_markdown(digest)}}))
    if env.get('DINGTALK_WEBHOOK'):
        url = signed_dingtalk(env['DINGTALK_WEBHOOK'], env.get('DINGTALK_SECRET'), str(int(time.time() * 1000)))
        jobs.append(('钉钉', url, {'msgtype':'markdown', 'markdown':{'title':title, 'text':text}}))
    if env.get('FEISHU_WEBHOOK'):
        payload = {'msg_type':'text', 'content':{'text':text}}
        if env.get('FEISHU_SECRET'):
            stamp = str(int(time.time()))
            key = f"{stamp}\n{env['FEISHU_SECRET']}".encode()
            payload.update(timestamp=stamp, sign=base64.b64encode(hmac.new(key, b'', hashlib.sha256).digest()).decode())
        jobs.append(('飞书', env['FEISHU_WEBHOOK'], payload))
    if env.get('TELEGRAM_BOT_TOKEN') and env.get('TELEGRAM_CHAT_ID'):
        jobs.append(('Telegram', f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/sendMessage", {'chat_id':env['TELEGRAM_CHAT_ID'], 'text':text, 'link_preview_options':{'is_disabled':True}}))
    if env.get('SERVERCHAN_SENDKEY'):
        jobs.append(('Server酱', f"https://sctapi.ftqq.com/{env['SERVERCHAN_SENDKEY']}.send", {'title':title, 'desp':text}))
    return jobs


def send(digest, env=None, receipt_path=None):
    jobs = deliveries(digest, os.environ if env is None else env)
    failures = []
    receipt_path = Path(receipt_path) if receipt_path else None
    date = digest.get('brief', {}).get('date')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path and receipt_path.exists() else {'date': date, 'delivered': {}}
    if receipt.get('date') != date:
        raise ValueError('Delivery receipt date mismatch')
    for name, url, payload in jobs:
        if name in receipt['delivered']:
            print(f'[*] {name}: already delivered today; skipped')
            continue
        try:
            if not url.startswith('https://'):
                raise ValueError('HTTPS required')
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode())
            if (name == 'Telegram' and result.get('ok') is not True) or any(result.get(k, 0) != 0 for k in ('errcode','code','StatusCode')):
                raise ValueError('Provider rejected message')
            receipt['delivered'][name] = dt.datetime.now(dt.timezone.utc).isoformat()
            if receipt_path:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = receipt_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                temporary.replace(receipt_path)
            print(f'[+] {name}: delivered')
        except Exception:
            # Exceptions can contain access_token or bot token. Do not print them.
            failures.append(name)
            print(f'[Warning] {name}: delivery failed; check secret, signature and bot settings')
    if not jobs:
        print('[*] No notification channels configured; skipped')
    return failures

if __name__ == '__main__':
    digest = json.loads(Path('notification.json').read_text(encoding='utf-8'))
    date = digest['brief']['date']
    failures = send(digest, receipt_path=Path('data/delivery') / f'{date}.json')
    raise SystemExit(1 if failures else 0)
