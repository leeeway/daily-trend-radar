# 接入 lwblog.cn（Astro）

根据 common 会话，现有主站源码位于 `/Users/leeway/project/common/leeway-apple-src`，中英文共用 `src/components/ParallaxPortfolio.astro`。本仓库不直接改动主站或服务器配置。

## 1. 导航增加入口

在该组件的 `.nav-links` 内，原有导航循环后加入：

```astro
<a href="https://leeeway.github.io/daily-trend-radar/" target="_blank" rel="noopener noreferrer">
  {zh ? '技术周报 ↗' : 'Tech Radar ↗'}
</a>
```

手机端注意原有导航隐藏规则，可在作品区再放一个同样的入口。

## 2. 首页显示自动更新卡片（推荐）

放在作品区与“此刻”区之间。卡片独立加载，每天更新无需重新构建主站：

```astro
<section class="wrap" aria-label={zh ? '技术周报' : 'Tech Radar'}>
  <iframe
    src="https://leeeway.github.io/daily-trend-radar/embed.html"
    title={zh ? '最新技术早报' : 'Latest tech brief'}
    loading="lazy"
    style="width:100%;height:300px;border:0;border-radius:18px;"
  ></iframe>
  <a href="https://leeeway.github.io/daily-trend-radar/">{zh ? '查看全部日报与周报 ↗' : 'All tech briefs ↗'}</a>
</section>
```

iframe 内返回主站／查看全文会跳到顶层页面。若主站启用了 CSP，允许 frame-src 中的 `https://leeeway.github.io`。

## 3. 原生 Astro 卡片（构建时获取）

```astro
---
let latest = null;
try {
  const response = await fetch('https://leeeway.github.io/daily-trend-radar/latest.json', {
    signal: AbortSignal.timeout(5000),
  });
  if (response.ok) latest = (await response.json()).latest;
} catch { /* 站点不可达时保留兜底入口 */ }
---
<a href={latest?.url ?? 'https://leeeway.github.io/daily-trend-radar/'}>
  {latest?.title ?? '阅读技术日报与周报'} ↗
</a>
```

静态 Astro 只在构建时读取 JSON，需要每日重新构建主站才会刷新；因此当前主站优先使用 iframe。RSS 阅读器也可订阅 `https://leeeway.github.io/daily-trend-radar/feed.xml`。

后续若想用 `radar.lwblog.cn`，可单独给该子域名配置 GitHub Pages，再修改本仓库 `SITE_URL` 和主站入口；不需要更改 `lwblog.cn` 根域名或服务器上的代理配置。此处仅提供接入方案，未更改线上主站。
