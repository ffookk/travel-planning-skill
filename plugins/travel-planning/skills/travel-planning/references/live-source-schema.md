# 动态交通与住宿快照

飞猪 FlyAI、飞常准 Aviation MCP 和 Tripmatch MCP 的返回先由 Provider Adapter 转换为统一的 `travel-source-snapshot/v1`，再进入研究 workspace 或 `itinerary.json`。开放式航班/铁路覆盖查询的命令输出使用 `travel-source-snapshot-batch/v1` 汇总，但其中每个结果仍是独立标准快照并分别落盘。机器可读契约位于 `schemas/travel-source-snapshot.schema.json`，行程层不得直接依赖供应商原始字段。

## 标准结构

```json
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
  "product_type": "flight",
  "tool": "search-flight",
  "query": {
    "origin": "上海",
    "destination": "北京",
    "dep_date": "2026-10-03"
  },
  "freshness": {
    "checked_at": "2026-09-20T12:00:00+08:00",
    "expires_at": "2026-09-20T12:30:00+08:00",
    "dynamic": true
  },
  "items": [],
  "count": 0,
  "raw_response_hash": "sha256:...",
  "source": {
    "title": "飞猪 FlyAI",
    "url": "https://github.com/alibaba-flyai/flyai-skill",
    "kind": "official_platform_api"
  },
  "disclaimer": "查询时的平台快照，提交订单前必须重新核验"
}
```

`items[]` 的公共字段为非空且快照内唯一的 `offer_id`、`name`、`price`、`availability` 和 `action_link`。航班/火车增加 `departure`、`arrival`、`segments[]`、`total_duration` 和允许列出的 `operational` 字段；酒店增加 `location` 和 `hotel`。供应商未提升为公共字段的数据不进入快照，避免把未知敏感字段透传到规划层。

`snapshot_kind=quote` 表示候选与价格，`operational` 表示指定航班状态/舒适度，`lookup` 表示车站等基础检索。三类共用相同来源、查询、新鲜度和错误边界。

## 状态与错误

- `platform_reported`：供应商本次返回了记录，只代表查询时状态。
- `no_results`：供应商成功响应但结果为空，不能等同于供应商故障。
- 命令失败返回独立的 `travel-source-error/v1`，机器契约位于 `schemas/travel-source-error.schema.json`，不伪装成成功快照。类型包括 `credential_missing`、`authorization_failed`、`quota_exceeded`、`runtime_unavailable`、`timeout`、`invalid_response`、`workspace_error`、`provider_error` 和 `unsupported_provider`。
- 凭证值、Cookie、授权头和临时 Token 不得出现在标准快照；原始响应不落盘，只保留 SHA-256 哈希用于追溯。

## 消费规则

1. 查询阶段把快照写入 workspace 的 `snapshots/<task_id>/<snapshot_id>.json`；Agent 结果只提交 `source_snapshot_ids[]`，主 Agent 合并后再写入 `planning.source_snapshots[]`。
2. 价格的 `amount`、`currency`、`basis` 和原始 `display` 必须一起保留；币种无法可靠识别时不能猜测。
3. 只有供应商实际返回的 HTTPS 地址才能进入 `action_link`，不得自行拼接购买深链。
4. 飞猪或飞常准的中国铁路结果是平台信息，最终车次、席别价格和余票仍在 12306 复核；境外铁路回到对应运营方官方渠道。
5. 任何查询结果都不表示已经预订、占座或锁价。
6. 交通和住宿候选使用 `inventory_refs[]` 引用，结构为 `snapshot_id`、`offer_id`、`role`。`role` 只能是 `candidate_quote`、`operational_check` 或 `station_lookup`。
7. quote 默认 30 分钟、运行状态默认 15 分钟、lookup 默认 24 小时失效。已选候选过期时审查会警告；`workflow.phase=final` 时作为阻断项。
8. 中国铁路候选仍需 `country_code=CN` 和 `rail_verification.channel=12306`。最终行程标记为 `final` 前，所选中国铁路候选必须完成 12306 复核。
9. 酒店快照的 `query.requested_occupancy` 记录本次成人数和房间数；`supplier_capacity_filter_supported=false` 表示这些条件没有被供应商库存接口强制校验。此时即使返回价格，也只能称为报价候选，不能声称多间同房型有房。
