# 餐厅候选研究与路线适配

餐饮是路线确认后的前置研究，不是页面生成时补一句“附近吃饭”。先有景点出入口、酒店候选和交通骨架，再建立用餐时段，最后研究餐厅并计算绕行；未完成本流程的正餐不能进入 `confirmed_planning`。

## 流水线位置

1. 主 Agent 根据事件骨架生成 `meal_slots[]`。每个时段固化日期、餐别、时间窗、上一事件出口、下一事件入口、交通方式、最长可接受绕行、用餐时长、预算、饮食与停车约束。
2. `restaurant-discovery`（`stage=restaurant_discovery`，领域 `restaurant-research`）读取景点、住宿与第一阶段路线结果，搜索餐厅实体和近期体验，输出 `meal_candidate_sets[]`；正常时每个正餐时段提交 3 个有效候选，最低 2 个，但不得提前写最终主选和排名。
3. `route-data-meals`（`stage=meal_route_evaluation`，领域 `route-data`）依赖 `restaurant-discovery`，为每餐先生成唯一 `meal_baseline_routes[]`，再按已核验坐标计算“上一锚点 → 餐厅 → 下一锚点”两段路线和额外绕行。
4. `restaurant-ranking`（`stage=restaurant_ranking`，领域 `restaurant-research`）同时依赖前两者，只输出完成证据化比较与排序的 `meal_options[]`。主 Agent 只从该任务已完成比较的候选中选择主选和备选。
5. 独立审查检查候选数量、来源、距离、评分语义、图片权利、动态状态和主备切换条件，阻断项清零后才渲染。

三个任务使用不同 `task_id`，结果不可覆盖。后续 assignment 只能在依赖结果以 `complete` 状态提交后创建，且依赖文件进入 `input_revision`；这样餐厅发现结果或路线评估被改动后，旧排序不能继续提交。

机场安检区、封闭景区、服务区、深夜到达地等客观上不足 2 个可选商户时，可以使用 `candidate_policy.status=constrained`，但必须记录搜索范围、唯一候选的证据、随身餐或便利店备选和复核时间；不能用“附近没有”作为无来源例外。

## 数据分层

### 餐厅实体 `planning.restaurants[]`

餐厅实体描述“这家店是什么”，不包含它在某一天是否顺路、营业或评分：

```json
{
  "id": "restaurant-daji-dunhuang",
  "name": "达记酱驴肉黄面馆",
  "aliases": ["达记驴肉黄面"],
  "cuisine": ["敦煌地方菜", "面食"],
  "location": {
    "physical_address": "甘肃省敦煌市沙州镇示例路18号",
    "coordinates": "94.661114,40.137937",
    "coordinate_system": "GCJ-02",
    "poi_id": "amap-poi-id",
    "poi_provider": "amap",
    "poi_source_id": "restaurant-amap-daji",
    "poi_verified_at": "2026-09-21T12:00:00+08:00",
    "phone": "公开电话或未取得"
  },
  "signature_dishes": ["驴肉黄面", "酱驴肉"],
  "dietary_notes": ["两人先点小份肉"],
  "media": [
    {
      "kind": "display_image",
      "url": "https://...",
      "alt": "餐厅或菜品实景",
      "source_url": "https://...",
      "source_label": "商家官方",
      "author": "商家",
      "license_or_permission": "official_promotional_asset",
      "checked_at": "2026-09-21"
    }
  ],
  "action_links": [{"type": "restaurant", "label": "查看店铺详情", "provider": "高德", "url": "https://www.amap.com/place/..."}],
  "source_ids": ["restaurant-amap-daji"]
}
```

可执行结构以 `schemas/restaurant.schema.json` 为准；字符串格式只能做确定性筛查，真实 POI 存在性必须由绑定的地图查询证据和最终事实审查确认。

### 动态快照 `planning.restaurant_snapshots[]`

