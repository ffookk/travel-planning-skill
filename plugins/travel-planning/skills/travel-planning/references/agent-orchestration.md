# 子 Agent 编排

## 触发条件

协作能力可用且存在两个以上独立研究域时必须并行。多城市、超过 3 天、超过 8 个候选景点、涉及两种以上城际交通，或用户明确要求 Agent 派发，任一条件即触发。路线尚未确认时只可派发路线候选任务，不进行深度研究。

## 固定任务域与字段所有权

| 任务 | 独占产出 | 可引用但不可改写 |
| --- | --- | --- |
| `attractions` | `attractions[]`、实体地址/官网/预约/公告入口、适用日期运营时间、入口/出口、`execution.checkpoints[]`、节点讲解/图片/内部交通、景点费用、预约任务草案 | 路线日期、人群约束 |
| `route-data` | `source_snapshot_ids[]`、绑定具体 offer 的 `intercity_options[]` / `transport_edges[]`、车辆/包车方案、`meal_baseline_routes[]`、门到门时间、地图数据 | 景点入口出口、住宿锚点 |
| `stay-food` | 酒店 `source_snapshot_ids[]`、绑定具体 offer 的 `lodging_options[]`、住宿事件补丁、`meal_options[]` 餐窗初稿 | 每日片区、交通时间窗、checkpoint ID |
| `restaurant-research` | discovery 阶段的 `restaurants[]`、`restaurant_snapshots[]`、`meal_candidate_sets[]`；ranking 阶段的最终 `meal_options[]`；餐厅公共库候选 | 用餐时段、景点/酒店锚点、路线评估 |
| `weather-risk` | `weather[]`、固定图标代码、天气网站、`event_impacts[]`、`route_impacts[]`、天气备选 | 景点、交通和 checkpoint ID |
| `readiness` | 节假日、临时公告、行李、入境/通信/保险和分阶段复核 | 已选城际方案与住宿夜 |
| `audit` | 阻断项、警告、已检查事件 ID | 合并后的 `itinerary.json` |

子 Agent 不生成完整 `days[]`，不决定城市顺序，不修改最终 `itinerary.json`。

## 统一结果契约

所有研究结果必须从 assignment 指定的领域模板复制，并可按 ID 合并；不接受以 `data` 包住任意内容的报告。`entities` 只属于本次行程，跨行程稳定候选写入 `catalog_candidates`：

```json
{
  "task_id": "attractions",
  "schema_version": "travel-research-result/v1",
  "template_version": "复制 assignment.template_version；不同领域可不同",
  "template_digest": "复制 assignment.template_digest",
  "status": "complete",
  "input_revision": "selected-route sha256",
  "summary": "不超过200字，只写关键结论和阻塞项",
  "source_snapshot_ids": [],
  "entities": {"attractions": []},
  "catalog_candidates": [],
  "event_bindings": [
    {
      "id": "attractions-bind-chaka-lakeside",
      "day_id": "d3",
      "preferred_window": "07:50-10:20",
      "target": {"type": "checkpoint", "entity_id": "attractions-chaka", "checkpoint_id": "attractions-chaka-cp-lakeside"},
      "operation": "merge",
      "snapshot_ids": ["attractions-operations-chaka-20261003"],
      "event_patch": {},
      "source_ids": []
    }
  ],
  "constraints": [],
  "unresolved": [],
  "source_ids": []
}
```

`summary` 不进入页面。本次动态事实写入 `entities`，酒旅 Provider 快照只用 `source_snapshot_ids[]` 引用，稳定候选写入 `catalog_candidates`，对日程的影响写入 `event_bindings`，硬约束写入 `constraints`，未取得的数据写入 `unresolved`。交通和住宿候选的 `inventory_refs[]` 必须同时指定 `snapshot_id`、`offer_id` 和 `role`；有结果的 quote 快照若未投影成候选，提交会被拒绝。binding 必须有稳定 `id` 和 `snapshot_ids[]`；constraint 必须包含目标、规则与严重度；unresolved 必须包含字段、原因、下一动作、复核时间、操作入口与严重度。存在 blocking unresolved 时任务不能标记为 `complete`。`target.type` 可为 `day`、`attraction`、`transport_edge`、`meal`、`lodging`、`checkpoint` 或 `booking_task`；`operation` 只允许 `merge`、`append_reference`、`invalidate`，禁止跨字段所有权整体替换。

