# 高德 MCP 工具路由

当前插件固定 `@amap/amap-maps-mcp-server@0.0.8`。以下名称来自该版本的实时 `tools/list`。

## 地点与坐标

| 意图 | 工具 | 关键参数 |
| --- | --- | --- |
| 地址或地标转坐标 | `maps_geo` | `address`，可选 `city` |
| 坐标转行政地址 | `maps_regeocode` | `location` |
| 城市内关键词搜索 | `maps_text_search` | `keywords`，可选 `city`、`types` |
| 坐标周边搜索 | `maps_around_search` | `location`，可选 `keywords`、`radius` |
| POI 详情 | `maps_search_detail` | 前序搜索返回的 `id` |

地点名称可能重名。搜索结果用于发现候选，采用前应以 POI ID、地址和城市确认实体；路线端点使用确认后的坐标。

### 附近餐厅

1. 用已核验用餐锚点的 GCJ-02 坐标调用 `maps_around_search(location, keywords, radius)`；`keywords` 可使用“餐厅”或具体菜系。
2. 周边结果只作为候选池。对保留候选调用 `maps_search_detail(id)`，取得精确坐标、地址、营业、人均和平台展示评分。
3. 当前 MCP 周边工具未暴露 `sortrule`，不得根据返回顺序声称“评分最高”或“高德官方推荐”。路线排序由调用方基于逐候选路线结果计算。
4. 详情可能缺少评价量和评论正文。评分可展示为“高德评分 X，评价量未取得”，但不能据此形成口碑最佳结论。
5. 已核验 POI 可生成 `https://uri.amap.com/poidetail?poiid=<POI_ID>&src=travel-planning&callnative=1`；有坐标时再生成 `https://uri.amap.com/navigation` 到店入口。URI API 参数必须来自本次核验结果。

## 路线与距离

| 意图 | 工具 | 必填参数 |
| --- | --- | --- |
| 步行 | `maps_direction_walking` | `origin`、`destination` |
| 驾车 | `maps_direction_driving` | `origin`、`destination` |
| 骑行 | `maps_bicycling` | `origin`、`destination` |
| 公交/地铁/综合交通 | `maps_direction_transit_integrated` | `origin`、`destination`、`city`、`cityd` |
| 距离测量 | `maps_distance` | `origins`、`destination`；`type=0/1/3` 分别为直线/驾车/步行 |

多个距离起点以 `|` 分隔。高德返回的路线耗时不自动包含找入口、候车、安检、停车和步行缓冲。

## 其他

- `maps_weather(city)`：城市名或 adcode。
- `maps_ip_location(ip)`：IP 定位；不得在用户未要求时主动提交 IP。

官方来源：<https://lbs.amap.com/api/mcp-server/summary>