评分、营业、人均、排队和社区信号按餐厅、适用日期与用餐时段单独保存，使用 `restaurant-source-snapshot/v1`：

```json
{
  "schema_version": "restaurant-source-snapshot/v1",
  "snapshot_id": "restaurant-daji-20261005-lunch",
  "restaurant_id": "restaurant-daji-dunhuang",
  "applicable_date": "2026-10-05",
  "time_window": "13:15–14:30",
  "platform_signals": [
    {
      "platform": "amap",
      "rating": "4.6",
      "review_count": 1280,
      "per_person": "约80元",
      "status": "platform_reported",
      "checked_at": "2026-09-21T12:00:00+08:00",
      "source_ids": ["restaurant-amap-daji"]
    }
  ],
  "community_consensus": {
    "platform": "xiaohongshu",
    "status": "available",
    "query_runs": [{"keyword": "达记酱驴肉黄面馆 敦煌 排队", "filters": {"publish_time": "year"}, "executed_at": "2026-09-21T12:00:00+08:00"}],
    "notes_considered": 3,
    "recent_note_count": 3,
    "positive": ["黄面口感", "地方特色"],
    "negative": ["旺季排队", "肉类价格需看菜单"],
    "promotion_risk": "medium",
    "confidence": "medium",
    "checked_at": "2026-09-21T12:00:00+08:00",
    "references": [
      {"note_id": "note-1", "title": "原帖标题1", "url": "https://www.xiaohongshu.com/explore/note-1", "author": "作者甲", "published_at": "2026-08-01", "checked_at": "2026-09-21T12:00:00+08:00", "source_id": "restaurant-xhs-daji-1"},
      {"note_id": "note-2", "title": "原帖标题2", "url": "https://www.xiaohongshu.com/explore/note-2", "author": "作者乙", "published_at": "2026-07-01", "checked_at": "2026-09-21T12:00:00+08:00", "source_id": "restaurant-xhs-daji-2"},
      {"note_id": "note-3", "title": "原帖标题3", "url": "https://www.xiaohongshu.com/explore/note-3", "author": "作者丙", "published_at": "2026-06-01", "checked_at": "2026-09-21T12:00:00+08:00", "source_id": "restaurant-xhs-daji-3"}
    ]
  },
  "operations": {
    "opening_hours": "平台或店铺当前公示",
    "reservation": "是否接受预约",
    "queue": "近期排队信号",
    "parking": "停车/上下客条件",
    "status": "platform_reported",
    "checked_at": "2026-09-21T12:00:00+08:00",
    "recheck_at": "2026-10-05T11:30:00+08:00"
  },
  "checked_at": "2026-09-21T12:00:00+08:00",
  "expires_at": "2026-10-05T11:30:00+08:00",
  "action_links": [{"type": "restaurant", "label": "复核营业状态", "provider": "高德", "url": "https://www.amap.com/place/..."}],
  "source_ids": ["restaurant-amap-daji", "restaurant-xhs-daji-1", "restaurant-xhs-daji-2", "restaurant-xhs-daji-3"]
}
```

`platform_signals[]` 分平台展示评分、评价量和人均，不把高德、小红书或其他平台强行合成一个虚假“用户评分”。无法取得数字时写 `status=unavailable`、原因、查询条件和手动入口，不能猜测。

`community_consensus` 来自近期多篇内容的摘要，只支持口味、份量、环境、排队、服务体感和疑似推广判断。小红书的互动数是帖子信号，不是餐厅评分。

### 用餐时段 `planning.meal_options[]`

用餐时段描述“这一餐在行程中如何选择”：

