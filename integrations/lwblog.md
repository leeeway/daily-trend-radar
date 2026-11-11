# lwblog.cn 原生技术雷达

主站源码位于 `/Users/leeway/project/common/leeway-apple-src`，Astro 中英文首页共用 `src/components/ParallaxPortfolio.astro`。本目录的 [TechRadarHub.astro](lwblog/TechRadarHub.astro) 与 [radar-hub.mjs](lwblog/radar-hub.mjs) 是可复用的接入源码。

## 首页功能

| 入口 | 行为 |
| --- | --- |
| 最新日报 / 周报 | 从公开 `latest.json` 获取最近归档日期，计算对应 ISO 周报地址 |
| 新增发现 | 展示本期首次本站收录总数和开源 / 热议 / 安全分类，打开 `explore.html?fresh=1` |
| Star 增长榜 | 打开 `explore.html?sort=growth`，比较最新一期项目真实的七日 Star 变化 |
| 阅读工作台 | 打开 `explore.html?unread=1`，继续浏览未读内容 |
| 收藏待读 | 打开 `explore.html?saved=1&unread=1`，组合收藏与未读筛选 |

增长榜仅纳入具备相隔七天采样的项目，保留零增长和负增长。新增发现指首次进入本站归档，不表示项目当天创建。

阅读入口在雷达站新标签页打开，与现有收藏、已读记录使用同一来源的浏览器存储。记录保存在当前浏览器；跨设备使用资讯库内的 JSON 备份 / 恢复功能，不自动同步到服务器。

## 安装到 Astro

将两个源码文件复制到主站的 `src/components/`。在 `ParallaxPortfolio.astro` 中导入：

```astro
---
import TechRadarHub from './TechRadarHub.astro';
---
<TechRadarHub lang={lang} />
```

使用此组件替换旧 `#radar` 区块，同时移除旧卡片的更新脚本，避免重复 ID 和重复请求。原有导航仍链接 `#radar`。传入 `lang="zh"` 或 `lang="en"`；英文入口对应的日报内容仍为中文。

组件进入视口附近时读取 `https://leeeway.github.io/daily-trend-radar/latest.json`，因此日报更新无需重新构建个人网站。请求最长等待 8 秒；不可达、结构无效或统计缺失时保留可用的静态入口，不展示虚构的零值。日期、每日地址和计数经过校验，动态文字通过 `textContent` 更新。

若主站启用了 CSP，保留 `script-src 'self'`、`style-src 'self' 'unsafe-inline'`，并允许 `connect-src` 中的 `https://leeeway.github.io`。主站已有这些设置，新增模块构建为同源外部脚本，无需添加新的脚本权限或 iframe 权限。

## 验证与发布

```sh
# 本仓库：覆盖筛选、阅读状态及主站 API 解析和异常回退
node --test tests/*.test.cjs
.venv/bin/python -m unittest discover -s tests -v

# 个人网站
cd /Users/leeway/project/common/leeway-apple-src
npm run build
```

主站源码修改前的备份在 `.lwblog-backups/radar-hub-20261111T143003Z/`。部署包只包含中英文首页与 `_astro` 资源。线上通过 `/var/www/lwblog-current` 软链接指向版本目录；发布时先备份当前版本，再复制当前版本到新目录，叠加首页和资源，校验后原子切换软链接。保留其他项目页、应用资源和服务配置，上一版本可直接用于回滚。不要把历史静态目录当成当前发布入口。

2026-11-11：已发布至[中文首页](https://lwblog.cn/#radar)与[英文首页](https://lwblog.cn/en/#radar)。41 项自动测试及 Astro 构建通过；公网 14 个文件与部署包哈希一致，中英文动态统计、桌面及手机布局、增长榜跳转验证通过，主站现有 CSP 保持一致。
