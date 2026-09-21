# 行程研究工作区

多城市、超过 3 天、候选景点较多或需要子 Agent 并行研究时，为本次行程创建独立目录。大型来源、中间数据和子 Agent 结果通过文件传递，不反复塞入主 Agent 上下文。

跨行程稳定实体不放在这里，统一存入[跨行程公共资料库](shared-travel-library.md)。本目录只保存公共实体的确定 revision 快照、本次动态查询、事件绑定、决策和最终产物。

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

默认生成：

```text
.travel-research/<trip-id>/
|-- manifest.json
|-- brief.json
|-- route-proposals.json
|-- selected-route.json        # 路线确认后生成
|-- assignments/               # 主 Agent 编写
|   `-- templates/             # 按任务复制并锁定摘要的结果模板
|-- results/                   # 每个子 Agent 只写自己的 task_id
|-- sources/                   # 每个子 Agent 独立 JSONL
|-- snapshots/                 # 飞猪/飞常准标准快照，按 task_id 隔离且不可覆盖
|   `-- <task_id>/
|-- evidence/                  # 中途链接、摘要、笔记和允许留存的文档
|   |-- main/                  # 主 Agent 的档案记录与 files/
|   `-- <task_id>/             # 子 Agent 各自拥有，避免并发覆盖
|-- state/                     # 主 Agent 合并后的共享状态
|   |-- library-seed.json      # 本次采用的公共实体 revision 快照
|   |-- source-snapshots.json # 合并后的本次动态酒旅快照
|   |-- catalog-candidates.json
|   `-- library-promotions.json
`-- artifacts/                 # itinerary.json 和 itinerary.html
```

不把 API Key、Cookie、账号密码、身份证件、乘车人证件、保单号、订单号或支付信息写入该目录。工作区默认保留作为来源和决策记录，不自动删除。网页正文不要整页复制；保存本次结论、必要短摘录和原始链接即可。只有官方公开文件、用户提供且允许保存的文件，或许可证允许留存的材料才归档原文件。

餐厅研究使用三个不可覆盖的任务文件：`restaurant-discovery`（`stage=restaurant_discovery`）保存实体、动态快照与 `meal_candidate_sets[]`；`route-data-meals`（`stage=meal_route_evaluation`）保存每餐唯一基准、各候选双腿路线与绕行；`restaurant-ranking`（`stage=restaurant_ranking`）读取前两者且只提交最终 `meal_options[]`。空结果不能标记 `complete`，三阶段候选集合必须完全一致。片区、街区和酒店附近只能作为搜索锚点，不能冒充餐厅实体。

## 路线确认

主 Agent 将路线候选写入 `route-proposals.json`。用户确认后，把所选路线对象保存为临时 JSON，再执行：

```bash
python3 skills/travel-planning/scripts/research_workspace.py select-route \
  --workspace ".travel-research/hangzhou-2026-10" \
  --route-file "/tmp/selected-route.json"
```

深度研究任务只能在 `selected-route.json` 存在后创建。

## 子 Agent 任务

主 Agent 为每个独立领域分配稳定的 `task_id`：

```bash
python3 skills/travel-planning/scripts/research_workspace.py assign \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "route-data" \
  --domain "route-data" \
  --instructions "比较铁路、航班、大巴、包车加司机及关键门到门交通边"

python3 skills/travel-planning/scripts/research_workspace.py assign \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "readiness" \
  --domain "readiness" \
  --depends-on "route-data" \
  --instructions "按 trip-readiness.md 检查行前就绪，并生成分阶段复核项"
```

依赖任务必须已经以 `status=complete` 提交，才能创建后续 assignment。例如餐饮阶段依次创建：

```bash
python3 skills/travel-planning/scripts/research_workspace.py assign --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "restaurant-discovery" --domain "restaurant-research" \
  --stage "restaurant_discovery" \
  --depends-on "attractions" --depends-on "stay-food" \
  --instructions "按餐窗搜索具体餐厅、动态平台信号、社区原帖和图片"

python3 skills/travel-planning/scripts/research_workspace.py assign --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "route-data-meals" --domain "route-data" \
  --stage "meal_route_evaluation" \
  --depends-on "restaurant-discovery" \
  --instructions "计算每个候选的双腿路线、同基准直达路线和额外绕行"

