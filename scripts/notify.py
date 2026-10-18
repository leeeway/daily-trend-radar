#!/usr/bin/env python3
"""Optional, independent delivery adapters. Never log webhook URLs or API responses."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request


def signed_dingtalk(url, secret, timestamp):
    if not secret:
        return url
    sign = base64.b64encode(hmac.new(secret.encode(), f'{timestamp}\n{secret}'.encode(), hashlib.sha256).digest()).decode()
    return url + ('&' if '?' in url else '?') + urllib.parse.urlencode({'timestamp': timestamp, 'sign': sign})


def deliveries(digest, env):
    title, text = digest['title'], digest['text']
    jobs = []
    if env.get('WECHAT_WEBHOOK'):
        jobs.append(('企业微信', env['WECHAT_WEBHOOK'], {'msgtype':'markdown', 'markdown':{'content':text}}))
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


def send(digest, env=None):
    jobs = deliveries(digest, os.environ if env is None else env)
    failures = []
    for name, url, payload in jobs:
        try:
            if not url.startswith('https://'):
                raise ValueError('HTTPS required')
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode())
            if (name == 'Telegram' and result.get('ok') is not True) or any(result.get(k, 0) != 0 for k in ('errcode','code','StatusCode')):
                raise ValueError('Provider rejected message')
            print(f'[+] {name}: delivered')
        except Exception:
            # Exceptions can contain access_token or bot token. Do not print them.
            failures.append(name)
            print(f'[Warning] {name}: delivery failed; check secret, signature and bot settings')
    if not jobs:
        print('[*] No notification channels configured; skipped')
    return failures

if __name__ == '__main__':
    failures = send(json.loads(Path('notification.json').read_text(encoding='utf-8')))
    raise SystemExit(1 if failures else 0)
