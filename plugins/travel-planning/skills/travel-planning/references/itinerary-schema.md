# 行程数据结构

使用 UTF-8 编码的 JSON。渲染器接受以下结构：

```json
{
  "trip": {
    "title": "京都慢游 4 日",
    "subtitle": "寺院、散步与小店",
    "destination": "日本京都",
    "date_range": "2026-10-03 — 2026-10-06",
    "travelers": "2 位成人",
    "budget": "中等",
    "currency": "JPY",
    "updated_at": "2026-09-20",
    "assumptions": ["以京都站附近住宿为基点"]
  },
  "workflow": {
    "phase": "confirmed_planning",
    "selected_route_id": "proposal-1",
    "confirmed_at": "2026-09-20T10:00:00+08:00",
    "pending_confirmations": ["酒店片区", "高铁具体车次"]
  },
  "route_proposals": [
    {
      "id": "proposal-1",
      "title": "经典舒适路线",
      "cities": ["京都"],
      "day_allocation": [{"place": "京都", "days": 4}],
      "highlights": ["东山寺院", "岚山散步"],
      "intercity_mode": "高铁",
      "pace": "适中",
      "rough_budget": "约 ¥6000–9000/人（估算）",
      "risks": ["红叶季住宿价格较高"],
      "status": "confirmed"
    }
  ],
  "planning": {
    "route_strategy": "先游东山北部，再向南步行，日落前到达清水寺",
    "inventory_contract_version": 1,
    "source_snapshots": [
      {
        "schema_version": "travel-source-snapshot/v1",
        "snapshot_id": "0123456789abcdef01234567",
        "snapshot_kind": "quote",
        "status": "platform_reported",
        "provider": {
          "id": "fliggy_flyai",
          "name": "飞猪 FlyAI",
          "authority": "official_platform",
          "transport": "cli_to_vendor_mcp_api",
          "package": "@fly-ai/flyai-cli",
          "version": "1.0.16"
        },
        "product_type": "train",
        "tool": "search-train",
        "query": {"origin": "东京", "destination": "京都", "dep_date": "2026-10-03"},
        "freshness": {"checked_at": "2026-09-20T10:00:00+08:00", "expires_at": "2026-09-20T10:30:00+08:00", "dynamic": true},
        "items": [{"offer_id": "train-offer-1", "name": "列车候选", "price": {"amount": null, "currency": null, "display": null, "basis": "provider_reported"}, "availability": {"status": "provider_returned", "remaining": null}, "action_link": null}],
        "count": 1,
        "raw_response_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "source": {"title": "飞猪 FlyAI", "url": "https://github.com/alibaba-flyai/flyai-skill", "kind": "official_platform_api"},
        "disclaimer": "查询时的平台快照，提交订单前必须重新核验"
      }
    ],
    "readiness": [
      {
        "id": "ready-1",
        "category": "节假日与活动",
        "status": "to_recheck",
        "summary": "检查旅行日期是否撞上地方节庆、每周闭馆或季节停运",
        "deadline": "出发前 14 天",
        "checked_at": "2026-09-20",
        "source_ids": ["s1"],
        "action_links": [
          {"type": "official", "label": "复核京都 2026-10-03 至 10-06 官方活动与关闭公告", "provider": "京都官方旅游网站", "url": "https://kyoto.travel/", "checked_at": "2026-09-20", "disclaimer": "核对地方活动、交通影响与临时关闭"}
        ]
      }
    ],
    "attractions": [
      {
        "id": "a1",
        "name": "清水寺",
        "area": "东山",
        "address": "可定位地址",
        "seasonal_highlights": ["秋季红叶", "傍晚山景"],
        "best_time": "日落前 2 小时",
        "best_time_reason": "兼顾白天游览、夕阳和下山交通",
        "visit_duration": "约 2 小时",
        "activities": [
          {
            "name": "本堂及舞台参观",
            "fee_type": "included",
            "price": "包含在基础门票中",
            "reservation": "通常无需分时预约",
            "required": true
          },
          {
            "name": "夜间特别参拜",
            "fee_type": "paid_optional",
            "price": "以当季公告为准",
            "reservation": "需确认开放日期",
            "required": false
          }
        ],
        "entrance": {
          "name": "仁王门",
          "reason": "主要入口，公共交通和步行导航信息完整",
          "exit": "仁王门",
          "location_query": "清水寺 仁王门"
        },
        "accessibility": "有坡道和台阶",
        "weather_limits": "雨天石板路湿滑",
        "confidence": "high",
        "source_ids": ["s1", "s2"]
      }
    ],
    "transport_edges": [
      {
        "id": "r1",
        "from": "京都站中央口",
        "to": "清水寺仁王门",
        "mode": "公交 + 步行",
        "route": "市营公交至清水道，再步行上坡",
        "service_or_train": "以出行当天实时线路为准",
        "departure_window": "08:30–09:00",
        "ride_duration": "约 20 分钟",
        "door_to_door_duration": "约 40–55 分钟",
        "walking_distance": "约 1 公里",
        "cost": "约 ¥230/人（估算）",
        "booking_channel": "交通卡或现场支付",
        "last_service_constraint": "不适用",
        "recommended": true,
        "reason": "比全程步行省力，避免核心区停车问题",
        "fallback": "打车至五条坂后步行",
        "live_status": "出发前复核",
        "map_route": {
          "origin": "135.758766,34.985849",
          "destination": "135.778553,34.994856",
          "mode": "bus",
          "assumption": "起终点为已核验 POI；出发时按实时交通复核"
        },
        "action_links": [
          {
            "type": "map",
            "label": "在地图查看完整路线",
            "provider": "地图平台",
            "url": "https://example.com/verified-route",
            "checked_at": "2026-09-20",
            "disclaimer": "出发时按实时导航复核"
          }
        ],
        "source_ids": ["s3"]
      }
    ],
    "intercity_options": [
      {
        "id": "ic1",
        "from": "东京",
        "to": "京都",
        "mode": "高铁",
        "departure_station": "东京站",
        "arrival_station": "京都站",
        "service_or_train": "具体车次以 12306 或当地铁路官方渠道为准",
        "departure_time": "待查询",
        "arrival_time": "待查询",
        "door_to_door_duration": "约 3.5–4.5 小时（估算）",
        "fare": "待查询",
        "availability": "不得推断余票",
        "departure_timezone": "Asia/Tokyo",
        "arrival_timezone": "Asia/Tokyo",
        "baggage_allowance": "预订前按承运方规则核对",
        "separate_ticket": false,
        "self_transfer_requirements": "不适用",
        "booking_channel": "铁路官方渠道",
        "buffer": "至少提前 45 分钟到站",
        "fallback": "航班或夜间巴士",
        "inventory_refs": [
          {"snapshot_id": "0123456789abcdef01234567", "offer_id": "train-offer-1", "role": "candidate_quote"}
        ],
        "source_ids": ["s4"]
      }
    ],
    "excluded_attractions": [
      {"name": "示例景点", "reason": "位置偏远，会造成明显折返"}
    ],
    "lodging_options": [
      {
        "id": "h1",
        "name": "京都站附近住宿候选",
        "area": "京都站",
        "check_in": "2026-10-03",
        "check_out": "2026-10-06",
        "price": "约 ¥700–1200/晚（估算）",
        "luggage_storage": "预订前确认",
        "why_here": "城际到达和返程方便",
        "travel_times": ["到京都站步行约 10 分钟"],
        "action_links": [
          {"type": "hotel", "label": "查看住宿候选", "provider": "携程", "url": "https://www.ctrip.com/", "checked_at": "2026-09-20", "disclaimer": "房态和最终价格以平台为准"}
        ]
      }
    ],
    "restaurant_research_version": 3,
    "restaurants": [
      {
        "id": "restaurant-yudofu-a",
        "name": "东山汤豆腐候选 A",
        "cuisine": ["京都料理"],
        "location": {"physical_address": "可定位地址", "coordinates": "135.778,34.995", "coordinate_system": "WGS84", "poi_id": "map-poi-id"},
        "signature_dishes": ["汤豆腐"],
        "media": [{"kind": "link_preview", "source_url": "https://example.com/restaurant-a", "alt": "查看餐厅官方相册", "source_label": "餐厅官方"}],
        "action_links": [{"type": "restaurant", "label": "查看餐厅 A", "provider": "餐厅官方", "url": "https://example.com/restaurant-a"}],
        "source_ids": ["restaurant-a-official"]
      }
    ],
    "restaurant_snapshots": [
      {
        "schema_version": "restaurant-source-snapshot/v1",
        "snapshot_id": "restaurant-yudofu-a-20261003-lunch",
        "restaurant_id": "restaurant-yudofu-a",
        "applicable_date": "2026-10-03",
        "time_window": "12:20–13:20",
        "status": "platform_reported",
        "platform_signals": [{"platform": "map", "rating": "4.5", "scale": "5", "review_count": 320, "per_person": "约 ¥1000–2000", "status": "platform_reported", "checked_at": "2026-09-20", "source_ids": ["restaurant-a-map"]}],
        "community_consensus": {"platform": "xiaohongshu", "notes_considered": 3, "recent_note_count": 3, "positive": ["汤豆腐"], "negative": ["午市排队"], "promotion_risk": "medium", "confidence": "medium", "checked_at": "2026-09-20", "references": []},
        "operations": {"opening_hours": "午市营业", "reservation": "待店铺确认", "queue": "超过20分钟切换备选", "parking": "步行到达", "status": "platform_reported", "checked_at": "2026-09-20", "recheck_at": "2026-10-03T11:30:00+09:00"},
        "checked_at": "2026-09-20",
        "expires_at": "2026-10-03T11:30:00+09:00",
        "action_links": [{"type": "restaurant", "label": "复核餐厅 A", "provider": "地图平台", "url": "https://example.com/restaurant-a-map"}],
        "source_ids": ["restaurant-a-map"]
      }
    ],
    "meal_route_evaluations": [
      {"id": "meal-route-m1-a", "meal_id": "m1", "restaurant_id": "restaurant-yudofu-a", "from_previous": {"distance_meters": 600, "duration_minutes": 9, "door_to_door_minutes": 12, "map_url": "https://uri.amap.com/navigation?..."}, "to_next": {"distance_meters": 900, "duration_minutes": 13, "door_to_door_minutes": 16, "map_url": "https://uri.amap.com/navigation?..."}, "total_door_to_door_minutes": 28, "baseline_door_to_door_minutes": 24, "detour_minutes": 4, "checked_at": "2026-09-20", "source_ids": ["map-route-a"]},
      {"id": "meal-route-m1-b", "meal_id": "m1", "restaurant_id": "restaurant-yudofu-b", "from_previous": {"distance_meters": 700, "duration_minutes": 10, "door_to_door_minutes": 13, "map_url": "https://uri.amap.com/navigation?..."}, "to_next": {"distance_meters": 850, "duration_minutes": 12, "door_to_door_minutes": 15, "map_url": "https://uri.amap.com/navigation?..."}, "total_door_to_door_minutes": 28, "baseline_door_to_door_minutes": 24, "detour_minutes": 4, "checked_at": "2026-09-20", "source_ids": ["map-route-b"]}
    ],
    "meal_options": [
      {"id": "m1", "meal_type": "午餐", "time_window": "12:20–13:20", "previous_anchor": {"name": "清水寺出口", "coordinates": "135.778,34.995"}, "next_anchor": {"name": "祇园入口", "coordinates": "135.775,35.003"}, "constraints": {"max_detour_minutes": 15, "max_queue_minutes": 20, "budget_per_person": "¥1000–2000"}, "candidate_ids": ["restaurant-yudofu-a", "restaurant-yudofu-b"], "selected_candidate_id": "restaurant-yudofu-a", "fallback_candidate_ids": ["restaurant-yudofu-b"], "candidates": [{"restaurant_id": "restaurant-yudofu-a", "snapshot_id": "restaurant-yudofu-a-20261003-lunch", "route_evaluation_id": "meal-route-m1-a", "rank": 1}, {"restaurant_id": "restaurant-yudofu-b", "snapshot_id": "restaurant-yudofu-b-20261003-lunch", "route_evaluation_id": "meal-route-m1-b", "rank": 2}], "candidate_policy": {"status": "normal", "minimum": 2, "searched_count": 6}, "selection_summary": "两家均顺路；主选额外绕行更少", "fallback_rule": "主选排队超过20分钟切换备选", "checked_at": "2026-09-20"}
    ],
    "weather": [
      {"id": "wx-d1-higashiyama", "date": "2026-10-03", "location": "京都东山", "basis": "历史气候", "icon_code": "partly_cloudy", "summary": "精确预报待出发前 7 天查询", "temperature": "待查询", "sunrise": "待查询", "sunset": "待查询", "status": "to_recheck", "checked_at": "2026-09-20", "action_links": [{"type": "weather", "label": "查看京都天气", "provider": "天气服务", "url": "https://example.com/kyoto-weather", "checked_at": "2026-09-20", "disclaimer": "出发前48小时复核"}]}
    ],
    "budget": {
      "currency": "JPY",
      "items": [
        {"category": "住宿", "per_person": "约 ¥1050–1800（估算）", "group": "约 ¥2100–3600（估算）", "status": "estimated"}
      ],
      "total_per_person": "待选定住宿和车次后计算",
      "excludes": ["个人购物"]
    },
    "booking_tasks": [
      {"id": "b1", "title": "确认并购买高铁票", "deadline": "开售后尽快", "priority": "book_when_open", "status": "pending", "action_links": [{"type": "train", "label": "打开铁路官方查询入口", "provider": "铁路运营方", "url": "https://global.jr-central.co.jp/en/", "checked_at": "2026-09-20", "disclaimer": "车次、席位和票价以查询时为准"}]}
    ],
    "alternatives": [
      {"trigger": "持续降雨", "replace_event_ids": [], "plan": "将户外步行替换为博物馆或室内文化设施"}
    ]
  },
  "days": [
    {
      "date": "2026-10-03",
      "label": "D1 · 周六",
      "title": "东山初见",
      "summary": "清水寺到祇园的步行线",
      "weather": "出发前 48 小时复查",
      "events": [
        {
          "id": "e-d1-r1",
          "time": "09:00",
          "end_time": "10:10",
          "type": "transport",
          "route_id": "r1",
          "title": "京都站 → 清水道",
          "subtitle": "公交 + 步行",
          "duration": "约 35 分钟",
          "area": "东山",
          "cost": "约 ¥230/人（估算）",
          "reservation": "无需预约",
          "details": ["避开早高峰后出发", "下车后步行约 12 分钟"],
          "tips": ["携带零钱或交通卡"],
          "images": [{"url": "https://example.com/photo.jpg", "alt": "东山街景"}],
          "map_url": "https://maps.google.com/",
          "action_links": [
            {"type": "map", "label": "导航到仁王门", "provider": "地图", "url": "https://maps.google.com/", "checked_at": "2026-09-20", "disclaimer": "路线以出发时实时导航为准"}
          ],
          "source_ids": ["s1"]
        },
        {
          "id": "e-d1-a1",
          "time": "10:15",
          "end_time": "12:15",
          "type": "attraction",
          "attraction_id": "a1",
          "title": "清水寺",
          "subtitle": "从仁王门进入，按本堂—舞台—音羽瀑布游览",
          "duration": "约 2 小时",
          "area": "东山",
          "cost": "基础门票及二次付费项目分开记录",
          "reservation_required": false,
          "weather_id": "wx-d1-higashiyama",
          "admission": {
            "opening_hours": "08:00–18:00",
            "last_entry": "17:30",
            "reservation_method": "普通日通常无需分时预约；特别参拜按公告",
            "entry_requirement": "仁王门进入，现场购票/核验",
            "notice": "出发前复核当季特别参拜和临时关闭公告"
          },
          "transport_mode": "公交 + 步行",
          "execution": {
            "entry": {"name": "仁王门", "location_query": "清水寺 仁王门", "reason": "主要入口且导航信息完整"},
            "exit": {"name": "仁王门", "location_query": "清水寺 仁王门"},
            "checkpoints": [
              {"id": "cp-niomon", "order": 1, "time": "10:15", "end_time": "10:30", "name": "仁王门", "kind": "entry", "required": true, "instruction": "从主入口进入并核对当日公告", "narration": "观察仁王门及入口轴线", "move_from_previous": {"mode": "步行", "duration": "约 12 分钟"}},
              {"id": "cp-hondo", "order": 2, "time": "10:30", "end_time": "11:45", "name": "本堂与舞台", "kind": "visit", "required": true, "instruction": "完成本堂和舞台主线参观", "narration": "关注木构舞台与山谷视线", "move_from_previous": {"mode": "步行", "duration": "以现场单向流线为准"}},
              {"id": "cp-exit", "order": 3, "time": "11:45", "end_time": "12:15", "name": "仁王门出口", "kind": "exit", "required": true, "instruction": "从主入口区域离开并衔接午餐"}
            ],
            "leave_by": "12:15",
            "fallback": "雨天跳过湿滑支路，保留本堂主线"
          },
          "cost_items": [
            {
              "name": "基础门票",
              "kind": "base_ticket",
              "unit_price": "500日元/人",
              "quantity": "2人",
              "subtotal": "1000日元/2人",
              "pricing_role": "baseline",
              "required": true,
              "status": "official_confirmed",
              "source_ids": ["s1"]
            },
            {
              "name": "夜间特别参拜",
              "kind": "optional_experience",
              "unit_price": "当季公告为准",
              "quantity": "0",
              "subtotal": "未计入基线",
              "pricing_role": "optional",
              "required": false,
              "status": "to_recheck",
              "source_ids": ["s1"]
            }
          ],
          "cost_summary": "基线1000日元/2人；可选项目未计入",
          "source_ids": ["s1", "s2"]
        },
        {
          "id": "e-d1-m1",
          "time": "12:20",
          "end_time": "13:20",
          "type": "meal",
          "meal_id": "m1",
          "title": "东山顺路午餐",
          "subtitle": "沿下一段步行方向就餐，不折返"
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "s1",
      "title": "京都市交通局",
      "url": "https://www2.city.kyoto.lg.jp/kotsu/",
      "checked_at": "2026-09-20",
      "note": "交通规则与票价"
    }
  ],
  "claims": [
    {
      "entity_id": "a1",
      "field": "best_time",
      "value": "日落前 2 小时",
      "source_ids": ["s1", "s2"],
      "checked_at": "2026-09-20",
      "confidence": "medium",
      "status": "community_consensus",
      "conflict_note": "夜间特别参拜仅在特定日期开放"
    }
  ]
}
```

