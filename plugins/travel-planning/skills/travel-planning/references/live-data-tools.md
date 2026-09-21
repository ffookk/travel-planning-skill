# 实时数据工具

只在路线已确认、需要深度规划时读取本文档。工具只读查询，不预订、不付款、不绕过平台访问限制。

## 前置健康检查

```bash
python3 skills/travel-planning/scripts/research_sources.py preflight \
  --city "杭州" \
  --airport HGH \
  --require amap-maps \
  --require flyai \
  --require open-meteo \
  --require xiaohongshu
```

`preflight` 会检查三个插件 MCP 的进程启动、`initialize`、`tools/list` 与预期工具契约，并默认执行只读上游 smoke query；同时检查飞猪 CLI 到供应商 MCP API、Open-Meteo 真实请求，以及小红书依赖与登录态。输出不包含凭证值，状态为 `ready`、`degraded` 或 `unavailable`。`--require` 可重复传入，仅当本次行程必需来源未就绪时返回非零；其他故障标为降级并按来源策略使用 fallback。`--skip-upstream` 只用于离线诊断，结果固定为 `degraded`，不能作为深度规划开始的依据。

可用来源标识为 `amap-maps`、`variflight-aviation`、`variflight-tripmatch`、`flyai`、`open-meteo` 和 `xiaohongshu`。只有实际涉及航班时才要求 Aviation；铁路或空铁联运要求 Tripmatch；中国境内地图要求高德。保留的 `capabilities` 命令只用于展示适配器、凭证和登录要求，`adapter_available=true` 不代表实时健康。

## 正式接入状态

| 来源 | 当前接入方式 | 自动化边界 |
| --- | --- | --- |
| 景区官方 | 公共搜索定位 + 官方 HTTPS 复核 + workspace 证据归档 | 页面公开可读时提取；预约或登录交给用户 |
| 飞猪 FlyAI | 插件内 `$flyai` 通用 Skill；官方 CLI 转供应商 MCP API，固定 `@fly-ai/flyai-cli@1.0.16` | 通用旅行发现及航班、火车、酒店、景点等只读查询；基础模式无需 Key，增强结果可配 Key |
| 飞常准 Aviation | `$variflight` 引导的官方 stdio MCP，固定 `@variflight-ai/variflight-mcp@1.0.3` | 航班运行、班次、舱位价格、舒适度；必须配置 Key |
| 飞常准 Tripmatch | `$variflight` 引导的官方 stdio MCP，固定 `@variflight-ai/tripmatch-mcp@0.0.5` | 火车与空铁联运候选；必须配置 Key |
| 12306 | 官方查询页最终复核 | 不调用/逆向非公开余票接口；平台火车结果不能替代出票前复核 |
| 携程 | 平台查询页用户会话交接 | 无授权 API 时不抓取；保留日期、人数、产品等条件 |
| 高德 | `$amap-maps` 引导的官方 `@amap/amap-maps-mcp-server@0.0.8` + Web 服务 API + 无 Key 路线页 iframe | MCP/API 的 POI 与算路需要 Key；页面路线展示不需要 |
| OSM/Nominatim | 低频公开地点 API | 境外入口候选，不做批量抓取 |
| Open-Meteo | 公开天气 API | 近期预报；中国预警回到中央气象台 |
| 小红书 | `autoclaw-cc/xiaohongshu-skills` 通用 Skill/CLI + 用户 Chrome 扩展 | 旅行研究默认只读；写操作必须来自用户明确请求；不绕过风控 |

## 飞猪与飞常准

三套 Provider Adapter 位于 `scripts/source_adapters.py`。插件级启动器位于根目录 `scripts/providers/`，共享环境加载器为 `scripts/runtime_env.py`；它们通过固定版本的 `npx` 命令按需启动，不进行全局安装，并且只向各 Provider 子进程传递其自身凭证。供应商原始响应统一转换为 [`travel-source-snapshot/v1`](live-source-schema.md)。路线确认后的深度规划直接执行这些只读查询，不逐次请求用户确认，也不因预计调用次数或额度提示而暂停。查询只发送完成检索所需的日期、地点、车站、机场、航班号和住宿条件；正式研究必须传入 `--workspace` 与 `--task-id`，把完整标准快照直接写入任务目录。所有命令均只读，不预订、不占座、不付款。

