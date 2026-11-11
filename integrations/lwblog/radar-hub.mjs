export const radarBase = 'https://leeeway.github.io/daily-trend-radar';
export const hubLinks = Object.freeze({
  home: radarBase + '/',
  discoveries: radarBase + '/explore.html?fresh=1',
  growth: radarBase + '/explore.html?sort=growth',
  reading: radarBase + '/explore.html?unread=1',
  saved: radarBase + '/explore.html?saved=1&unread=1',
  rss: radarBase + '/feed.xml',
});

function calendarDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Invalid radar date');
  const date = new Date(value + 'T00:00:00Z');
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0,10) !== value) throw new Error('Invalid calendar date');
  return date;
}
export function weeklyUrl(value) {
  const date = calendarDate(value);
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const year = date.getUTCFullYear();
  const week = Math.ceil(((date.getTime() - Date.UTC(year,0,1)) / 86400000 + 1) / 7);
  return `${radarBase}/weekly/${year}-W${String(week).padStart(2,'0')}.html`;
}
const count = value => Number.isSafeInteger(value) && value >= 0 && value <= 10000000;
export function parseLatest(data) {
  const latest = data?.latest;
  calendarDate(latest?.date);
  const daily = `${radarBase}/daily/${latest.date}.html`;
  if (latest.url !== daily) throw new Error('Unexpected radar URL');
  const stats = data.latest_discoveries;
  const validStats = stats && stats.date === latest.date &&
    ['repos','stories','advisories','total'].every(key => count(stats[key])) &&
    stats.total === stats.repos + stats.stories + stats.advisories;
  return {date:latest.date, daily, weekly:weeklyUrl(latest.date),
    entryCount:count(data.entry_count) ? data.entry_count : null,
    discoveries:validStats ? {total:stats.total, repos:stats.repos, stories:stats.stories, advisories:stats.advisories} : null};
}

export async function refreshHub(root, fetcher = fetch) {
  const zh = root.dataset.radarLang !== 'en';
  const text = (selector, value) => {
    const node = root.querySelector(selector);
    if (node) node.textContent = value;
  };
  try {
    const response = await fetcher(`${radarBase}/latest.json`, {
      signal:AbortSignal.timeout(8000), credentials:'omit', referrerPolicy:'no-referrer',
    });
    if (!response.ok) throw new Error('Radar feed unavailable');
    const latest = parseLatest(await response.json());
    root.querySelectorAll('[data-radar-latest], [data-radar-read]').forEach(link => {link.href = latest.daily;});
    root.querySelector('[data-radar-weekly]')?.setAttribute('href', latest.weekly);
    text('[data-radar-date]', latest.date);
    text('[data-radar-latest]', zh ? `${latest.date} 技术早报` : `Tech brief · ${latest.date}`);
    text('[data-radar-status]', zh ? '最近归档' : 'LATEST ARCHIVE');
    text('[data-radar-note]', zh ? '随技术雷达自动更新 · 内容为资讯汇编' : 'Synced with Tech Radar · Automatically compiled');
    if (latest.discoveries) {
      const {total, repos, stories, advisories} = latest.discoveries;
      text('[data-radar-new-count]', zh ? `${total} 条新发现` : `${total} new discoveries`);
      text('[data-radar-new-detail]', zh ? `开源 ${repos} · 热议 ${stories} · 安全 ${advisories}` : `${repos} open source · ${stories} discussions · ${advisories} advisories`);
      text('[data-radar-new-period]', zh ? `${latest.date} · 本站首次收录` : `${latest.date} · First seen in this archive`);
    }
    if (latest.entryCount !== null) text('[data-radar-library-count]', zh ? `在 ${latest.entryCount.toLocaleString('zh-CN')} 条资讯中继续阅读` : `Continue across ${latest.entryCount.toLocaleString('en-US')} archived entries`);
    root.dataset.radarState = latest.discoveries ? 'ready' : 'partial';
  } catch {
    text('[data-radar-note]', zh ? '暂未获取最新统计，日报、增长榜与阅读入口仍可直接打开。' : 'Latest stats unavailable. All reading and discovery links remain available.');
    root.dataset.radarState = 'fallback';
  }
}