## 字段规则

- 必填字段：`trip.title`、`days[]`、`day.date`、`day.events[]`、`event.id`、`event.time`、`event.type`、`event.title`。`confirmed_planning` 和 `final` 阶段的事件 ID 必须唯一。
- 详细规划时必须提供 `planning.attractions[]` 和 `planning.transport_edges[]`。跨城旅行还必须提供 `planning.intercity_options[]`。
- 详细规划必须提供 `planning.readiness[]`；按[行前就绪检查](trip-readiness.md)写入适用项，不适用项用 `not_applicable` 明确说明。
- `workflow.phase` 使用 `proposal`、`awaiting_confirmation`、`confirmed_planning` 或 `final`。路线未确认时不得生成标记为 `final` 的完整日程。
- 飞猪、飞常准等动态交通与住宿查询使用 `planning.source_snapshots[]` 保存 [`travel-source-snapshot/v1`](live-source-schema.md)，并设置 `planning.inventory_contract_version=1`。相关交通和住宿对象通过 `inventory_refs[]` 的 `snapshot_id + offer_id + role` 精确关联；不得把供应商私有响应当作行程数据契约。中国铁路候选还必须提供 `rail_verification`，最终阶段要求 `channel=12306` 且 `status=verified`；境外铁路使用对应运营方官方渠道。
- `route_proposals[]` 保存路线候选与状态；深度调研只能使用 `selected_route_id` 指向的已确认方案。
- 进入日程的景点事件必须通过 `attraction_id` 引用景点研究记录；交通事件必须通过 `route_id` 引用交通边。跨城交通可引用 `intercity_options[].id`。
- `best_time` 必须包含明确时段；`best_time_reason` 必须写出季节、光线、客流、演出、开放时间或返程交通等实际依据。
- `activities[].fee_type` 使用 `free`、`included`、`paid_required`、`paid_optional` 之一；不要把基础门票与景区二次消费合并成一个模糊总价。
- 进入日程的景点事件必须提供 `cost_items[]`，至少包含 `kind=base_ticket`。`kind` 使用 `base_ticket`、`required_transport`、`optional_experience`、`package`、`transport`、`lodging`、`meal` 或 `other`。
- `cost_items[]` 必须提供 `unit_price`、`quantity`、`subtotal`、`pricing_role`、`required`、`status` 和 `source_ids`。`pricing_role` 使用 `baseline`、`optional` 或 `alternative`；`status` 使用 `official_confirmed`、`platform_reported`、`estimated`、`to_recheck` 或 `free`。
- 套票使用 `kind=package` 和 `pricing_role=alternative`；同一组单票与套票不能同时计入 `baseline`。`cost_summary` 说明当前2人/全体基线以及未计入的可选项。
- 景点事件必须提供结构化 `admission`，分别记录 `opening_hours`、`last_entry`、`reservation_method`、`entry_requirement` 和 `notice`。被日程引用的景点实体必须提供 `official.physical_address`、`official.homepage_url`、`official.notice_url` 和 `official.checked_at`；需要预约时还必须有 `official.booking_url`，无需预约且无购票页时显式写 `official.booking_status=not_applicable`。不要把这些信息混进 `opening_status` 或 `reservation` 自由文本。
- 景点事件必须提供 `execution.entry`、`execution.exit` 和 `execution.checkpoints[]`。入口含 `name`、`location_query`、`reason`；出口含 `name`、`location_query`。每个 checkpoint 至少含 `id`、`order`、`time`、`end_time`、`kind`、`name`、`required`、`instruction`；按需要补 `narration`、`images[]`、`move_from_previous`、`meal_id`、内部交通、操作链接和 `fallback`。`kind` 使用 `entry`、`ticket_check`、`visit`、`experience`、`internal_transport`、`meal`、`rest`、`photo` 或 `exit`。`visit_order` 只用于旧数据摘要，不能代替执行结构。
- 景点级且必须在出发前完成的装备或证件要求写入 `preparation[]` 并靠近开放预约区展示；现场动作、避坑与天气备选必须写入对应 checkpoint，不能继续堆到 `details[]`、`tips[]` 形成卡尾汇报。
- 景点事件通过 `weather_id` 引用 `planning.weather[]`。天气对象必须含固定 `icon_code`、摘要、状态、查询时间和 `type=weather` 的用户查看入口；`icon_code` 使用 `clear_day`、`clear_night`、`partly_cloudy`、`cloudy`、`fog`、`drizzle`、`rain`、`heavy_rain`、`snow`、`thunderstorm`、`wind`、`dust`、`warning` 或 `unknown`。事件正文不再单列天气事实，改变动作的影响写入 checkpoint 备选。
- 景点事件用 `reservation_required` 明确是否需要预约。为 `true` 时必须提供 `booking_task_ids[]`；对应 booking task 必须用 `event_id` 和 `attraction_id` 双重绑定，并包含目标日期/场次、人数、产品、状态、放票时间或规则、下一次操作、截止、具体动作和官方 `action_links[]`。
- 页面预算必须从事件 `cost_items[]` 派生，不得把 `planning.budget.items[]` 当作另一套真值。保留聚合预算时应注明生成时间和派生范围。
- `entrance` 必须包含推荐入口名称、选择理由和可用于导航的定位词；有多个入口时说明为何不选其他入口。
- `transport_edges[]` 记录出口到入口的门到门路线。`ride_duration` 是乘车时间，`door_to_door_duration` 包含等待、换乘和步行，两者不可混用。
- `transport_edges[].mode` 和 `intercity_options[].mode` 可使用“包车＋司机”或“包车＋司导”。该类方案增加 `vehicle_type`、`seat_capacity`、`luggage_capacity`、`pricing_basis`、`quoted_price`、`included_costs`、`excluded_costs`、`service_hours`、`overtime_fee`、`pickup_dropoff`、`provider`、`qualification_status`、`insurance_status`、`cancellation_terms` 和 `emergency_contact_status`。
- 包车报价必须明确按车还是按人，并区分油费、路桥、停车、司机食宿、异地返程和超时费；未取得书面报价或资质/保险确认时使用 `to_recheck`。
- 火车/高铁数据记录出发站、到达站、车次、出发/到达时间、票价、余票状态、购票渠道和进站缓冲；无法实时获取的字段写“待查询”或“待复核”，不得猜测。
- 长途大巴数据记录客运站全名、承运方、班次、上车点、下车点、行李规则和查询平台，并尽量补充官方复核来源。
- 航班增加当地出发/到达日期与时区、机场/航站楼、票价是否含税及按人/全体、手提与托运行李额度/费用、是否分开出票、是否自行提取和重新托运、退改规则。分开出票时必须同时核对过境入境要求。
- 事件类型只允许：`attraction`（景点）、`transport`（交通）、`meal`（餐饮）、`lodging`（住宿）、`rest`（休息）、`note`（提示）。
- `details`、`tips`、`images`、`sources` 以及其他展示元数据均为可选字段。
- 日期尽量使用 ISO 格式；时间均为目的地当地时间。
- 可能变化的事实需要通过一个或多个 `source_ids` 引用来源。估算值中必须明确包含“估算”“预计”“约”等标识。
- `sources[].kind` 建议使用 `official`、`transport_official`、`booking_platform`、`community` 或 `map`；社区内容只支持体验判断，不能单独证明营业时间、价格或交通规则。
- 重要动态字段通过 `claims[]` 记录字段级证据；`status` 使用 `verified`、`platform_reported`、`community_consensus`、`estimated` 或 `to_recheck`。
- `readiness[].status` 使用 `verified`、`platform_reported`、`estimated`、`to_recheck` 或 `not_applicable`；`to_recheck` 必须提供至少一个可执行的 HTTPS `action_links[]`。
- `booking_tasks[].priority` 使用 `book_now`、`book_when_open`、`recheck_later` 或 `optional`。`book_now` 和 `book_when_open` 必须提供可执行 HTTPS 入口；相对期限换算为实际日期或明确触发条件。
- 住宿事件通过 `lodging_id` 引用 `lodging_options[]`；餐饮事件通过 `meal_id` 引用 `meal_options[]`。餐厅研究采用[餐厅候选研究与路线适配](restaurant-research.md)的四层结构：`restaurants[]` 保存稳定身份，`restaurant_snapshots[]` 保存评分/评价量/人均/营业/排队/社区共识等本次动态覆盖，`meal_baseline_routes[]` 保存每餐唯一的同口径直达基准，`meal_route_evaluations[]` 保存每个候选的双腿路线与额外绕行。
- 正常正餐的 `meal_options[]` 必须包含 2～3 个真实去重的 `candidate_ids[]`、`selected_candidate_id`、至少一个 `fallback_candidate_ids[]`、逐候选 `snapshot_id`/`route_evaluation_id`、`baseline_route_id`、前后锚点、数值型最大绕行、选择理由和切换规则。受限场景少于 2 个候选时使用 `candidate_policy.status=constrained`，并提供有来源的限制原因与应急补给。
- 餐厅评分按平台分开记录，必须带量表、评价量（平台提供时）、查询时间和来源；不得把平台评分与小红书互动数合成一个评分。餐厅动态快照遵循 `schemas/restaurant-source-snapshot.schema.json`。
- 每个餐厅候选至少提供一项合法可视证据：可展示图片必须有作者/机构、许可/允许方式和原始页面；否则使用 `kind=link_preview` 的官方相册、地图详情或社区原帖链接，不复制或热链临时社区图片。
- `action_links[]` 的 `type` 使用 `map`、`official`、`official_homepage`、`official_notice`、`official_booking`、`weather`、`weather_warning`、`ticket`、`train`、`bus`、`hotel`、`restaurant`、`guide`、`image_source` 或 `source`。必须使用 HTTPS，包含平台名和提示，不允许脚本自行拼接购买链接。
- 动态声明标记为 `to_recheck` 时，相关对象必须至少提供一个可手动查询的 `action_links[]`。其 `label` 应包含目的地、日期、车站或其他关键查询条件，`disclaimer` 说明待核对字段和建议复核时间；不得只链接不相关首页。
- `budget.items[].status` 使用 `confirmed`、`estimated` 或 `optional`，总价必须说明按人还是按全体以及未计入项。
- 图片替代文本应准确描述图片内容，不要直接使用文件名。
- checkpoint 图片除 `url`、`alt` 外还要有作者/机构、许可、`source_url` 和查询时间；图片主题必须对应当前节点。
- 大尺寸照片不要使用 Data URL，否则会导致页面难以分享。