源码开发时，私密配置默认位于插件根目录 `config/sources.local.env`；该文件已忽略，并在安装、分享和缓存同步时明确排除。安装后的插件没有本地文件时，回退到用户配置目录 `~/.config/travel-planning/sources.local.env`，并在新路径尚不存在时兼容旧配置目录。也可通过 `TRAVEL_SOURCES_CONFIG` 指定其他文件：

```dotenv
# 可选；飞猪基础模式无需 Key
FLYAI_API_KEY=

# 飞常准两套 MCP 必需
VARIFLIGHT_API_KEY=

# 高德官方 MCP 与 Web 服务 API 共用；两种变量名任选其一
AMAP_MAPS_API_KEY=
```

批次一，飞猪航班、火车与酒店。开放式交通候选发现必须使用 `*-coverage`，一次覆盖最早出发、最晚出发、时长优先、价格优先和平台推荐五种排序；单排序命令只用于复核指定窗口或指定班次，不能据此判断全天没有合适班次：

```bash
python3 skills/travel-planning/scripts/research_sources.py flyai-flight-coverage \
  --origin "北京" --destination "上海" --date 2026-10-03 \
  --workspace ".travel-research/example-trip" --task-id route-data

python3 skills/travel-planning/scripts/research_sources.py flyai-train-coverage \
  --origin "北京南" --destination "上海虹桥" --date 2026-10-03 \
  --seat-class "second class" \
  --workspace ".travel-research/example-trip" --task-id route-data

python3 skills/travel-planning/scripts/research_sources.py flyai-hotel \
  --destination "杭州" --poi "西湖" \
  --check-in 2026-10-03 --check-out 2026-10-05 \
  --adults 4 --rooms 2 --bed-type "双床房" \
  --stars "4,5" --max-price 800 \
  --workspace ".travel-research/example-trip" --task-id stay-food
```

覆盖查询返回 `travel-source-snapshot-batch/v1` 汇总，同时把其中每个标准快照分别写入任务目录；任务结果把全部 `snapshot_ids` 写入 `source_snapshot_ids[]`，再按硬时间窗口筛选。商圈酒店查询只用于发现候选；采用前必须以酒店全名再次查询，并用地图核验城市、行政区、地址、坐标和距目标锚点。`--adults` 与 `--rooms` 会进入查询快照，但当前飞猪酒店工具不保证按多间同房型校验库存，因此 `availability.remaining=null` 时只能称为报价候选。

批次二，飞常准航班运行、价格、舒适度、火车与空铁联运：

```bash
python3 skills/travel-planning/scripts/research_sources.py variflight-flight \
  --origin BJS --origin-kind city \
  --destination PVG --destination-kind airport \
  --date 2026-10-03

python3 skills/travel-planning/scripts/research_sources.py variflight-flight-number \
  --flight-number MU2157 --date 2026-10-03

python3 skills/travel-planning/scripts/research_sources.py variflight-flight-price \
  --origin BJS --destination SHA --date 2026-10-03

python3 skills/travel-planning/scripts/research_sources.py variflight-flight-comfort \
  --flight-number MU2157 --date 2026-10-03

python3 skills/travel-planning/scripts/research_sources.py variflight-train \
  --origin "北京" --destination "上海" --date 2026-10-03

python3 skills/travel-planning/scripts/research_sources.py variflight-train-stations \
  --query "北京西"

python3 skills/travel-planning/scripts/research_sources.py variflight-air-rail \
  --origin BJS --destination SHA --date 2026-10-03
```

IATA 参数必须使用 3 位城市或机场代码。`variflight-flight` 通过 `--origin-kind` 和 `--destination-kind` 区分城市代码与具体机场代码；价格和空铁联运命令只接受城市代码。正式研究中的飞常准命令同样追加 `--workspace <目录> --task-id route-data`。缺凭证、凭证被拒、额度不足、无结果和供应商故障分别输出，不得把其中任何一种改写成“没有可用班次”。

## 天气

无需 Key，通过 Open-Meteo 查询近期预报、降雨、紫外线、日出和日落：