python3 skills/travel-planning/scripts/research_workspace.py assign --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "restaurant-ranking" --domain "restaurant-research" \
  --stage "restaurant_ranking" \
  --depends-on "restaurant-discovery" --depends-on "route-data-meals" \
  --instructions "按距离、评分、特色、社区证据和营业风险完成主备排序"
```

子 Agent 必须先读 assignment 的 `input_paths` 和只读 `dependency_paths`。默认输入包括：

1. `manifest.json`
2. `brief.json`
3. `selected-route.json`
4. `assignments/<task_id>.json`

子 Agent 只负责自己的结果和来源，不修改 `itinerary.json`、其他任务文件或主 Agent 状态。依赖任务结果只读，并纳入 `input_revision`；其内容变化后，当前任务结果无法提交。

## 结果格式

结果 JSON 必须从 assignment 的 `result_template` 复制；`summary` 最长 200 字，只写关键结论和阻塞项，不得提交一篇调研报告。`template_digest`、`input_revision` 或公共库 seed 变化后必须重新分配任务：

```json
{
  "task_id": "route-data",
  "schema_version": "travel-research-result/v1",
  "template_version": "复制 assignment.template_version；不同领域可不同",
  "template_digest": "assignment 中的摘要",
  "status": "complete",
  "input_revision": "selected-route sha256",
  "summary": "门到门对比结论",
  "source_snapshot_ids": ["0123456789abcdef01234567"],
  "entities": {"transport_edges": []},
  "catalog_candidates": [],
  "event_bindings": [
    {
      "id": "route-data-bind-edge-1",
      "day_id": "d2",
      "preferred_window": "08:00-10:00",
      "target": {"type": "transport_edge", "entity_id": "route-data-edge-1"},
      "operation": "merge",
      "snapshot_ids": ["route-data-edge-1"],
      "event_patch": {},
      "source_ids": ["route-data-source-1"]
    }
  ],
  "constraints": [],
  "unresolved": [],
  "source_ids": ["route-data-source-1"]
}
```

本次日期、人数和查询时点的事实写入 `entities`；飞猪/飞常准完整响应先标准化并独立保存到 `snapshots/<task_id>/`，结果只列 `source_snapshot_ids[]`。采用的交通或住宿候选用 `inventory_refs[]` 指向具体 `snapshot_id + offer_id`。跨行程稳定实体候选写入 `catalog_candidates`；对日程的影响写入 `event_bindings`；硬时间和前置条件写入 `constraints`。主 Agent不复制 `summary` 到页面，只按稳定 ID 合并结构化字段。候选必须通过公共库白名单与来源校验，且只能在最终审查通过后由主 Agent审核晋升。

所有飞猪/飞常准命令都接受 `--workspace` 与 `--task-id`。二者必须同时传入，且任务领域必须匹配产品：航班/火车/空铁联运只能写入 `route-data`，酒店只能写入 `stay-food`。例如：

```bash
python3 skills/travel-planning/scripts/research_sources.py flyai-train-coverage \
  --origin "北京南" --destination "上海虹桥" --date 2026-10-03 \
  --workspace ".travel-research/hangzhou-2026-10" --task-id route-data
```

提交时会重新校验快照结构、查询与过期时间、HTTPS 跳转、offer 唯一性以及候选引用。`merge` 将任务快照汇总到 `state/source-snapshots.json`；价格、库存、余票和运行状态始终是 `trip_only` 动态数据，不进入公共资料库。

`submit --sources-file` 接收临时 JSON 对象或数组；脚本提交后统一写成 `sources/<task_id>.jsonl`。每条至少包含带 `task_id-` 前缀的 `id` 和 `url`：

```json
[
  {
    "id": "route-data-official-1",
    "title": "承运方官方时刻页",
    "url": "https://example.com/official",
    "kind": "transport_official",
    "checked_at": "2026-09-20T18:00:00+08:00",
    "location": "杭州",
    "topic": "公共交通",
    "tags": ["hangzhou", "transport"],
    "freshness": "stable",
    "reuse_scope": "candidate_for_future"
  }
]
```

提交任务时，每条来源会自动生成不可覆盖的 `evidence/<task_id>/<source_id>.json` 档案记录。来源 ID 只能使用小写字母、数字、下划线和连字符，外部链接必须是 HTTPS。

## 中途归档

看到一个后续可能需要引用的链接时立即归档，不必等任务结束：

```bash
python3 skills/travel-planning/scripts/research_workspace.py archive \
  --workspace ".travel-research/hangzhou-2026-10" \
  --record-id "hangzhou-tourism-notices" \
  --task-id main --kind link \
  --title "杭州文旅公告入口" \
  --url "https://wgly.hangzhou.gov.cn/" \
  --source-kind official --location "杭州" --topic "文旅公告" \
  --tag hangzhou --tag official \
  --summary "用于复核大型活动、临时关闭和旅游提示" \
  --freshness dynamic --reuse-scope candidate_for_future
