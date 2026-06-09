# GitHub Stars 增长速度报表看板 PRD

## 1. 背景

用户希望构建一个自动化系统，用于发现 GitHub 上 Star 增长最快的仓库，并按日、周、月生成 HTML 报表看板。系统需要能够跳转访问仓库，解释仓库用途，分析增长原因，并支持将每次采集与报表结果归档到外部对象存储，例如 Cloudflare R2。

本项目不限制仓库领域，目标是尽可能覆盖 GitHub 上近期增长较快的公开仓库。首版榜单规模为每日 Top 10。

## 2. 目标

### 2.1 核心目标

- 每日按北京时间统计昨日 GitHub 仓库 Stars 增长速度。
- 每周按北京时间统计上周 GitHub 仓库 Stars 增长速度。
- 每月按北京时间统计上月 GitHub 仓库 Stars 增长速度。
- 每份报表展示增长最快的 Top 10 仓库。
- 报表使用 HTML 格式，支持直接点击跳转到 GitHub 仓库。
- 对每个入榜仓库生成用途总结与增长原因分析。
- 分析信息来源包括 README、release、issues，以及联网搜索到的文章、社区讨论、新闻或其他公开页面。
- 支持将采集结果、分析结果、HTML 报表归档到本地，并预留 Cloudflare R2/S3 兼容对象存储上传能力。

### 2.2 非目标

- 首版不承诺覆盖 GitHub 全量公开仓库。
- 首版不做实时榜单，只做定时批处理。
- 首版不做用户登录、多用户权限、在线编辑配置后台。
- 首版不依赖单一第三方趋势榜单作为唯一数据源。
- 首版不保证增长原因分析是事实定论，报告应明确区分数据事实、来源证据与模型推断。

## 3. 用户场景

### 3.1 每日趋势观察

用户每天早上查看昨日 GitHub Stars 增长最快的 10 个仓库，快速了解哪些项目突然流行，以及可能的原因。

### 3.2 周度复盘

用户每周查看上周增长最快的仓库，观察持续增长项目、阶段性热点和技术方向变化。

### 3.3 月度归档

用户每月查看月度增长榜，并将报表和原始数据长期保存，用于后续趋势对比。

### 3.4 深入跳转

用户在 HTML 看板中点击仓库链接，直接访问 GitHub 仓库、release、issues 或外部来源页面。

## 4. 数据范围与候选仓库发现

### 4.1 候选范围

- 默认不限制语言、领域、topic 或组织。
- 仅统计公开 GitHub 仓库。
- 默认排除已 archived 或 disabled 的仓库。
- 默认排除 fork 仓库，避免重复统计上游项目影响。后续可配置是否包含 fork。

### 4.2 候选发现策略

由于 GitHub 官方 API 不直接提供全站 Stars 增长最快榜单，系统需要构建候选仓库池。

首版候选来源建议包括：

- GitHub Search API：
  - 按 `stars` 区间筛选。
  - 按 `created` 时间筛选近期新项目。
  - 按 `pushed` 时间筛选近期活跃项目。
  - 按 `updated` 时间筛选近期有变化项目。
  - 按 stars 倒序获取高关注项目。
- GitHub Trending 页面或可访问的公开趋势源：
  - 作为候选补充，不作为唯一来源。
- 历史入榜仓库：
  - 所有曾经入榜的仓库自动保留在候选池中，便于持续跟踪。
- 近期高增长仓库邻近扩展：
  - 可根据相同 owner、topic、语言补充相关仓库。

### 4.3 候选池规模

首版建议每日候选池规模控制在 500 到 3000 个仓库之间，避免 API 速率、分析成本和运行时间失控。

候选池规模应可配置：

- `candidate_limit`: 默认 1000。
- `top_n`: 默认 10。
- `include_forks`: 默认 false。
- `include_archived`: 默认 false。

## 5. 指标定义

### 5.1 基础指标

每个仓库至少采集：

- `full_name`: 仓库完整名称，例如 `owner/repo`。
- `html_url`: GitHub 页面地址。
- `description`: 仓库描述。
- `topics`: GitHub topics。
- `language`: 主要语言。
- `stargazers_count`: 当前 Stars 总数。
- `forks_count`: Fork 数。
- `open_issues_count`: Open issues 数。
- `created_at`: 仓库创建时间。
- `updated_at`: 仓库更新时间。
- `pushed_at`: 最近 push 时间。
- `archived`: 是否归档。
- `fork`: 是否 fork。

### 5.2 增长指标

每日指标：