```bash
python3 skills/travel-planning/scripts/research_sources.py weather --location "杭州" --days 7
```

也可传经纬度：

```bash
python3 skills/travel-planning/scripts/research_sources.py weather --latitude 30.25 --longitude 120.17 --name "西湖" --days 7
```

中国天气预警不从 Open-Meteo 推断，必须同时保留中央气象台预警复核入口。

## 高德地图

后台 POI/算路需要用户自己的高德 Web 服务 Key。页面内嵌路线按宿主设备切换：桌面浏览器使用 `https://ditu.amap.com/dir`，移动端驾车使用 `https://m.amap.com/navigation/carmap/`，公交与步行仍使用通用路线页；这些展示地址都不需要 JavaScript API Key 或安全密钥。源码开发时推荐直接编辑插件根目录的私密配置文件：

```text
config/sources.local.env
```

填写：

```dotenv
AMAP_MAPS_API_KEY=你的高德Web服务Key
```

插件级环境加载器会自动读取该文件。`AMAP_API_KEY` 也是兼容别名，官方 MCP 启动器会在子进程中映射为 `AMAP_MAPS_API_KEY`。可提交的字段模板位于 `config/sources.example.env`；本机 `sources.local.env` 不得进入 Git、安装包、分享包或插件缓存。环境变量仍可覆盖文件配置：

```bash
export AMAP_API_KEY="<your-key>"
# 或 export AMAP_MAPS_API_KEY="<your-key>"
```

Web 服务 Key 只用于后台请求，绝不能写入行程 JSON、HTML、命令输出或版本库。`sources.local.env` 本身不得提交。

查景区入口或 POI：

```bash
python3 skills/travel-planning/scripts/research_sources.py amap-place --city "杭州" --keywords "西湖风景区 曲院风荷入口"
```

查路线：

```bash
python3 skills/travel-planning/scripts/research_sources.py amap-route \
  --origin "120.130210,30.259002" \
  --destination "120.144590,30.243710" \
  --mode walking

python3 skills/travel-planning/scripts/research_sources.py amap-route \
  --origin "120.130210,30.259002" \
  --destination "120.144590,30.243710" \
  --mode transit \
  --city "杭州"
```

高德返回的 `duration_seconds` 是平台路线耗时，行程中的门到门时间还需加上出入口步行、等车、换乘、安检和缓冲。景区入口的开放状态仍需景区官网确认。

### 餐厅候选批次

餐厅研究不能只搜一次“附近美食”。`restaurant-research` 先按每个用餐时段的上一出口、下一入口和绕行上限建立搜索范围，再对每个候选分别执行地点核验与社区查询：

```bash
python3 skills/travel-planning/scripts/research_sources.py amap-place \
  --city "杭州" --keywords "灵隐寺出口 杭帮菜"

python3 skills/xiaohongshu/scripts/cli.py search-feeds \
  --keyword "杭州 灵隐 餐厅 店名 排队 口味" \
  --sort-by 最新 --publish-time 半年内
```

高德地点结果用于确认分店、POI、地址、坐标、电话和平台入口；再用 `amap-route` 分别查询“上一站→餐厅”和“餐厅→下一站”。营业、人均和菜单需从商家官方或可靠餐饮详情页获取，查询不到时保留带店名、日期和待核字段的手动入口。小红书只用于近期口味、份量、排队、服务和推广风险；每条被计入共识的笔记都保存原帖链接，不能用小红书互动数替代餐厅评分。

所有候选先写入单次 workspace：discovery 保存 `restaurants[]`、`restaurant_snapshots[]`、`meal_candidate_sets[]`，route 阶段保存每餐唯一 `meal_baseline_routes[]` 和逐候选 `meal_route_evaluations[]`，ranking 再输出 `meal_options[]`。只有稳定身份字段可在审查后晋升公共餐厅库；评分、营业、价格、排队、基准路线和本次路线距离不得晋升。