## 分波次调度

1. 主 Agent 搜索公共库，将选中的实体 revision 固化到 `state/library-seed.json`；再建立 assignment。每个任务读取同一 seed 和脚本复制的领域模板。
2. 第一波同时启动 `attractions`、`route-data` 第一阶段和 `stay-food`。`route-data` 先完成城际、包车/租车比较及已有明确 POI 的路线；`stay-food` 先产住宿锚点和餐窗，不提前拍脑袋选餐厅。
3. 景点出入口、住宿锚点和餐窗稳定后创建 `restaurant-discovery`（领域仍为 `restaurant-research`），每个正餐正常提交 3 个、最低 2 个可定位候选及动态快照。
4. 任一槽位释放后启动 `weather-risk`；城际方案稳定后启动 `readiness`。
5. `restaurant-discovery` 完成后创建 `route-data-meals`，依赖前者，为每个候选计算上一锚点和下一锚点的双腿路线、基准直达路线及额外绕行。随后创建 `restaurant-ranking`（领域 `restaurant-research`），同时依赖 `restaurant-discovery` 与 `route-data-meals`，完成最终比较、排序和主备切换条件。三个结果文件均不可覆盖。
6. 第一阶段景点、城际交通、住宿锚点和餐窗提交后，主 Agent先生成硬时间候选事件流并执行可行性预审；景点/用餐重叠、接驳缓冲不足、晚间活动晚于末班车或入住衔接失败时，立即重排或创建 `gap-<domain>-vN`，不能等餐厅研究和页面渲染完成后再发现。
7. 所有采集任务提交后，主 Agent合并规范化实体和事件补丁，生成完整候选 `itinerary.json`，最后单独启动 `audit`。审查失败时继续创建修补任务或修正编排，再重新审查。

槽位不足时按上述波次排队，不把所有研究退化成主 Agent 串行浏览。依赖尚未完成时只把后续任务保留在调度队列，不提前创建 assignment；`assign` 会拒绝缺少 `complete` 结果的依赖。依赖结果进入 assignment 的 `input_revision`，之后发生任何变化都会使提交失效。

## Assignment 必填内容

初始消息和 assignment 均须包含：workspace 绝对路径、`task_id`、输入路径、依赖路径、允许写入路径、禁止路径、字段所有权、完成门槛和 `submit` 命令。

```json
{
  "task_id": "route-data",
  "input_paths": ["manifest.json", "brief.json", "selected-route.json", "assignments/route-data.json"],
  "dependency_paths": ["results/attractions.json", "results/stay-food.json"],
  "owned_paths": ["results/route-data.json", "sources/route-data.jsonl", "snapshots/route-data/", "evidence/route-data/"],
  "forbidden_paths": ["state/", "artifacts/", "SKILL.md", "scripts/", "references/"],
  "source_id_prefix": "route-data-"
}
```

子 Agent 始终可读 `input_paths` 和 assignment 列出的 `dependency_paths`；后者只读，并已在创建 assignment 前完成且纳入版本摘要。

## 各任务完成门槛

### `attractions`

- 每个拟采用景点都有可定位入口、出口和坐标。
- 实体地址、官网、预约入口和公告入口分开；有适用日期的开放、停止售票、停止入场、闭园、节假日覆盖、临时公告和查询时间。
- 有基础票、必选景交、可选体验和互斥套票。
- 有入口到出口的结构化 `checkpoints[]`；节点写明时间段、类型、动作，相关时包含讲解、许可图片、内部交通、餐饮引用、操作链接和失败备选。
- 需要预约的项目生成可绑定事件的 booking task，写明目标日期/场次、人数、产品、放票规则、下次动作、截止和官方入口。
- 社区内容只用于体验、拥挤和避坑，不覆盖官方事实。

### `route-data`

- 飞猪/飞常准等已配置只读查询直接执行，不等待逐次授权；开放式航班和铁路发现使用 `flyai-flight-coverage` / `flyai-train-coverage` 覆盖最早、最晚、时长、价格和推荐排序，并将各标准快照直接写入本任务 `snapshots/`；结果只携带 `source_snapshot_ids[]`。
- 每个采用的航班、火车或空铁联运候选都用 `inventory_refs[]` 绑定具体快照和 offer；quote、运行状态和车站检索分别使用 `candidate_quote`、`operational_check`、`station_lookup`。
- 覆盖出发地到目的地、站点到住宿、住宿到首景点、景点间、末景点到住宿及返程。
- 每条边有精确起终点、门到门时间、费用、备选、实时状态和查询时间。
- 每餐有唯一 `meal_baseline_routes[]`；餐厅候选路线引用同一基准和比较口径，保存两腿端点、两腿门到门时间、候选总时间和差值；所有保留候选都不得超过必填的数值绕行上限。
- 中国境内地面交通有高德坐标、内嵌路线数据和独立 URI 链接。
- 火车/航班不虚构余票；包车写清资质、合同、车型、行李、油路停、司机食宿、超时和异地返空。

