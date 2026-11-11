/* No third-party scripts or tracking. Source text is always rendered with textContent. */
(() => {
  'use strict';
  const form = document.querySelector('#explore-form');
  const results = document.querySelector('#results');
  const status = document.querySelector('#result-count');
  const more = document.querySelector('#load-more');
  const retry = document.querySelector('#retry-load');
  const interestForm = document.querySelector('#interest-form');
  const interestStatus = document.querySelector('#interest-status');
  const interestInclude = document.querySelector('#interest-include');
  const interestExclude = document.querySelector('#interest-exclude');
  // A cached older page can briefly arrive with newer assets during publication.
  if (!interestForm || typeof globalThis.RadarExplore?.parseInterests !== 'function') {
    status.textContent = '工作台已更新，请刷新页面加载最新版本。';
    retry.hidden = false;
    retry.addEventListener('click', () => location.reload());
    return;
  }
  const fields = {q: form.elements.q, source: form.elements.source, from: form.elements.from,
    to: form.elements.to, sort: form.elements.sort, saved: form.elements.saved,
    unread: form.elements.unread, fresh: form.elements.fresh, following: form.elements.following};
  const checkboxKeys = new Set(['saved', 'unread', 'fresh', 'following']);
  const scope = new URL('.', location.href).pathname;
  const legacyKey = 'radar:bookmarks:v1:' + scope;
  const storageKey = 'radar:reading:v1:' + scope;
  let saved = new Set(), read = new Set(), entries = [], limit = 24, loaded = false, latestDate = '';
  let interests = RadarExplore.parseInterests();
  function storageUnavailable() {
    document.querySelector('#storage-note').textContent = '浏览器记录不可用，修改仅在本页打开期间保留；可使用备份保存。';
  }
  function readingState() {
    return {type: RadarExplore.readingType, version: 1, bookmarks: [...saved], read: [...read], interests};
  }
  function persistReading() {
    try { localStorage.setItem(storageKey, JSON.stringify(readingState())); }
    catch { storageUnavailable(); }
  }
  function loadReading() {
    try {
      const data = RadarExplore.loadReading(localStorage.getItem(storageKey), localStorage.getItem(legacyKey));
      saved = new Set(data.bookmarks);
      read = new Set(data.read);
      interests = data.interests;
    } catch { storageUnavailable(); }
  }
  function showInterests() {
    interestInclude.value = interests.include.join(', ');
    interestExclude.value = interests.exclude.join(', ');
  }
  function readURL() {
    const query = new URLSearchParams(location.search);
    for (const [key, field] of Object.entries(fields)) {
      if (checkboxKeys.has(key)) field.checked = query.get(key) === '1';
      else field.value = query.get(key) || (key === 'sort' ? 'newest' : '');
    }
  }
  function filters() {
    return Object.fromEntries(Object.entries(fields).map(([key, field]) =>
      [key, checkboxKeys.has(key) ? field.checked : field.value]));
  }
  function updateURL() {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(filters())) {
      if (value && !(key === 'sort' && value === 'newest')) query.set(key, checkboxKeys.has(key) ? '1' : value);
    }
    const url = new URL(location.href);
    url.search = query.toString();
    history.replaceState(null, '', url);
  }
  function node(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function link(text, url, className) {
    const el = node('a', className, text);
    // Defence in depth for generated JSON and deployments on a different base path.
    try {
      const parsed = new URL(url, location.href);
      if (['https:', 'http:'].includes(parsed.protocol)) {
        el.href = parsed.href;
        el.target = '_blank';
        el.rel = 'noopener noreferrer';
      }
    } catch { /* Invalid source links stay inert. */ }
    return el;
  }
  function signed(value) {
    return (value > 0 ? '+' : '') + value.toLocaleString();
  }
  function starHistory(entry) {
    const section = node('div', 'star-history');
    const history = entry.star_history || [];
    const trend = entry.star_trend || {};
    if (history.length < 2) {
      section.append(node('p', 'trend-note', history.length ? '首次采样，积累后展示增长趋势。' : '暂无 Star 采样。'));
      return section;
    }
    if (Number.isFinite(trend.previous_delta)) {
      section.append(node('p', 'trend-change ' + (trend.previous_delta < 0 ? 'trend-down' : ''),
        `较上次采样 ${signed(trend.previous_delta)} Star · 间隔 ${trend.previous_days} 天`));
    }
    if (Number.isFinite(trend.week_delta)) {
      section.append(node('p', 'trend-note', `7 日变化 ${signed(trend.week_delta)} · ${trend.week_start} → ${history.at(-1).date}`));
    }
    const points = RadarExplore.chartPoints(history);
    if (points.length) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 300 60');
      svg.setAttribute('class', 'sparkline');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', `${history[0].date} 至 ${history.at(-1).date} 的 Star 采样趋势，具体数据见下方表格`);
      const line = document.createElementNS(svg.namespaceURI, 'polyline');
      line.setAttribute('points', points.map(point => `${point.x},${point.y}`).join(' '));
      svg.append(line);
      section.append(svg, node('p', 'trend-range', `${history[0].date} / ${history[0].stars.toLocaleString()} ★ → ${history.at(-1).date} / ${history.at(-1).stars.toLocaleString()} ★`));
    }
    const details = node('details', 'trend-details');
    details.append(node('summary', '', `查看 ${history.length} 次 Star 采样`));
    const table = node('table');
    const head = node('tr');
    for (const label of ['收录日期', 'Star', '较上次采样']) head.append(node('th', '', label));
    const thead = node('thead');
    thead.append(head);
    const tbody = node('tbody');
    history.forEach((sample, index) => {
      const row = node('tr');
      const previous = history[index - 1];
      const days = previous ? Math.round((Date.parse(sample.date) - Date.parse(previous.date)) / 86400000) : 0;
      for (const value of [sample.date, sample.stars.toLocaleString(), previous ? `${signed(sample.stars - previous.stars)} / ${days} 天` : '首次采样']) row.append(node('td', '', value));
      tbody.append(row);
    });
    table.append(thead, tbody);
    details.append(table);
    section.append(details);
    return section;
  }
  function card(entry) {
    const el = node('article', 'result-card');
    if (read.has(entry.id)) el.classList.add('is-read');
    const top = node('div', 'result-top');
    const badges = node('div', 'entry-badges');
    badges.append(node('span', 'source-tag source-' + entry.kind,
      {repos: '开源项目', stories: '开发者热议', advisories: '安全公告'}[entry.kind]));
    if (entry.first_seen === latestDate) badges.append(node('span', 'source-tag new-tag', '本期首次收录'));
    top.append(badges);
    const bookmark = node('button', 'bookmark', saved.has(entry.id) ? '已收藏' : '＋ 收藏');
    bookmark.type = 'button';
    bookmark.setAttribute('aria-pressed', String(saved.has(entry.id)));
    bookmark.setAttribute('aria-label', (saved.has(entry.id) ? '取消收藏：' : '收藏：') + entry.title);
    bookmark.addEventListener('click', () => {
      if (saved.has(entry.id)) saved.delete(entry.id); else saved.add(entry.id);
      persistReading();
      // Preserve focus after replacing the result list.
      const position = [...results.children].indexOf(el);
      render();
      const button = results.children[Math.min(position, results.children.length - 1)]?.querySelector('.bookmark');
      (button || fields.saved).focus();
    });
    top.append(bookmark);
    const title = node('h2');
    title.append(link(entry.title, entry.url));
    el.append(top, title);
    if (entry.description) el.append(node('p', 'result-description', entry.description));
    const match = RadarExplore.interestMatch(entry, interests);
    if (match.excluded.length) el.append(node('p', 'interest-match interest-excluded', '排除词命中：' + match.excluded.join(' · ')));
    else if (match.included.length) el.append(node('p', 'interest-match', '关注命中：' + match.included.join(' · ')));
    const metrics = [];
    if (entry.language) metrics.push(entry.language);
    if (Number.isFinite(entry.stars)) metrics.push('★ ' + entry.stars.toLocaleString());
    if (Number.isFinite(entry.score)) metrics.push(entry.score + ' points');
    if (Number.isFinite(entry.comments)) metrics.push(entry.comments + ' 条评论');
    if (entry.cve && entry.cve !== 'N/A') metrics.push(entry.cve);
    el.append(node('p', 'result-metrics', metrics.join(' · ')));
    if (entry.kind === 'repos') el.append(starHistory(entry));
    const bottom = node('div', 'result-bottom');
    bottom.append(link('收录于 ' + entry.last_seen + ' ↗', entry.daily_url));
    if (entry.dates.length > 1) bottom.append(node('span', '', '共收录 ' + entry.dates.length + ' 天'));
    if (entry.discuss_url) bottom.append(link('查看讨论 ↗', entry.discuss_url));
    const readButton = node('button', 'read-toggle', read.has(entry.id) ? '已读 · 标为未读' : '标记已读');
    readButton.type = 'button';
    readButton.setAttribute('aria-pressed', String(read.has(entry.id)));
    readButton.setAttribute('aria-label', (read.has(entry.id) ? '标为未读：' : '标记已读：') + entry.title);
    readButton.addEventListener('click', () => {
      if (read.has(entry.id)) read.delete(entry.id); else read.add(entry.id);
      persistReading();
      const position = [...results.children].indexOf(el);
      render();
      const button = results.children[Math.min(position, results.children.length - 1)]?.querySelector('.read-toggle');
      (button || fields.unread).focus();
    });
    bottom.append(readButton);
    el.append(bottom);
    return el;
  }
  function render() {
    document.querySelector('#saved-count').textContent = String(saved.size);
    const configured = interests.include.length + interests.exclude.length > 0;
    interestStatus.textContent = configured ? `关注 ${interests.include.length} 个词 · 排除 ${interests.exclude.length} 个词` :
      '尚未设置关注主题。展开“我的关注主题”，保存后即可筛选。';
    if (fields.following.checked && !configured) document.querySelector('#interest-panel').open = true;
    if (!loaded) return;
    if (configured) {
      const hits = entries.filter(entry => RadarExplore.interestMatch(entry, interests).matches);
      interestStatus.textContent += ` · 全库匹配 ${hits.length} 条，其中未读 ${hits.filter(entry => !read.has(entry.id)).length} 条`;
    }
    const current = filters();
    fields.to.min = current.from;
    fields.from.max = current.to;
    const matches = RadarExplore.select(entries, {...current, asOf: latestDate}, saved, read, interests);
    results.replaceChildren(...matches.slice(0, limit).map(card));
    status.textContent = `找到 ${matches.length} 条资讯 · 已展示 ${Math.min(limit, matches.length)} 条`;
    if (!matches.length) {
      results.append(node('p', 'empty-state', current.following ? (configured ?
        '没有同时符合关注主题与当前筛选的内容，可调整关注词、排除词或放宽其他条件。' :
        '请先在“我的关注主题”中保存关键词。关闭“只看关注”可继续浏览全部资讯。') : current.unread ?
        '当前筛选下没有未读内容。可取消“只看未读”，或查看最新一期首次收录。' : current.saved ?
        '还没有符合条件的收藏。取消“只看收藏”，选择内容卡片上的收藏按钮。' :
        current.sort === 'growth' ? '没有符合条件的项目。7 日增长排序需要最新一期、且具备相隔 7 天采样的开源项目。' :
        '没有找到匹配内容，试试减少关键词或放宽日期范围。'));
    }
    more.hidden = matches.length <= limit;
  }
  async function load() {
    retry.hidden = true;
    try {
      const response = await fetch('./search-index.json');
      if (!response.ok) throw new Error('index unavailable');
      const data = await response.json();
      if (data.version !== 1 || !Array.isArray(data.entries)) throw new Error('invalid index');
      entries = data.entries;
      latestDate = data.latest_date;
      loaded = true;
      render();
    } catch {
      status.replaceChildren(node('span', '', '资讯库暂时未能加载。请重试，或先'), link('浏览日报与周报', './'));
      retry.hidden = false;
    }
  }
  form.addEventListener('submit', event => event.preventDefault());
  interestForm.addEventListener('submit', event => {
    event.preventDefault();
    try {
      const next = RadarExplore.parseInterests({include: interestInclude.value, exclude: interestExclude.value});
      loadReading();
      interests = next;
      persistReading();
      showInterests();
      fields.following.checked = interests.include.length + interests.exclude.length > 0;
      limit = 24;
      updateURL();
      render();
    } catch (error) { interestStatus.textContent = error.message + '，未更改已有设置。'; }
  });
  form.addEventListener('input', () => { limit = 24; updateURL(); render(); });
  form.addEventListener('reset', event => {
    event.preventDefault();
    for (const [key, field] of Object.entries(fields)) {
      if (checkboxKeys.has(key)) field.checked = false;
      else field.value = key === 'sort' ? 'newest' : '';
    }
    limit = 24;
    updateURL();
    render();
  });
  more.addEventListener('click', () => { limit += 24; render(); });
  retry.addEventListener('click', load);
  const readingStatus = document.querySelector('#reading-status');
  const readingFile = document.querySelector('#reading-file');
  document.querySelector('#export-reading').addEventListener('click', () => {
    try {
      const data = RadarExplore.parseBackup(JSON.stringify(readingState()));
      const blob = new Blob([JSON.stringify({...data, created_at: new Date().toISOString()}, null, 2)], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const download = document.createElement('a');
      download.href = url;
      download.download = 'radar-reading-' + new Date().toISOString().slice(0, 10) + '.json';
      document.body.append(download);
      download.click();
      download.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      readingStatus.textContent = `已生成备份：${saved.size} 条收藏、${read.size} 条已读记录，含关注与排除词。`;
    } catch { readingStatus.textContent = '备份生成失败，现有记录未改变。'; }
  });
  document.querySelector('#import-reading').addEventListener('click', () => readingFile.click());
  readingFile.addEventListener('change', async () => {
    const file = readingFile.files[0];
    if (!file) return;
    try {
      if (file.size > 1048576) throw new Error('Backup is too large');
      const backup = RadarExplore.parseBackup(await file.text());
      // Other tabs may have added records while the file chooser was open.
      loadReading();
      const merged = RadarExplore.mergeReading(readingState(), backup);
      saved = new Set(merged.bookmarks);
      read = new Set(merged.read);
      interests = merged.interests;
      persistReading();
      showInterests();
      render();
      readingStatus.textContent = `恢复完成，已合并去重：${saved.size} 条收藏、${read.size} 条已读记录，以及关注与排除词。`;
    } catch { readingStatus.textContent = '导入失败，现有记录未改变。请选择有效备份（最多 1 MB），合并后每类词最多 40 个。'; }
    finally { readingFile.value = ''; }
  });
  window.addEventListener('popstate', () => { readURL(); limit = 24; render(); });
  window.addEventListener('storage', event => {
    if ([storageKey, legacyKey, null].includes(event.key)) {
      loadReading();
      if (!interestForm.contains(document.activeElement)) showInterests();
      render();
    }
  });
  loadReading();
  showInterests();
  readURL();
  load();
})();