渲染器根据交通段的 `map_route.origin`、`map_route.destination` 与 `map_route.mode` 生成高德消费端路线页 iframe。路线类型要求 `car`、`bus` 或 `walk`。`m.amap.com/navigation/carmap` 会检查浏览器 UA，iframe 的尺寸或宿主页 `meta viewport` 不能把桌面 UA 改成移动 UA；因此桌面必须使用通用 `ditu.amap.com/dir`，只有宿主浏览器报告移动设备时才给驾车段加载 `carmap`。首次打开可能出现高德登录提示，用户关闭后由高德自己的存储状态控制后续展示；宿主页不得尝试跨域关闭或修改弹窗。同时必须保留官方 URI API 的 `action_links[type=map]`。

## 境外地点与入口候选

无需 Key，通过 Nominatim/OpenStreetMap 做低频地点检索。查询词尽量包含当地语言名称、城市和国家；一次命令只发一个请求，禁止并发扫点或批量抓取。

```bash
python3 skills/travel-planning/scripts/research_sources.py osm-place \
  --query "Kiyomizu-dera Niomon, Kyoto, Japan" \
  --countrycodes jp --limit 3
```

返回坐标是候选，不等于景区官方入口。用景区官网确认入口名称和开放状态，再用实际地图平台确认导航与门到门时间。中国境内仍优先高德，避免坐标系混用。

## 手动查询链接

自动获取失败或不允许自动化时，生成可直接写入 `action_links[]` 的结构：

```bash
python3 skills/travel-planning/scripts/research_sources.py fallback --kind train \
  --origin "北京南" --destination "上海虹桥" --date "2026-10-03" \
  --fields "车次、时刻、二等座票价和余票"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind ctrip \
  --product "酒店" --city "杭州" --date "2026-10-03 至 2026-10-05" \
  --travelers "2 位成人·1 间房"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind ctrip \
  --product "包车＋司机/司导" --origin "上一景点出口" \
  --destination "偏远景区官方入口" --date "2026-10-04" \
  --travelers "4 人·4 件行李" \
  --fields "车型、报价包含项、资质、保险、超时费和退改"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind map \
  --city "杭州" --keywords "西湖风景区 曲院风荷入口"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind map \
  --map-provider google --city "Kyoto" \
  --keywords "Kiyomizu-dera Niomon entrance"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind weather \
  --city "杭州" --date "2026-10-03"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind xiaohongshu \
  --keywords "西湖 10月 日落 入口 避坑"
```

景区降级链接必须传入已经核对过的官方地址：

```bash
python3 skills/travel-planning/scripts/research_sources.py fallback --kind attraction \
  --keywords "门票、开放时间、停止入场、预约和临时公告" \
  --url "https://example.gov.cn/official-attraction-page"
```

## 数据合并

- 飞猪与飞常准完整标准快照先写入 `snapshots/<task_id>/`，研究结果只保留 `source_snapshot_ids[]`。
- 主 Agent 合并后把快照写入 `planning.source_snapshots[]`；采用的交通或住宿对象使用 `inventory_refs[]` 精确关联 `snapshot_id + offer_id`，页面显示 Provider、查询时间、有效期和供应商实际返回的 HTTPS 入口。
- 动态报价、库存和运行状态只属于本次 workspace；机场、车站、酒店身份等稳定数据经审核后才可进入公共资料库。
- 高德和天气 API 返回的动态数据状态使用 `platform_reported`，人工查询入口使用 `to_recheck`。
- 手动查询链接必须保留查询条件，不将平台首页冒充为已核验详情页。

## 小红书

首次使用按[小红书通用能力集成](xiaohongshu-integration.md)安装上游 Skill，并由用户本人加载 Chrome 扩展和完成登录。常用命令：

```bash
python3 skills/xiaohongshu/scripts/setup.py status
python3 skills/xiaohongshu/scripts/cli.py check-login
python3 skills/xiaohongshu/scripts/cli.py search-feeds \
  --keyword "目的地 月份 日落 入口 避坑" \
  --sort-by 最新 --publish-time 半年内
python3 skills/xiaohongshu/scripts/cli.py get-feed-detail \
  --feed-id "<feed-id>" --xsec-token "<临时令牌>"
```

上游搜索会返回详情读取所需的临时令牌。只能在当前查询链内部使用，不得展示或归档；旅行 workspace 只保存公开来源标识或链接和研究摘要，不能复制用户数据目录中的小红书运行状态。