```json
{
  "id": "meal-d5-lunch",
  "meal_type": "午餐",
  "time_window": "13:15–14:30",
  "previous_anchor": {"name": "莫高窟数字展示中心返程出口", "coordinates": "94.768408,40.161492"},
  "next_anchor": {"name": "敦煌酒店候选入口", "coordinates": "94.665992,40.135406"},
  "constraints": {"max_detour_minutes": 20, "max_queue_minutes": 30, "budget_per_person": "70–120元"},
  "baseline_route_id": "meal-baseline-d5-lunch",
  "candidates": [
    {"restaurant_id": "restaurant-daji-dunhuang", "snapshot_id": "restaurant-daji-20261005-lunch", "route_evaluation_id": "meal-route-d5-lunch-daji", "rank": 1},
    {"restaurant_id": "restaurant-shunzhang-dunhuang", "snapshot_id": "restaurant-shunzhang-20261005-lunch", "route_evaluation_id": "meal-route-d5-lunch-shunzhang", "rank": 2}
  ],
  "candidate_ids": ["restaurant-daji-dunhuang", "restaurant-shunzhang-dunhuang"],
  "selected_candidate_id": "restaurant-daji-dunhuang",
  "fallback_candidate_ids": ["restaurant-shunzhang-dunhuang"],
  "candidate_policy": {"status": "normal", "minimum": 2, "searched_count": 8},
  "selection_summary": "主选总绕行更少且能步行回酒店；若排队超过30分钟切换备选",
  "checked_at": "2026-09-21T12:00:00+08:00"
}
```

候选不能只用“附近”“商圈”“酒店餐厅”代替实体；如主选确实是酒店餐厅，也要建立可定位的餐厅实体。`selected_candidate_id` 必须属于 `candidate_ids`，`fallback_candidate_ids` 至少包含一个不同实体。

### 路线评估 `planning.meal_route_evaluations[]`

每餐先保存且只保存一条直达基准 `planning.meal_baseline_routes[]`。其起终点必须与餐窗前后锚点一致，并保存交通方式、路线策略、出发时刻、门到门时间、地图链接、查询时间和来源。每个候选再引用同一基准，并保存相同口径的两段地图数据：

```json
{
  "id": "meal-route-d5-lunch-daji",
  "meal_id": "meal-d5-lunch",
  "restaurant_id": "restaurant-daji-dunhuang",
  "baseline_route_id": "meal-baseline-d5-lunch",
  "comparison_basis": {"mode": "driving", "routing_policy": "fastest", "departure_at": "2026-10-05T13:15:00+08:00"},
  "from_previous": {"route_id": "route-mogao-daji", "origin": {"name": "莫高窟返程出口", "coordinates": "94.768408,40.161492"}, "destination": {"name": "达记酱驴肉黄面馆", "coordinates": "94.661114,40.137937"}, "distance_meters": 11730, "duration_minutes": 18, "door_to_door_minutes": 35, "map_url": "https://..."},
  "to_next": {"route_id": "route-daji-hotel", "origin": {"name": "达记酱驴肉黄面馆", "coordinates": "94.661114,40.137937"}, "destination": {"name": "敦煌酒店入口", "coordinates": "94.665992,40.135406"}, "distance_meters": 699, "duration_minutes": 10, "door_to_door_minutes": 15, "map_url": "https://..."},
  "total_door_to_door_minutes": 50,
  "baseline_door_to_door_minutes": 44,
  "detour_minutes": 6,
  "access": {"mode": "驾车后步行", "parking": "下客后步行回酒店"},
  "checked_at": "2026-09-21T12:00:00+08:00",
  "source_ids": []
}
```

`detour_minutes` 必须相对 `baseline_route_id` 指向的统一直达路线计算。两腿门到门时间之和必须等于候选总时间，候选总时间减基准时间必须等于绕行；两腿首尾坐标必须严格构成“上一锚点 → 餐厅 → 下一锚点”，且 mode、routing policy、departure_at 与基准一致。不能用直线距离或任意数字替代。所有保留候选都必须在数值型 `max_detour_minutes` 内。结构校验以 `schemas/meal-baseline-route.schema.json` 和 `schemas/meal-route-evaluation.schema.json` 为准。

## 来源与筛选

