# 飞常准 MCP 工具路由

当前插件固定 Aviation `@variflight-ai/variflight-mcp@1.0.3` 与 Tripmatch `@variflight-ai/tripmatch-mcp@0.0.5`。以下名称来自这两个版本的实时 `tools/list`。

## Aviation

| 意图 | 工具 | 关键输入 |
| --- | --- | --- |
| 按出发地、到达地和日期查直飞 | `searchFlightsByDepArr` | `date`；城市使用 `depcity/arrcity`，机场使用 `dep/arr` |
| 按航班号核验 | `searchFlightsByNumber` | `fnum`、`date`；可选 `dep/arr` |
| 查中转航班 | `getFlightTransferInfo` | `depcity`、`arrcity`、`depdate` |
| 舒适度、准点和机上服务 | `flightHappinessIndex` | `fnum`、`date` |
| 飞机实时位置 | `getRealtimeLocationByAnum` | 已知注册号 `anum` |
| 机场未来三日天气 | `getFutureWeatherByAirport` | 机场码 `airport` |
| 推荐航班摘要 | `searchFlightItineraries` | `depCityCode`、`arrCityCode`、`depDate` |
| 城市间舱位价格 | `getFlightPriceByCities` | `dep_city`、`arr_city`、`dep_date` |

## Tripmatch

| 意图 | 工具 | 关键输入 |
| --- | --- | --- |
| 空铁联运 | `getFlightAndTrainTransferInfo` | `depcity`、`arrcity`、`depdate` |
| 城市级火车覆盖 | `searchTrainTicketsByCity` | 中文城市名 `from/to`、`date` |
| 精确车站间火车 | `searchTrainTicketsByStation` | 精确中文站名 `from/to`、`date` |
| 搜索车站标准名 | `searchTrainStations` | `query` |

Tripmatch 也暴露若干航班工具。航班单项查询优先 Aviation；Tripmatch 的重复工具仅在同一次空铁联运研究确有必要时使用。

## 日期与代码

- `getTodayDate` 返回供应商本地时区的当天日期，只用于解析“今天”等相对表达。
- `BJS` 是北京城市码，`PEK`/`PKX` 是具体机场码；类似场景依此区分。
- 城市价格工具不接受机场码，站级铁路工具不接受模糊城市意图。

官方来源：<https://github.com/variflight/variflight-mcp>、<https://github.com/variflight/tripmatch-mcp>