- `stars_start`: 昨日开始时 Stars 数。
- `stars_end`: 昨日结束时 Stars 数。
- `stars_delta`: 昨日新增 Stars。
- `growth_rate`: 昨日新增 / 昨日开始 Stars。
- `rank_by_delta`: 按新增 Stars 排名。
- `rank_by_rate`: 按增长率排名。

周度指标：

- `weekly_stars_delta`: 上周新增 Stars。
- `weekly_growth_rate`: 上周增长率。
- `daily_delta_series`: 上周每日新增序列。

月度指标：

- `monthly_stars_delta`: 上月新增 Stars。
- `monthly_growth_rate`: 上月增长率。
- `weekly_delta_series`: 上月每周新增序列。

### 5.3 排名规则

默认榜单按 `stars_delta` 降序排序。

当 `stars_delta` 相同，排序规则为：

1. `growth_rate` 更高者优先。
2. `stargazers_count` 更高者优先。
3. `pushed_at` 更新者优先。

报表可额外展示增长率，但不默认以增长率作为主榜单，避免低基数仓库因少量新增获得异常高排名。

## 6. 时间规则

### 6.1 时区

所有报表和周期判断均以北京时间 `Asia/Shanghai` 为准。

### 6.2 日报

- 运行时间建议：每天北京时间 `00:05`。
- 报告周期：昨日 `00:00:00` 到 `23:59:59`。
- 文件日期使用昨日日期。

示例：

- 2026-06-09 00:05 运行。
- 生成 2026-06-08 的日报。

### 6.3 周报

- 运行时间建议：每周一北京时间 `00:10` 或由每日任务在周一触发。
- 报告周期：上周一 `00:00:00` 到上周日 `23:59:59`。
- 周报可以由每日任务判断当天是否为周一后生成。

### 6.4 月报

- 运行时间建议：每月 1 日北京时间 `00:15` 或由每日任务在每月 1 日触发。
- 报告周期：上个自然月第一天 `00:00:00` 到最后一天 `23:59:59`。
- 月报可以由每日任务判断当天是否为每月 1 日后生成。

## 7. 数据采集设计

### 7.1 GitHub API

优先使用 GitHub REST API 采集仓库元数据、README、releases、issues 等信息。

需要支持 GitHub Token，以提高 API 速率限制并访问更多元数据。

建议环境变量：

- `GITHUB_TOKEN`: GitHub Personal Access Token 或 fine-grained token。

### 7.2 Star 增长计算

首版以每日快照差值为主：

- 每日保存候选仓库的 `stargazers_count`。
- 日报通过昨日结束快照减去昨日开始快照计算。
- 周报和月报通过周期首尾快照计算。

补充能力：

- 对入榜候选仓库，可调用 stargazers 接口获取更精细的 `starred_at` 数据，用于校验增长时间分布。
- 大仓库 stargazers 分页成本较高，默认只对 Top 候选或异常仓库执行。

### 7.3 README 采集

对 Top 10 仓库采集 README 内容，用于用途总结。

要求：

- 优先读取默认分支 README。
- 支持 Markdown 内容。
- 对超长 README 做截断或摘要。
- 保存 README 摘要，而不是在报表中完整复制 README。

### 7.4 Release 采集

对 Top 10 仓库采集近期 releases。

关注字段：

- release 标题。
- 发布时间。
- tag。
- changelog 摘要。
- 是否为 prerelease。

### 7.5 Issues/PR 活跃度

采集近期 issues 和 PR 数据，用于判断增长是否与社区讨论、bug 修复、功能发布有关。

建议指标：

- 最近 7 天 opened issues 数。
- 最近 7 天 closed issues 数。
- 最近 7 天 merged PR 数。
- 最近活跃 issue 标题摘要。

### 7.6 外部联网搜索

对 Top 10 仓库执行联网搜索。

搜索关键词组合：

- `"owner/repo" GitHub`
- `"repo name" GitHub`
- `"repo name" release`
- `"repo name" Hacker News`
- `"repo name" Reddit`
- `"repo name" blog`
- `"repo name" news`

搜索结果用于判断：

- 是否有近期发布文章。
- 是否被社区讨论。
- 是否被媒体或榜单推荐。
- 是否与热点技术方向相关。
- 是否被大号、机构或公司传播。

## 8. 分析输出要求

### 8.1 仓库用途总结

每个仓库应输出 2 到 4 句话，说明：

- 仓库主要解决什么问题。
- 面向什么用户或场景。
- 核心技术或产品形态。

### 8.2 增长原因分析

每个仓库应输出结构化分析：

- `observed_signals`: 可观察到的增长信号。
- `likely_reasons`: 可能增长原因。
- `evidence`: 支撑来源，如 README、release、issue、外部页面。
- `confidence`: 低 / 中 / 高。
- `risk_notes`: 可能误判点。