每个候选至少完成以下来源动作：

- 地图平台：确认同名店、POI、坐标、评分/评价量（能取得时）、电话、路线、停车和营业标记。来源记录必须保存 `kind=map|restaurant_platform`、`provider`、查询时间及本次响应中的 `provider_poi_ids[]`，餐厅实体以 `poi_source_id` 绑定该证据。
- 店铺官方或可靠平台：确认营业、预约、菜单/人均和商家图片；动态字段记录查询时间。
- 小红书等社区：主选交叉查看至少 3 篇、备选至少 2 篇近 12 个月原帖，逐条保存 note ID、标题、作者、发布时间、查询时间、原始 URL 和来源 ID，并至少覆盖 2 位作者；客观无法取得时必须标记 `status=unavailable`，记录实际查询词、失败类型、原因、手动搜索入口和复核时间，不能用降低置信度代替零证据。
- 地方文旅/可靠餐饮指南：只用于发现地方菜和老字号线索；旧价格不能当当前价格。

主 Agent 按透明维度排序，默认权重可随行程约束调整：

- 路线适配与额外绕行 35%
- 特色菜与用户偏好 20%
- 平台口碑及评价量 15%
- 社区近期共识 10%
- 营业、排队、预约和停车可执行性 15%
- 来源完整度 5%

页面必须展示各维度事实和选中理由；综合分只用于排序，不替代原始平台信号。高海拔、长途驾驶、赶车或晚到场景可以提高路线与出餐权重。

## 图片与链接

每个候选至少有一种可视证据：

- 可展示图片：用户素材、店铺官方明确允许的宣传图或许可清晰的图片，必须有 `alt`、原始页面、作者/机构、许可/允许方式和查询时间。
- 仅跳转预览：没有合法可复用图片时，提供商家官方相册、地图详情或小红书原帖链接卡，标记 `kind=link_preview`，不复制、下载或热链临时 CDN 图片。

不能用无来源菜品图、截图、渐变色块或通用美食图冒充餐厅实景。

## 公共资料库

审查通过后，餐厅可以作为 `entity_type=restaurant` 晋升公共库。只晋升慢变化字段：标准名称、别名、菜系、特色菜、地址、坐标、电话、官方/平台固定入口、许可图片元数据、无障碍/停车设施和长期饮食标签。

评分、评价数、人均、菜单价、营业时间、排队、预约余量、节假日状态、帖子互动数以及相对本次酒店/景点的距离留在单次 workspace。新行程 materialize 公共实体后必须重新获取动态覆盖和路线评估，不能把旧快照当现状。

## 完成门槛

一顿正餐只有满足以下条件才能进入 `confirmed_planning`：

- 有 2～3 个实体候选，或有来源支持的受限场景声明。
- 每个候选有可定位地址/坐标、特色菜、动态营业状态、至少一个平台详情入口和可视证据。
- 地址必须能定位到具体门牌或经营点；禁止“景区附近”“酒店周边”“unknown”等占位。中国境内高德数据使用 GCJ-02，境外地点可用 WGS84，但必须显式声明且同一组路线不得混用。`poi_id` 必须绑定 provider、核验时间和地图来源 ID；来源记录的 `provider_poi_ids[]` 必须包含同一个 ID。候选按平台 POI、标准化地址以及同名 30 米近邻去重，不能换 ID 冒充多个备选。
- 每个候选都有上一锚点到餐厅、餐厅到下一锚点的路线评估以及额外绕行。
- 评分和社区信号分平台、带查询时间；没有数字时明确未取得。
- 主选、至少一个备选和自动切换条件明确。
- 动态价格、营业、排队和预约有复核时间。
- 所有图片和社区引用满足权利与只读边界。

审查不得把“同商圈”“酒店附近”“到时再看”当作满足上述门槛。它们只能作为受限场景的最后降级，并必须附具体查询入口和随身餐/便利店等可执行备选。