```

保存允许留存的官方 PDF 或用户文件：

```bash
python3 skills/travel-planning/scripts/research_workspace.py archive \
  --workspace ".travel-research/hangzhou-2026-10" \
  --record-id "west-lake-official-notice" \
  --task-id main --kind document \
  --title "西湖景区官方公告" \
  --url "https://example.gov.cn/notice.pdf" \
  --file "/tmp/notice.pdf" \
  --source-kind official --location "杭州西湖" --topic "景区公告" \
  --summary "与本次日期相关的开放调整" \
  --freshness dynamic --reuse-scope trip_only
```

支持 PDF、HTML、Markdown、文本、JSON、CSV、DOCX、XLSX 和常见图片，单文件上限 25 MiB。文件复制进 workspace 后记录原文件名、字节数和 SHA-256；原临时文件之后是否删除由调用方决定。

归档字段：

- `freshness=dynamic`：价格、库存、时刻、天气、临时公告；下次只能作线索，必须重查。
- `freshness=seasonal`：季节玩法、季节交通和装备；仅供相同季节候选，必须复核年份和日期。
- `freshness=stable`：官方入口、地理背景、长期规则；可复用为背景或查询入口，关键事实仍需复核。
- `reuse_scope=trip_only`：默认，仅服务本次行程。
- `reuse_scope=candidate_for_future`：允许在后续行程检索中出现；不代表内容仍然有效。

## 跨行程借鉴

创建新行程前可检索 `.travel-research` 下历史 workspace：

```bash
python3 skills/travel-planning/scripts/research_workspace.py search-archive \
  --root ".travel-research" \
  --query "杭州 公共交通"

python3 skills/travel-planning/scripts/research_workspace.py search-archive \
  --root ".travel-research" \
  --location "杭州" --tag official
```

默认只返回 `candidate_for_future`。只有审计本次历史过程时才加 `--include-trip-only`。搜索结果带原行程、原日期、来源路径和 `reuse_guidance`；任何命中项都先作为候选，动态内容重新查询后才能进入新行程。

assignment 同时给出 `owned_paths`、`forbidden_paths` 和 `source_id_prefix`。子 Agent 只能写入所有权清单中的路径；提交时脚本原子写入独立文件，已存在的任务结果不会被覆盖：

```bash
python3 skills/travel-planning/scripts/research_workspace.py submit \
  --workspace ".travel-research/hangzhou-2026-10" \
  --task-id "route-data" \
  --result-file "/tmp/route-data-result.json" \
  --sources-file "/tmp/route-data-sources.json"
```

## 合并与状态

```bash
python3 skills/travel-planning/scripts/research_workspace.py status \
  --workspace ".travel-research/hangzhou-2026-10"

python3 skills/travel-planning/scripts/research_workspace.py merge \
  --workspace ".travel-research/hangzhou-2026-10"
```

`merge` 默认要求所有已分配任务提交，检查来源 ID 冲突，然后生成：

- `state/research.json`
- `state/sources.json`
- `state/archive.json`

主 Agent 在实体合并后另写 `state/merge-decisions.json`，记录字段冲突的采用值、理由和来源；候选日程生成后写入 `artifacts/itinerary.json`。最终审查结果写入 `state/audit.json`，只有 `blocking=[]` 才生成 `artifacts/itinerary.html`。

主 Agent 只把合并后的必要摘要载入上下文，需要核对某项结论时再按 `task_id`、`source_id` 或档案 `record_id` 定向读取。二进制文档不直接载入上下文，先根据元数据和摘要判断是否需要读取。