### 8.3 报告口径

报告必须区分：

- 数据事实：API 或快照直接得到的数据。
- 来源摘要：来自 README、release、issues、搜索结果的摘要。
- 推断判断：基于证据形成的增长原因分析。

## 9. HTML 看板需求

### 9.1 页面类型

首版生成静态 HTML 文件。

页面类型：

- 日报：`reports/daily/YYYY-MM-DD.html`
- 周报：`reports/weekly/YYYY-Www.html`
- 月报：`reports/monthly/YYYY-MM.html`
- 最新入口页：`reports/index.html`

### 9.2 日报内容

日报至少包含：

- 报表标题。
- 统计周期。
- 生成时间。
- Top 10 增长榜表格。
- 每个仓库的分析卡片。
- 数据来源说明。
- 风险与限制说明。

Top 10 表格字段：

- 排名。
- 仓库名称。
- GitHub 链接。
- Stars 起始值。
- Stars 结束值。
- 新增 Stars。
- 增长率。
- 主要语言。
- topics。
- 一句话用途。
- 增长原因摘要。

### 9.3 周报内容

周报至少包含：

- 上周 Top 10 增长榜。
- 每日增长趋势摘要。
- 持续增长项目说明。
- 与前一周对比。

### 9.4 月报内容

月报至少包含：

- 上月 Top 10 增长榜。
- 周度趋势摘要。
- 本月高增长方向总结。
- 代表性仓库深度分析。

### 9.5 交互要求

首版以静态 HTML 为主，不要求复杂前端框架。

必要交互：

- 仓库名可点击跳转到 GitHub。
- 外部来源可点击跳转。
- 支持按新增 Stars、增长率、语言排序，可在后续版本实现。

## 10. 存储设计

### 10.1 本地目录

建议目录结构：

```text
config/
  sources.yml
data/
  snapshots/
    YYYY-MM-DD.json
  candidates/
    YYYY-MM-DD.json
  analysis/
    YYYY-MM-DD.json
reports/
  index.html
  daily/
    YYYY-MM-DD.html
  weekly/
    YYYY-Www.html
  monthly/
    YYYY-MM.html
src/
  collect/
  analyze/
  render/
  storage/
```

### 10.2 原始数据保存

每次运行应保存：

- 候选仓库列表。
- 仓库元数据快照。
- Top 10 分析结果。
- 外部搜索结果摘要。
- 生成的 HTML 报表。

### 10.3 Cloudflare R2 归档

后续接入 R2 时，建议使用 S3 兼容接口。

环境变量：

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_PUBLIC_BASE_URL`，可选，用于生成公开访问链接。

建议对象路径：

```text
github-stars/snapshots/YYYY-MM-DD.json
github-stars/candidates/YYYY-MM-DD.json
github-stars/analysis/YYYY-MM-DD.json
github-stars/reports/daily/YYYY-MM-DD.html
github-stars/reports/weekly/YYYY-Www.html
github-stars/reports/monthly/YYYY-MM.html
github-stars/reports/index.html
```

## 11. 自动化运行需求

### 11.1 推荐调度

创建一个每日自动化：

- 类型：Cron 自动化。
- 时间：北京时间每天 `00:05`。
- 工作目录：当前项目目录。
- 任务：运行采集、分析、报表生成流程。

每日任务内部判断：

- 每天生成昨日日报。
- 如果今天是周一，额外生成上周周报。
- 如果今天是每月 1 日，额外生成上月月报。

### 11.2 自动化提示词建议

自动化任务应描述为：

```text
运行 GitHub Stars 增长报表流程。以北京时间为准，采集候选 GitHub 仓库数据，计算昨日 Stars 增长 Top 10，读取 README、release、issues 并联网搜索外部来源，总结仓库用途与增长原因，生成昨日 HTML 日报。如果今天是周一，同时生成上周周报；如果今天是每月 1 日，同时生成上月月报。保存原始数据、分析 JSON 和 HTML 报表；如果配置了 R2/S3 环境变量，则同步归档到对象存储。最后在自动化结果中汇报生成文件路径、Top 10 摘要、异常和数据覆盖限制。
```

## 12. 配置需求

首版配置文件建议为 `config/sources.yml`。

示例：

```yaml
timezone: Asia/Shanghai
top_n: 10
candidate_limit: 1000
include_forks: false
include_archived: false
github:
  search_queries:
    - "stars:>100 pushed:>=YYYY-MM-DD"
    - "stars:10..1000 created:>=YYYY-MM-DD"
    - "stars:>1000 pushed:>=YYYY-MM-DD"
