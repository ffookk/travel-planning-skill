# 跨行程公共资料库

`.travel-library/` 是跨行程复用的规范化实体库；`.travel-research/<trip-id>/` 是单次旅行的动态研究工作区。历史 workspace 的 `search-archive` 只用于发现旧线索，不能代替公共实体库。

## 数据边界

公共库只保存慢变化事实和执行骨架：规范名称、别名、行政区、坐标、实体地址、官方主页/公告/预约入口的网址、长期入口出口、内部卡点蓝图、典型游览时长、静态无障碍信息、许可明确的图片元数据，以及带月份和复核要求的季节画像。餐厅实体可保存准确分店、地图 POI ID、菜系、长期招牌菜、电话、服务方式、长期设施/停车画像、饮食标签和许可图片。

以下信息始终留在单次旅行 workspace：票价、开放/停票/停止入场/闭园时间、临时公告、预约库存、余票、车次航班时刻、酒店报价与房态、餐厅平台评分/评价量/当前人均/菜单价/当日营业/排队/预约、社区帖子互动数、相对本次景点或酒店的距离与绕行、天气预警、实时路况及地图实时耗时。餐厅动态字段使用 `restaurant-source-snapshot/v1`，路线适配使用本次 `meal_baseline_routes[]` 与 `meal_route_evaluations[]`，均不得反向写回公共实体。

公共实体是基础层，本次查询是覆盖层。合并优先级为：用户确认条件 → 本次日期权威动态事实 → 本次平台快照 → 公共库稳定字段 → 公共库季节候选。动态覆盖不得反向修改公共库。

## 目录与版本

```text
.travel-library/
|-- manifest.json
|-- entities/<entity-type>/<entity-id>.json
`-- history/<entity-type>/<entity-id>/<revision>.json
```

实体含 `library_version`、`entity_schema_version`、`revision`、`content_digest`、`status`、`last_verified_at`、`review_after` 和 `superseded_by`。`status` 使用 `active`、`needs_review`、`deprecated` 或 `superseded`。更新采用 `expected_revision` 乐观锁，覆盖前自动保存旧 revision。

公共实体的 `source_refs[]` 必须包含 `source_id`、标题、HTTPS URL、来源类型、权威主体、最近核验时间和状态。官方入口失效、运营主体或入口迁移时标记 `needs_review` 并创建新 revision；永久停业用 `deprecated`；被新实体替代用 `superseded`，不删除历史。

## 使用流程

初始化和搜索：

```bash
python3 skills/travel-planning/scripts/travel_library.py init
python3 skills/travel-planning/scripts/travel_library.py search --query "青海湖 二郎剑" --entity-type attraction
```

主 Agent 选择匹配实体后，将确定的 revision 快照进本次 workspace：

```bash
python3 skills/travel-planning/scripts/travel_library.py materialize \
  --workspace .travel-research/<trip-id> \
  --entity-id <entity-id>
```

结果写入 `state/library-seed.json`。每个任务 assignment 的输入摘要同时覆盖 `brief.json`、`selected-route.json`、这个 seed 和任务模板；任一文件变化后，旧 Agent 结果不能提交。

子 Agent 只能在结果的 `catalog_candidates[]` 中提出公共候选，不能直接修改共享库。候选通过本次审查后，由主 Agent逐个审核晋升：

```bash
python3 skills/travel-planning/scripts/travel_library.py promote \
  --workspace .travel-research/<trip-id> \
  --task-id attractions \
  --entity-id <entity-id>
```

更新已有实体时必须再传 `--expected-revision <n>`。晋升记录写入本次 workspace 的 `state/library-promotions.json`。不得批量自动晋升。

## Agent 模板

五个模板位于 `assets/agent-templates/`。创建 assignment 时脚本将对应模板复制到 `assignments/templates/<task-id>.result-template.json`，并从模板正文读取版本、记录内容摘要：

- `attractions.json`
- `route-data.json`
- `stay-food.json`
- `restaurants.json`
- `weather-risk.json`

Agent 从 assignment 复制 `input_revision`、`template_version` 和 `template_digest`，再填写模板。`entities` 只保存本次旅行数据；`catalog_candidates` 只保存可复用候选；`event_bindings` 表达本次如何使用数据。提交时会检查领域字段所有权、公共候选白名单和来源引用。

公共库里找不到实体时照常调研，不允许为了复用而降低来源要求。公共实体过期或状态不是 `active` 时，默认禁止 materialize；`--include-stale` 仅供审计，不得让过期事实直接进入最终行程。
