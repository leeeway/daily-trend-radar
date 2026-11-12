# 📡 leeway 技术雷达

每天自动收集开源项目、Hacker News 热议与严重安全公告，生成可订阅的技术早报和每周回顾。

- **站点**：[leeeway.github.io/daily-trend-radar](https://leeeway.github.io/daily-trend-radar/)
- **个人主页**：[lwblog.cn](https://lwblog.cn/)
- **资讯库**：[发现与收藏](https://leeeway.github.io/daily-trend-radar/explore.html)
- **RSS**：[feed.xml](https://leeeway.github.io/daily-trend-radar/feed.xml)

<!-- radar:start -->

最新日报：[2026-11-12](archives/2026-11-12.md)

- 📅 [2026-11-12 技术雷达](archives/2026-11-12.md)
- 📅 [2026-11-11 技术雷达](archives/2026-11-11.md)
- 📅 [2026-11-10 技术雷达](archives/2026-11-10.md)
- 📅 [2026-11-09 技术雷达](archives/2026-11-09.md)
- 📅 [2026-11-08 技术雷达](archives/2026-11-08.md)
- 📅 [2026-11-07 技术雷达](archives/2026-11-07.md)
- 📅 [2026-11-06 技术雷达](archives/2026-11-06.md)
- 📅 [2026-11-05 技术雷达](archives/2026-11-05.md)
- 📅 [2026-11-04 技术雷达](archives/2026-11-04.md)
- 📅 [2026-11-03 技术雷达](archives/2026-11-03.md)

<!-- radar:end -->

## 运作方式

北京时间每天 **14:37** 首次发布，**18:37、22:37** 再做补偿检查；日报和线上页面成功、已配置通道均成功送达或按关注规则静默跳过后，当天后续定时检查自动跳过。代码提交只构建站点；手动运行可选择推送、补偿模式和强制刷新。

GitHub 的 cron 是尽力而为的调度，可能延迟或丢弃事件，不能保证准点或每天必达。[官方说明](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows)。因此提供独立检查脚本，可在已登录 GitHub CLI 的常开设备运行：

```sh
python3 scripts/check_daily.py          # 只检查远端完成记录与公开站点
python3 scripts/check_daily.py --repair # 缺失时通过 workflow_dispatch 补跑
```

检查脚本不依赖 GitHub 的 cron，不需要复制企微密钥；只用宿主机已有 `gh` 登录。当天完成时安静退出，已有近期任务排队/运行时不重复触发。若使用 Codex 本机会话自动化作为兜底，电脑和 Codex 必须运行；要做到全天候，需把同一脚本部署到常开服务器或独立云调度器。

恢复机制：

- `data/digests/YYYY-MM-DD.json` 保存当天结构化资讯，补跑可复用，旧日报没有结构化数据时会自动补建。
- `data/delivery/YYYY-MM-DD.json` 保存各通道的成功回执，失败通道可单独重试，成功通道跳过。
- `data/status/YYYY-MM-DD.json` 在公开页面验证成功且所有配置通道送达或按关注规则有意跳过后记录完成，区分送达与跳过，包含运行链接和完成时间。
- 抓取请求遇到临时错误最多重试三次；任务有超时限制，排队后读取最新 `main` 状态。
- 发送成功与回执提交不具备跨服务事务：若服务商已接收但返回超时，或 runner 在保存回执前中断，仍可能重复发送；不承诺恰好一次送达。

- 开源：最近 14 天创建的仓库，按累计 Stars 排名前 8；不是官方 Trending 或每日 Star 增量榜。
- 热议：Hacker News 当前热门前 8 条。
- 安全：GitHub Critical 级别公告 6 条。
- 周报：按 ISO 周聚合已有日报，同一来源链接去重，周内持续更新；是资讯汇编，不冒充人工或 AI 点评。
- 全部数据源失败时终止，保留已有文章；单个源失败会在当日日报显示缺失。

## 发现与收藏

[资讯库](https://leeeway.github.io/daily-trend-radar/explore.html)聚合全部已归档资讯，同类内容按来源链接合并，保留首次、最近和实际收录日期。

- 关键词搜索覆盖标题、简介、语言、CVE 和链接，支持空格分隔多个关键词（全部匹配）。
- 按开源／热议／安全、收录日期范围筛选，按最近或最早收录排序，分批加载。
- 点击卡片的“收藏”，下次打开仍可在“只看收藏”中查看。收藏仅存于当前站点的当前浏览器，不跨设备同步；清理浏览器数据或切换域名会影响收藏。浏览器禁止存储时降级为本页临时收藏。
- 点击“标记已读”管理阅读进度，也可随时标为未读；打开外部链接不会自动当作读完。“只看未读”可与收藏、关键词和来源筛选组合。
- [最新一期首次收录](https://leeeway.github.io/daily-trend-radar/explore.html?fresh=1)只展示在本站归档中首次出现于最新一期的内容；曾出现后再次收录的条目不会重新标新。首页同步展示三类新增数量。这里的“首次”指现有本站归档，不代表该项目或文章刚在全网发布。
- 筛选条件保留在地址栏，可复制链接分享。例如 [Python 开源项目](https://leeeway.github.io/daily-trend-radar/explore.html?q=Python&source=repos)。

阅读工作台的“备份阅读记录”会下载 JSON 文件，包含收藏和已读状态；在另一设备打开同一个雷达站点，选择“恢复记录”即可合并去重，保留设备上已有的记录。恢复在浏览器本地处理，不上传备份文件。只接受技术雷达 version 1 备份（最多 1 MB、每类最多 20,000 条），无效格式会拒绝导入。它是手动备份恢复，不是账号云同步。旧版本收藏在首次使用新页面时自动读取，修改后与已读状态一起保存。

可分享组合筛选：`?fresh=1&unread=1` 查看本期新收录且未读内容；`?saved=1&unread=1` 查看收藏中的待读内容。分享的是筛选条件，收藏和已读记录仍属于各自浏览器。

### 网页关注主题

在资讯库展开“我的关注主题”，保存关注词与排除词，即可使用“只看关注”。任一关注词命中即可，排除词优先；只有排除词时展示未命中排除词的内容。匹配标题、简介、语言、CVE、等级和链接中的字面文字，不区分大小写及全半角；短语中的空格保留，不使用正则或语义匹配。每类最多 40 个词，每词最多 80 字符，用中英文逗号、分号或换行分隔。

卡片显示“关注命中”或“排除词命中”，方便核对原因。关注筛选可与搜索、来源、日期、未读、收藏和增长榜组合；“重置筛选”不会删除已保存的关注设置。没有设置主题时，“只看关注”显示设置引导，不把全库当作命中结果。

网页关注设置仅存于浏览器，不读取 GitHub Variables，不改变手机推送偏好，也不写入地址栏。分享 `?following=1` 只分享筛选开关，接收者使用自己的关注设置。阅读备份 version 1 新增可选 `interests.include/exclude` 字段，恢复时与本机词表合并去重；旧备份没有该字段时保留本机设置。合并超过词数上限会整体拒绝，避免部分导入。

旧日报从 Markdown 提取全部条目，并用已有精选数据补充；历史简介可能已被原日报截断，不补造内容。升级后的每日抓取保存 `schema_version: 2` 和完整 `items.repos/stories/advisories`，手机推送继续读取独立的精选 `brief`。指标显示最近一次收录快照，不能当作实时 Star 数或每日增长量。

### Star 增长趋势

开源卡片展示按真实日期分布的 Star 曲线，可展开采样表逐日核对。`较上次采样`标注实际间隔天数；缺失日期不补零、不插值，也不将多天增长冒充单日增长。Star 下降和零增长按实记录，只有一次采样时提示继续积累。

排序选择 [最新一期 7 日 Star 增长](https://leeeway.github.io/daily-trend-radar/explore.html?sort=growth)：只纳入最新一期收录、且具备当天与恰好 7 天前两次 Star 快照的项目，按实际差值降序排列。旧项目停止收录后不进入当前增长榜；排行榜不等于整个 GitHub 的增长榜。

`search-index.json` 中的开源条目新增 `star_history`（`date`、`stars`）与 `star_trend`（`previous_delta`、`previous_days`、`previous_date`、`week_delta`、`week_start`）。无法比较的指标为 `null`，与零增长区分。现有 version 1 索引字段保持兼容。

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

企微推送使用分区 Markdown：开源与热议各两条、安全一条，附 Star 数、评论量、来源和修复建议链接；描述保留来源原文，长文按词或句子截取。其余通道默认保持各一条的简版；启用关键词筛选后使用匹配内容的精选摘要。企微内容按 UTF-8 字节预算控制长度，完整日报链接始终保留。部署成功后才发送，某个通道失败仍继续尝试其他通道，并将工作流标记为失败以便排查。手动运行默认不推送，勾选 notify 后只补发尚未成功的通道；即使日报文件没有变化，也能恢复此前失败的发布和推送。

### 关注关键词定制推送

在 [GitHub Actions Variables](https://github.com/leeeway/daily-trend-radar/settings/variables/actions) 设置（不是 Webhook Secrets）：

| Variable | 示例 | 作用 |
| --- | --- | --- |
| `RADAR_KEYWORDS` | `Python,Rust,AI Agent,DeepSeek` | 任意一个词命中即可入选 |
| `RADAR_EXCLUDE_KEYWORDS` | `crypto,招聘` | 任意一个词命中就排除，优先于关注词 |

支持英文／中文逗号、分号或换行分隔，也支持 JSON 字符串数组。空格属于关键词本身，因此 `AI Agent` 是一个短语。按字面子串匹配标题、简介、语言、CVE、项目名和链接，不区分大小写及全半角，不进行语义扩展。筛选范围是当天实际收录的全部资讯，不是全网搜索。

默认配置在 `config/notifications.json`，两个列表均为空，保留综合精选。非空 GitHub Variable 覆盖同名配置；填写 `[]` 可以显式清空列表。只有排除词时，从当天全部资讯中排除。所有已配置通道使用相同偏好；开源、热议、安全各最多精选 2、2、1 条，消息显示总命中数，完整内容仍见日报。没有任何匹配时静默跳过，并在回执的 `skipped` 中记为 `no_keyword_match`，完成记录会列为 `skipped_channels`，不会冒充已送达，也不会反复补发。

第一次投递前将选定的公开内容写入当天回执的 `selection`。补偿重试复用该内容，修改关注词不会改写当天已经开始的投递；已成功或有意跳过的通道仍不重复处理。新偏好从下一天的新投递生效。筛选错误会使任务失败，不会悄悄退回综合推送。关注变量及 Webhook 不写入公开站点或回执；如果直接编辑仓库配置文件，其中的关注词会随公共仓库公开。

先用旧归档预览，不发消息、不写回执：

```sh
RADAR_KEYWORDS='DeepSeek,AI Agent' python scripts/notify.py --digest data/digests/2026-11-11.json --preview
```

旧版本数据会从对应 Markdown 日报恢复全部条目；若完整数据和日报均缺失，任务报错。旧日报简介可能已被截断，因此历史关键词预览可能少于完整原文可命中的数量。

协议参考：[飞书](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)、[钉钉](https://open.dingtalk.com/document/robots/customize-robot-security-settings)、[企业微信](https://developer.work.weixin.qq.com/document/path/91770)、[Telegram](https://core.telegram.org/bots/api#sendmessage)。

## 挂载到 lwblog.cn

现有主站是 Astro，雷达站可以独立托管，不需要修改代理或主站 DNS。具体接入代码见 [integrations/lwblog.md](integrations/lwblog.md)，中英文主站已使用原生卡片连接新增发现、Star 增长榜和阅读工作台，统计随日报自动更新。

公开接口（随 Pages 部署更新）：

| 路径 | 用途 |
| --- | --- |
| `/feed.xml` | RSS 订阅，最近 30 期日报 |
| `/latest.json` | 最新一期标题、日期、URL 及最近 30 期索引 |
| `/explore.html` | 关键词检索、来源与日期筛选、首次收录、收藏与未读管理、阅读记录备份恢复 |
| `/search-index.json` | 全部历史资讯去重索引（version 1），含实际收录日期与最近快照指标 |
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
node --test tests/*.test.cjs # 阅读工作台与主站接入测试，Node 18+，无需 npm 依赖
python scripts/fetch_radar.py  # 联网抓取，可用 GITHUB_TOKEN 提升 GitHub API 配额
python scripts/build_site.py
python -m http.server 8000 --directory dist
```

预览 `http://localhost:8000/`。生成目录 `dist/` 不入库。网页内容在构建时清理 HTML 和危险链接，不依赖浏览器运行 Markdown 框架。

MIT License，见 [LICENSE](LICENSE)。
