# 行程研究工作区

本文件只说明 `.travel-research/<trip-id>/` 的目录和命令。它是本次旅行唯一的研究与共享状态目录；何时拆任务、字段所有权、依赖波次与完成门槛见[子 Agent 编排](agent-orchestration.md)。

## 创建

```bash
python3 skills/travel-planning/scripts/research_workspace.py init \
  --trip-id "hangzhou-2026-10" \
  --destination "杭州" \
  --date-range "2026-10-03 至 2026-10-05" \
  --travelers "2 位成人" \
  --origin "上海" \
  --budget "中等" \
  --preferences "人文" \
  --preferences "慢节奏"
```

默认目录：

```text
.travel-research/<trip-id>/
|-- manifest.json
|-- brief.json
|-- route-proposals.json
|-- selected-route.json
|-- assignments/
|   `-- templates/
|-- results/
|-- sources/
|-- snapshots/<task_id>/
|-- evidence/main/
|-- evidence/<task_id>/
|-- state/
|   |-- research.json
|   |-- itinerary-plan.json
|   |-- sources.json
|   |-- source-snapshots.json
|   `-- archive.json
`-- artifacts/
```

不把 API Key、Cookie、账号密码、身份证件、乘车人证件、保单号、订单号或支付信息写入工作区。网页只保存本次结论、必要短摘录和原始链接；仅归档官方公开、用户授权或许可证允许的原文件。

## 路线确认

主 Agent 将路线候选写入 `route-proposals.json`。用户确认后执行：

```bash
python3 skills/travel-planning/scripts/research_workspace.py select-route \
  --workspace ".travel-research/hangzhou-2026-10" \
  --route-file "/tmp/selected-route.json"
```

深度研究 assignment 只能在 `selected-route.json` 存在后创建。

## 创建任务

```bash
python3 skills/travel-planning/scripts/research_workspace.py assign \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "route-data" \
  --domain "route-data" \
  --instructions "比较城际方案与关键门到门交通边"
```

依赖任务必须已经以 `complete` 提交：

```bash
python3 skills/travel-planning/scripts/research_workspace.py assign \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "restaurant-ranking" \
  --domain "restaurant-research" \
  --stage "restaurant_ranking" \
  --depends-on "restaurant-discovery" \
  --depends-on "route-data-meals" \
  --instructions "完成证据化比较、主备排序和切换条件"
```

assignment 固化 `input_paths`、只读 `dependency_paths`、`owned_paths`、`forbidden_paths`、字段所有权、结果模板及其摘要。子 Agent 先读这些输入，只写自己拥有的结果、来源、快照和证据；依赖变化后旧结果无法提交。

## 结果与提交

结果 JSON 从 assignment 的 `result_template` 复制，不自行发明包裹结构。`summary` 不超过 200 字；结构化内容写入 `source_snapshot_ids[]`、`entities`、`shared_entities[]`、`event_bindings[]`、`constraints[]`、`unresolved[]` 和 `source_ids[]`。只有其他 Agent、排程、审查或页面会消费的实体才放入 `shared_entities[]`；`merge` 自动汇总到 `state/research.json.global_state`。

正式飞猪或飞常准查询同时传入 `--workspace` 与已分配的 `--task-id`，让标准快照直接进入 `snapshots/<task_id>/`。提交时脚本重新校验快照、offer 引用、来源 ID、HTTPS 链接、模板摘要与输入版本。

```bash
python3 skills/travel-planning/scripts/research_workspace.py submit \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "route-data" \
  --result-file "/tmp/route-data-result.json" \
  --sources-file "/tmp/route-data-sources.json"
```

`--sources-file` 接受临时 JSON 对象或数组，提交后写成 `sources/<task_id>.jsonl`。每条来源至少包含带任务前缀的 `id`、标题、HTTPS URL、来源类型和查询时间；脚本同时生成不可覆盖的 `evidence/<task_id>/<source_id>.json`。

## 中途归档

发现后续可能引用的来源时立即归档，不依赖聊天上下文：

```bash
python3 skills/travel-planning/scripts/research_workspace.py archive \
  --workspace ".travel-research/hangzhou-2026-10" \
  --record-id "hangzhou-tourism-notices" \
  --task-id main --kind link \
  --title "杭州文旅公告入口" \
  --url "https://wgly.hangzhou.gov.cn/" \
  --source-kind official --location "杭州" --topic "文旅公告" \
  --tag hangzhou --tag official \
  --summary "用于复核大型活动和临时关闭" \
  --freshness dynamic
```

允许归档 PDF、HTML、Markdown、文本、JSON、CSV、DOCX、XLSX 和常见图片，单文件上限 25 MiB。文件入库后记录原名、大小和 SHA-256；是否删除原临时文件由调用方决定。

- `freshness=dynamic`：价格、库存、时刻、天气和临时公告，下次必须重查。
- `freshness=seasonal`：季节玩法和装备，只作相同季节候选。
- `freshness=stable`：官方入口、地理背景和长期规则，关键事实仍需复核。
## 合并与状态

```bash
python3 skills/travel-planning/scripts/research_workspace.py status \
  --workspace ".travel-research/hangzhou-2026-10"

python3 skills/travel-planning/scripts/research_workspace.py merge \
  --workspace ".travel-research/hangzhou-2026-10"
```

`merge` 默认要求所有已分配任务提交，并重新校验 assignment 身份、输入版本、结果契约、来源和快照绑定。它生成轻量的 `travel-research-state/v2` 中央状态：`tasks[]` 只保留摘要与结果路径，完整任务仍从 `results/<task_id>.json` 按需读取；来源、快照和档案分别通过 `indexes` 指向 `state/sources.json`、`state/source-snapshots.json` 和 `state/archive.json`。

`global_state.shared_entities[]` 按 `entity_id` 去重。互补对象字段自动合并，`source_ids`、别名和标签去重并集；同一字段冲突时按 `submitted_at` 较新的任务值覆盖，并在 `global_state.conflicts[]` 保留双方值、任务和处理规则，不需要人工晋升。主 Agent 另写候选行程和审查结果；只有 `blocking=[]` 才生成最终 HTML。

## 声明式装配

`merge` 后，主 Agent 将选用实体、景点执行配置、餐窗、逐日事件、预约任务和降级策略写入 `state/itinerary-plan.json`。计划使用 `itinerary-plan/v1`，并通过 `research_state_sha256` 绑定当前 `state/research.json`；Agent 只写 JSON 决策，不为目的地创建 Python。

```bash
python3 skills/travel-planning/scripts/assemble_itinerary.py \
  --workspace ".travel-research/hangzhou-2026-10" \
  --print-research-sha256

python3 skills/travel-planning/scripts/assemble_itinerary.py \
  --workspace ".travel-research/hangzhou-2026-10"
```

通用装配器从 `collections` 声明加载 `results/` 或 `state/` 中的对象，按稳定 ID 选择和绑定，生成 `artifacts/itinerary.json`。研究状态变化、选定路线不一致、实体缺失、快照冲突或事件 ID 重复都会停止装配。完整字段合同见 `schemas/itinerary-plan.schema.json`。

主 Agent 只载入合并后的必要摘要，需要证据时按 `task_id`、`source_id` 或 `record_id` 定向读取。二进制文档先看元数据和摘要，再决定是否打开。
