/* No third-party scripts or tracking. Source text is always rendered with textContent. */
(() => {
  'use strict';
  const form = document.querySelector('#explore-form');
  const results = document.querySelector('#results');
  const status = document.querySelector('#result-count');
  const more = document.querySelector('#load-more');
  const retry = document.querySelector('#retry-load');
  const fields = {q: form.elements.q, source: form.elements.source, from: form.elements.from,
    to: form.elements.to, sort: form.elements.sort, saved: form.elements.saved};
  const storageKey = 'radar:bookmarks:v1:' + new URL('.', location.href).pathname;
  let saved = new Set(), entries = [], limit = 24, loaded = false;
  function storageUnavailable() {
    document.querySelector('#storage-note').textContent = '浏览器存储不可用，收藏仅在本页打开期间保留。';
  }
  function loadSaved() {
    try {
      const data = JSON.parse(localStorage.getItem(storageKey) || '[]');
      saved = new Set(Array.isArray(data) ? data.filter(id => typeof id === 'string') : []);
    } catch { storageUnavailable(); }
  }
  function readURL() {
    const query = new URLSearchParams(location.search);
    for (const [key, field] of Object.entries(fields)) {
      if (key === 'saved') field.checked = query.get(key) === '1';
      else field.value = query.get(key) || (key === 'sort' ? 'newest' : '');
    }
  }
  function filters() {
    return Object.fromEntries(Object.entries(fields).map(([key, field]) =>
      [key, key === 'saved' ? field.checked : field.value]));
  }
  function updateURL() {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(filters())) {
      if (value && !(key === 'sort' && value === 'newest')) query.set(key, key === 'saved' ? '1' : value);
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
  function card(entry) {
    const el = node('article', 'result-card');
    const top = node('div', 'result-top');
    top.append(node('span', 'source-tag source-' + entry.kind,
      {repos: '开源项目', stories: '开发者热议', advisories: '安全公告'}[entry.kind]));
    const bookmark = node('button', 'bookmark', saved.has(entry.id) ? '已收藏' : '＋ 收藏');
    bookmark.type = 'button';
    bookmark.setAttribute('aria-pressed', String(saved.has(entry.id)));
    bookmark.setAttribute('aria-label', (saved.has(entry.id) ? '取消收藏：' : '收藏：') + entry.title);
    bookmark.addEventListener('click', () => {
      if (saved.has(entry.id)) saved.delete(entry.id); else saved.add(entry.id);
      try { localStorage.setItem(storageKey, JSON.stringify([...saved])); } catch { storageUnavailable(); }
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
    const metrics = [];
    if (entry.language) metrics.push(entry.language);
    if (Number.isFinite(entry.stars)) metrics.push('★ ' + entry.stars.toLocaleString());
    if (Number.isFinite(entry.score)) metrics.push(entry.score + ' points');
    if (Number.isFinite(entry.comments)) metrics.push(entry.comments + ' 条评论');
    if (entry.cve && entry.cve !== 'N/A') metrics.push(entry.cve);
    el.append(node('p', 'result-metrics', metrics.join(' · ')));
    const bottom = node('div', 'result-bottom');
    bottom.append(link('收录于 ' + entry.last_seen + ' ↗', entry.daily_url));
    if (entry.dates.length > 1) bottom.append(node('span', '', '共收录 ' + entry.dates.length + ' 天'));
    if (entry.discuss_url) bottom.append(link('查看讨论 ↗', entry.discuss_url));
    el.append(bottom);
    return el;
  }
  function render() {
    document.querySelector('#saved-count').textContent = String(saved.size);
    if (!loaded) return;
    const current = filters();
    fields.to.min = current.from;
    fields.from.max = current.to;
    const matches = RadarExplore.select(entries, current, saved);
    results.replaceChildren(...matches.slice(0, limit).map(card));
    status.textContent = `找到 ${matches.length} 条资讯 · 已展示 ${Math.min(limit, matches.length)} 条`;
    if (!matches.length) {
      results.append(node('p', 'empty-state', current.saved ?
        '还没有符合条件的收藏。取消“只看收藏”，选择内容卡片上的收藏按钮。' :
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
      loaded = true;
      render();
    } catch {
      status.replaceChildren(node('span', '', '资讯库暂时未能加载。请重试，或先'), link('浏览日报与周报', './'));
      retry.hidden = false;
    }
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', () => { limit = 24; updateURL(); render(); });
  form.addEventListener('reset', event => {
    event.preventDefault();
    for (const [key, field] of Object.entries(fields)) {
      if (key === 'saved') field.checked = false;
      else field.value = key === 'sort' ? 'newest' : '';
    }
    limit = 24;
    updateURL();
    render();
  });
  more.addEventListener('click', () => { limit += 24; render(); });
  retry.addEventListener('click', load);
  window.addEventListener('popstate', () => { readURL(); limit = 24; render(); });
  window.addEventListener('storage', event => { if (event.key === storageKey || event.key === null) { loadSaved(); render(); } });
  loadSaved();
  readURL();
  load();
})();
