#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Daily Trend Radar - 自动化数据抓取与报告生成器
抓取 GitHub 新兴热门仓库、Hacker News 全球极客热榜以及高危安全漏洞公告，
并自动生成当日归档 Markdown 与更新项目首页 README.md。
"""

import datetime
import json
import os
import urllib.request
import urllib.error
from zoneinfo import ZoneInfo
from pathlib import Path

USER_AGENT = "DailyTrendRadar/1.0 (+https://github.com/leeeway/daily-trend-radar)"

def fetch_json(url, headers=None, timeout=12):
    req_headers = {"User-Agent": USER_AGENT}
    if url.startswith("https://api.github.com/") and os.getenv("GITHUB_TOKEN"):
        req_headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"[Warning] Failed to fetch {url}: {e}")
        return None

def get_github_trending():
    """获取近期高增长与新突破开源项目"""
    two_weeks_ago = (datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date() - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    url = f"https://api.github.com/search/repositories?q=created:>{two_weeks_ago}&sort=stars&order=desc&per_page=8"
    data = fetch_json(url)
    items = []
    if data and "items" in data:
        for repo in data["items"]:
            items.append({
                "name": repo.get("full_name"),
                "url": repo.get("html_url"),
                "description": (repo.get("description") or "暂无项目描述").strip(),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language") or "Other"
            })
    return items

def get_hackernews_top():
    """获取 Hacker News 当日热门探讨 Top 8"""
    top_ids = fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    items = []
    if top_ids:
        for sid in top_ids[:8]:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            detail = fetch_json(item_url, timeout=5)
            if detail and "title" in detail:
                hn_discuss_url = f"https://news.ycombinator.com/item?id={sid}"
                article_url = detail.get("url") or hn_discuss_url
                items.append({
                    "title": detail["title"],
                    "url": article_url,
                    "score": detail.get("score", 0),
                    "comments": detail.get("descendants", 0),
                    "discuss_url": hn_discuss_url
                })
    return items

def get_security_advisories():
    """获取最新的 GitHub 高危与严重安全漏洞公告"""
    data = fetch_json("https://api.github.com/advisories?per_page=6&severity=critical")
    items = []
    if data and isinstance(data, list):
        for adv in data:
            items.append({
                "ghsa_id": adv.get("ghsa_id"),
                "cve_id": adv.get("cve_id") or "N/A",
                "summary": adv.get("summary") or "Security update",
                "severity": (adv.get("severity") or "unknown").upper(),
                "url": adv.get("html_url")
            })
    return items

def generate_markdown(today_str, repos, hn_items, advisories):
    md = []
    md.append(f"# 📡 Daily Trend Radar · {today_str}\n")
    md.append(f"> 自动追踪全球开发者趋势、最新爆款开源项目与关键安全威胁情报。\n")
    md.append(f"*生成时间: {today_str} · 数据来源: GitHub API & HackerNews*\n")
    md.append("---\n")

    # 1. GitHub Trending
    md.append("## 🔥 GitHub 近期新晋热门开源项目 (Breakout Repos)")
    if repos:
        md.append("| 项目名 | 语言 | ⭐ Stars | 🍴 Forks | 简介 |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for r in repos:
            clean_desc = r['description'].replace("|", "-").replace("\n", " ")
            if len(clean_desc) > 90:
                clean_desc = clean_desc[:87] + "..."
            md.append(f"| [{r['name']}]({r['url']}) | `{r['language']}` | **{r['stars']}** | {r['forks']} | {clean_desc} |")
    else:
        md.append("- 暂未获取到开源趋势数据。\n")
    md.append("\n---\n")

    # 2. Hacker News
    md.append("## 🌐 Hacker News 全球极客前沿热议")
    if hn_items:
        for idx, item in enumerate(hn_items, 1):
            md.append(f"{idx}. **[{item['title']}]({item['url']})**  ")
            md.append(f"   👍 {item['score']} points · 💬 [{item['comments']} 条讨论]({item['discuss_url']})")
    else:
        md.append("- 暂未获取到热议内容。\n")
    md.append("\n---\n")

    # 3. Security Advisories
    md.append("## 🛡️ 最新高危与严重漏洞告警 (Security Advisories)")
    if advisories:
        md.append("| 漏洞编号 | 严重等级 | 关联 CVE | 简要描述 |")
        md.append("| :--- | :--- | :--- | :--- |")
        for adv in advisories:
            sev_badge = "🔴 CRITICAL" if adv['severity'] == "CRITICAL" else "🟠 HIGH"
            summary = adv['summary'].replace("|", "-")
            md.append(f"| [{adv['ghsa_id']}]({adv['url']}) | {sev_badge} | `{adv['cve_id']}` | {summary} |")
    else:
        md.append("- 未获取到严重漏洞公告；可能是数据源不可用，请查看运行日志。\n")
    md.append("\n---\n")
    md.append("*本简报由 GitHub Actions 自动化定时生成并归档。*")

    return "\n".join(md)

def update_readme(today_str, archive_rel_path, archive_content):
    # 读取已有归档列表
    archives_dir = "archives"
    recent_archives = []
    if os.path.exists(archives_dir):
        files = sorted(os.listdir(archives_dir), reverse=True)
        for f in files:
            if f.endswith(".md"):
                date_part = f[:-3]
                recent_archives.append(f"- 📅 [{date_part} 技术雷达](archives/{f})")

    recent_list_str = "\n".join(recent_archives[:10]) if recent_archives else "- 暂无历史归档"

    readme_path = Path("README.md")
    existing = readme_path.read_text(encoding="utf-8")
    start, end = "<!-- radar:start -->", "<!-- radar:end -->"
    block = f"{start}\n\n最新日报：[{today_str}]({archive_rel_path})\n\n{recent_list_str}\n\n{end}"
    if start in existing and end in existing:
        before, rest = existing.split(start, 1)
        _, after = rest.split(end, 1)
        readme_path.write_text(before + block + after, encoding="utf-8")


def main():
    today_str = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date().strftime("%Y-%m-%d")
    print(f"[*] Starting Daily Trend Radar fetch for {today_str}...")

    archive_path = f"archives/{today_str}.md"
    force = os.getenv("FORCE_REFRESH", "").lower() in ("1", "true", "yes")
    is_schedule = os.getenv("GITHUB_EVENT_NAME") == "schedule"
    if is_schedule and not force and os.path.exists(archive_path):
        print(f"[*] Archive {archive_path} already exists for today. Skipping duplicate scheduled run.")
        return

    repos = get_github_trending()
    hn_items = get_hackernews_top()
    advisories = get_security_advisories()

    if not repos and not hn_items and not advisories:
        raise RuntimeError("All sources failed or returned no data; preserving existing archives")

    total_items = len(repos) + len(hn_items) + len(advisories)
    print(f"[*] Fetched {len(repos)} breakout repos, {len(hn_items)} HN stories, {len(advisories)} advisories.")

    os.makedirs("archives", exist_ok=True)
    archive_path = f"archives/{today_str}.md"

    md_content = generate_markdown(today_str, repos, hn_items, advisories)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    update_readme(today_str, archive_path, md_content)

    # 输出用于 Git Commit 的说明
    with open("commit_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"docs(radar): sync tech digest [{today_str}] ({total_items} updates)")

    site_url = os.getenv("SITE_URL", "https://leeeway.github.io/daily-trend-radar").rstrip("/")
    # Keep the message below provider size limits: three short picks and a reading link.
    picks = [f"技术雷达 · {today_str}"]
    if repos:
        picks.append("开源精选：" + repos[0]['name'][:100])
        picks.append(repos[0]['description'][:120])
    if hn_items:
        picks.append("今日热议：" + hn_items[0]['title'][:120])
    if advisories:
        picks.append("安全关注：" + advisories[0]['ghsa_id'] + " " + advisories[0]['summary'][:100])
    picks.append(f"阅读全文：{site_url}/daily/{today_str}.html")
    notification = {
        "title": picks[0],
        "text": "\n\n".join(picks),
        "brief": {
            "date": today_str,
            "url": f"{site_url}/daily/{today_str}.html",
            "repos": repos[:2],
            "stories": hn_items[:2],
            "advisories": advisories[:1],
            "counts": [len(repos), len(hn_items), len(advisories)],
        },
    }
    Path("notification.json").write_text(
        json.dumps(notification, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[+] Successfully generated {archive_path} and updated README.md")

if __name__ == "__main__":
    main()