analysis:
  readme_max_chars: 12000
  external_search: true
  max_external_sources_per_repo: 5
storage:
  local_enabled: true
  r2_enabled: false
```

实际运行时，日期占位符由程序动态替换。

## 13. 错误处理

### 13.1 GitHub API 限流

如果达到 API 限流：

- 保存已采集到的数据。
- 在报表中标注数据不完整。
- 自动化结果中报告限流状态。
- 后续优先支持 GitHub Token。

### 13.2 外部搜索失败

如果联网搜索失败：

- 不阻断报表生成。
- 报表中标注外部搜索不可用。
- 仅基于 GitHub 数据进行分析。

### 13.3 R2 上传失败

如果 R2 上传失败：

- 不影响本地报表生成。
- 记录失败对象路径和错误摘要。
- 自动化结果中提示需要检查环境变量或权限。

### 13.4 历史快照缺失

如果缺少周期起始快照：

- 使用可用最早快照估算。
- 报表中标注估算口径。
- 首次运行仅建立基线，不应生成完整增长榜，除非使用 stargazers `starred_at` 做补偿计算。

## 14. 验收标准

### 14.1 MVP 验收

- 能在本地运行一次完整流程。
- 能生成候选仓库快照 JSON。
- 能根据两天快照计算 Stars 增长 Top 10。
- 能生成 HTML 日报。
- HTML 日报中每个仓库可点击跳转 GitHub。
- 每个 Top 10 仓库包含用途总结和增长原因分析。
- 报表明确展示统计周期和北京时间口径。
- 自动化提示词和调度方案可用于创建 Codex 自动化。

### 14.2 深度分析验收

- 能读取 Top 10 仓库 README。
- 能读取近期 releases。
- 能统计近期 issues/PR 活跃度。
- 能执行外部联网搜索。
- 每个仓库至少引用或摘要 1 到 5 个有效来源。
- 分析结果区分事实、来源摘要和推断。

### 14.3 存储验收

- 每次运行保存原始数据、分析 JSON 和 HTML 报表。
- R2 环境变量未配置时，系统正常跳过上传。
- R2 环境变量配置后，系统能上传指定对象路径。

## 15. 风险与限制

### 15.1 全 GitHub 覆盖风险

GitHub API 不提供全站增长榜单，因此系统只能通过候选池近似发现高增长仓库。候选策略越广，API 成本越高。

### 15.2 首次运行无历史基线

首次运行无法通过快照差值得到昨日增长，需要先建立基线。可选补偿方案是对候选仓库调用 stargazers 接口获取 `starred_at`，但对大仓库成本较高。

### 15.3 分析误判风险

外部搜索结果可能不完整或不相关。增长原因分析必须标注置信度，避免将推断当作事实。

### 15.4 API 速率限制

无 GitHub Token 时 API 调用额度较低。建议配置 `GITHUB_TOKEN`。

### 15.5 报表运行时间

深度分析会显著增加运行时间。建议先采集候选与增长榜，再只对 Top 10 做深度分析。

## 16. 分阶段计划

### Phase 1: PRD 与项目骨架

- 完成 PRD。
- 确定技术栈。
- 创建配置文件结构。
- 创建数据与报表目录。

### Phase 2: 数据采集 MVP

- 实现 GitHub Search API 候选发现。
- 实现仓库元数据采集。
- 保存每日快照。
- 支持 GitHub Token。

### Phase 3: 增长计算与 HTML 日报

- 实现快照对比。
- 生成每日 Top 10。
- 渲染 HTML 日报。
- 生成 `reports/index.html`。

### Phase 4: 深度分析

- 读取 README。
- 读取 releases。
- 统计 issues/PR 活跃度。
- 联网搜索外部来源。
- 输出结构化增长原因分析。

### Phase 5: 周报、月报与对象存储

- 实现周报。
- 实现月报。
- 接入 Cloudflare R2/S3 上传。
- 增加运行日志和错误报告。

### Phase 6: Codex 自动化

- 创建每日北京时间 `00:05` 自动化。
- 自动化调用项目脚本。
- 自动化结果汇报生成文件、Top 10 摘要、异常与限制。

## 17. 待确认问题

- 首版技术栈使用 Python 还是 Node.js。
- 是否需要同时生成 Markdown 报表，便于在 GitHub 中预览。
- HTML 看板是否需要部署到 GitHub Pages 或 Cloudflare Pages。
- 候选仓库是否需要排除明显的教程、awesome-list、镜像仓库。
- 是否需要记录每个仓库的 star 增长历史曲线，用于后续图表展示。
- R2 上传是否需要公开访问链接，还是仅作为私有归档。
