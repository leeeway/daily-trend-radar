# 📡 leeway 技术雷达

每天自动收集开源项目、Hacker News 热议与严重安全公告，生成可订阅的技术早报和每周回顾。

- **站点**：[leeeway.github.io/daily-trend-radar](https://leeeway.github.io/daily-trend-radar/)
- **个人主页**：[lwblog.cn](https://lwblog.cn/)
- **RSS**：[feed.xml](https://leeeway.github.io/daily-trend-radar/feed.xml)

<!-- radar:start -->

最新日报：[2026-10-29](archives/2026-10-29.md)

- 📅 [2026-10-29 技术雷达](archives/2026-10-29.md)
- 📅 [2026-10-28 技术雷达](archives/2026-10-28.md)
- 📅 [2026-10-27 技术雷达](archives/2026-10-27.md)
- 📅 [2026-10-26 技术雷达](archives/2026-10-26.md)
- 📅 [2026-10-25 技术雷达](archives/2026-10-25.md)
- 📅 [2026-10-24 技术雷达](archives/2026-10-24.md)
- 📅 [2026-10-23 技术雷达](archives/2026-10-23.md)
- 📅 [2026-10-22 技术雷达](archives/2026-10-22.md)
- 📅 [2026-10-21 技术雷达](archives/2026-10-21.md)
- 📅 [2026-10-20 技术雷达](archives/2026-10-20.md)

<!-- radar:end -->

## 运作方式

北京时间每天 **14:37** 首次发布，**18:37、22:37** 再做补偿检查；日报、线上页面和已配置推送全部成功后，当天后续定时检查自动跳过。代码提交只构建站点；手动运行可选择推送、补偿模式和强制刷新。

GitHub 的 cron 是尽力而为的调度，可能延迟或丢弃事件，不能保证准点或每天必达。[官方说明](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows)。因此提供独立检查脚本，可在已登录 GitHub CLI 的常开设备运行：

```sh
python3 scripts/check_daily.py          # 只检查远端完成记录与公开站点
python3 scripts/check_daily.py --repair # 缺失时通过 workflow_dispatch 补跑
```

检查脚本不依赖 GitHub 的 cron，不需要复制企微密钥；只用宿主机已有 `gh` 登录。当天完成时安静退出，已有近期任务排队/运行时不重复触发。若使用 Codex 本机会话自动化作为兜底，电脑和 Codex 必须运行；要做到全天候，需把同一脚本部署到常开服务器或独立云调度器。

恢复机制：

- `data/digests/YYYY-MM-DD.json` 保存当天结构化资讯，补跑可复用，旧日报没有结构化数据时会自动补建。
- `data/delivery/YYYY-MM-DD.json` 保存各通道的成功回执，失败通道可单独重试，成功通道跳过。
- `data/status/YYYY-MM-DD.json` 只在公开页面验证成功且所有配置通道发送成功后记录完成，包含运行链接和完成时间。
- 抓取请求遇到临时错误最多重试三次；任务有超时限制，排队后读取最新 `main` 状态。
- 发送成功与回执提交不具备跨服务事务：若服务商已接收但返回超时，或 runner 在保存回执前中断，仍可能重复发送；不承诺恰好一次送达。

- 开源：最近 14 天创建的仓库，按累计 Stars 排名前 8；不是官方 Trending 或每日 Star 增量榜。
- 热议：Hacker News 当前热门前 8 条。
- 安全：GitHub Critical 级别公告 6 条。
- 周报：按 ISO 周聚合已有日报，同一来源链接去重，周内持续更新；是资讯汇编，不冒充人工或 AI 点评。
- 全部数据源失败时终止，保留已有文章；单个源失败会在当日日报显示缺失。

## 启用 GitHub Pages

在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流位于 `.github/workflows/daily-sync.yml`。

提交代码到 `main` 会部署已有文章；在 **Actions → Daily Radar Sync → Run workflow** 可立即抓取一次。仓库必须允许 Actions 读写内容，且 `github-pages` 环境允许从 `main` 发布。

默认网址为 `https://leeeway.github.io/daily-trend-radar/`。如果将来绑定子域名，在仓库 **Settings → Secrets and variables → Actions → Variables** 设置 `SITE_URL` 为完整 HTTPS 根网址，并在 Pages 设置自定义域名。不要把已有主站 `lwblog.cn` 的 DNS 改指 Pages。

## 手机推送（任选，可同时启用）

在 **Settings → Secrets and variables → Actions → Secrets** 添加对应项；未配置的通道自动跳过。密钥不要提交到仓库。

| 通道 | Secret 名称 | 配置说明 |
| --- | --- | --- |
| 企业微信群机器人 | `WECHAT_WEBHOOK` | 群机器人的完整 HTTPS Webhook 地址 |
| 钉钉机器人 | `DINGTALK_WEBHOOK`、`DINGTALK_SECRET` | Webhook；启用加签时填写 Secret。若设置关键词，允许“技术雷达” |
| 飞书群机器人 | `FEISHU_WEBHOOK`、`FEISHU_SECRET` | Webhook；启用签名校验时填写 Secret。若设置关键词，允许“技术雷达” |
| Telegram | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` | Bot token 与接收聊天 ID，先与 Bot 发起对话 |
| 微信（Server酱） | `SERVERCHAN_SENDKEY` | 自行在 Server酱绑定微信并取得 SendKey，额度和通道规则以服务商为准 |

企微推送使用分区 Markdown：开源与热议各两条、安全一条，附 Star 数、评论量、来源和修复建议链接；描述保留来源原文，长文按词或句子截取。其余通道保持各一条的简版。企微内容按 UTF-8 字节预算控制长度，完整日报链接始终保留。部署成功后才发送，某个通道失败仍继续尝试其他通道，并将工作流标记为失败以便排查。手动运行默认不推送，勾选 notify 后只补发尚未成功的通道；即使日报文件没有变化，也能恢复此前失败的发布和推送。

协议参考：[飞书](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)、[钉钉](https://open.dingtalk.com/document/robots/customize-robot-security-settings)、[企业微信](https://developer.work.weixin.qq.com/document/path/91770)、[Telegram](https://core.telegram.org/bots/api#sendmessage)。

## 挂载到 lwblog.cn

现有主站是 Astro，雷达站可以独立托管，不需要修改代理或主站 DNS。具体接入代码见 [integrations/lwblog.md](integrations/lwblog.md)，包括导航链接、iframe 卡片和 Astro 服务端读取最新一期 JSON。

公开接口（随 Pages 部署更新）：

| 路径 | 用途 |
| --- | --- |
| `/feed.xml` | RSS 订阅，最近 30 期日报 |
| `/latest.json` | 最新一期标题、日期、URL 及最近 30 期索引 |
| `/embed.html` | 响应式最新日报嵌入卡片 |
| `/daily/YYYY-MM-DD.html` | 每日文章 |
| `/weekly/YYYY-Www.html` | 周报与本周日报索引 |
| `/weekly/YYYY-Www.md` | 可下载周报 Markdown |

## 本地运行

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/fetch_radar.py  # 联网抓取，可用 GITHUB_TOKEN 提升 GitHub API 配额
python scripts/build_site.py
python -m http.server 8000 --directory dist
```

预览 `http://localhost:8000/`。生成目录 `dist/` 不入库。网页内容在构建时清理 HTML 和危险链接，不依赖浏览器运行 Markdown 框架。

MIT License，见 [LICENSE](LICENSE)。