### `stay-food`

- 酒店平台查询按入住/退房日期写入本任务 `snapshots/`；每个采用的住宿候选绑定具体 hotel offer，不复制供应商私有响应。
- 每次酒店查询保存成人数、房间数、床型和连续入住夜；商圈结果只作发现，采用前用酒店全名和地图核对城市、行政区、地址、坐标及距目标锚点。供应商未按多间同房型返回库存时，只能标记报价候选和复核动作。
- 每个住宿夜有可执行候选或明确片区锚点；退房至下次入住的行李有归属。
- 每个完整旅行日有实际午餐和晚餐时间窗，写明前后事件锚点、预算、最长绕行和交通/饮食约束。
- 景区内补给通过 checkpoint 的 `meal_id` 引用；承担正餐时同时提交顶级 meal 事件绑定，避免费用重复。
- 动态房价带查询时间及复核入口。

### `restaurant-research`

- 正常正餐时段有 2～3 个不同、可定位的餐厅候选；主选和至少一个备选明确。受限场景必须提交有来源的 `candidate_policy` 例外和应急补给。
- 每个候选有准确地址、适用坐标系、POI、菜系、特色菜、平台详情链接和合规可视证据；POI 必须绑定本任务地图来源，来源的 provider/POI ID/查询时间与实体一致。
- 每个候选有适用日期的 `restaurant-source-snapshot/v1`；评分、评价量、人均、营业、排队、预约和社区共识分来源保存并带查询时间。
- 正常正餐的主选至少交叉 3 条近期社区原帖，备选至少 2 条；来源客观不可用时显式写 `status=unavailable`、原因和手动搜索入口，不能用“低置信度”掩盖零证据。社区内容不证明营业和价格。
- 每个候选引用 route-data 的双腿路线评估和额外绕行；距离未知时不能提交最终排序。
- 生成明确切换条件，不用自由文本“附近再找”充当备选。

### `weather-risk`

- 每个日期有天气状态或明确的未来复核时间。
- 天气对象提供固定 `icon_code`、气温/降水/风/紫外线/日出日落/预警、状态、查询/复核时间和实际天气网站。
- 天气影响按景点、交通或 checkpoint 绑定，并转化为缩短、取消、改时、换交通或切换备选等动作。
- 降雨、风、温度、紫外线、日出日落和预警按相关性覆盖，不输出泛化穿衣报告。

## 主 Agent 合并顺序

1. 校验任务状态、输入版本、来源 ID 和结果契约。
2. 建立 canonical entity registry。
3. 先锁定预约、航班/车次、停止入场和强时段；交通候选先按门到门硬时间过滤，再比较价格。
4. 生成景点事件和内部卡点，再插入相邻交通边；此时先运行一次时间/空间可行性预审，冲突必须重排或按“换交通方式 → 缩短次要景点 → 取消次要活动”降级。
5. 插入住宿、行李、正餐和休息事件。
6. 将天气、费用、预约按实体/事件 ID 注入。
7. 在 `state/merge-decisions.json` 记录冲突取舍和来源。
8. 运行独立审查，阻断项清零后才能渲染 HTML。
9. 最终事实审查通过后，主 Agent逐个审核 `state/catalog-candidates.json`，再以乐观版本锁晋升稳定候选；任何动态查询结果不得写回公共库。

冲突依据来源等级和更新时间解决；无法解决时明确展示差异，不暗选。主 Agent只把必要实体载入上下文，需要证据时再按 `task_id` 或 `source_id` 定向读取文件。

## 停止条件

- 登录、验证码或平台访问限制阻止查询时停止该来源，记录缺口并使用合法替代入口。
- 动态价格或库存无法核实时标记复核，不持续高频重试。
- 用户改变日期、人数、出发地或路线时，使受影响任务失效并重新派发。
