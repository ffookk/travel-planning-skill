# 交互页面规范

最终页面默认采用“日期与时间节点 + 右侧卡片”的单列时间轴，同时提供可切换的高密度“行程一览”表格和按天聚合的“路线图”，并满足以下规则。

## 顶部与全局

- 顶部显示路线、日期、人数、预算策略和最后核验时间；不要把逐景点费用、逐段交通和逐日天气复制到顶部。
- 顶部提供“详细行程 / 行程一览 / 路线图”切换，默认进入详细行程。切换是即时、可逆的页内状态，支持 `Tab` 与左右方向键，不改写行程数据。
- 交互层由 `web/` 中的 Vue 源码经 Vite 编译，产物 CSS 与 JavaScript 由渲染器内联进最终 HTML；旅行者最终仍只收到一份 `itinerary.html`，不得依赖同目录下的本地脚本或样式文件。
- 页面采用渐进增强：Vue 成功挂载后以组件 `v-show` 管理三个视图；微信附件预览、内容安全策略或旧内核阻止脚本运行时，顶部控件必须退化为纯 CSS 单选状态并继续真正切换视图，所有地图保留 HTTPS 外链。
- 编译目标不得保留可选链等会让旧版微信 WebView 整段脚本解析失败的语法；发布前同时检查编译包语法、无脚本静态内容和微信内 HTTPS 页面。微信附件预览可能完全禁用脚本，不能把框架编译描述成附件内完整交互的保证。
- PC 端的顶部内容、详细行程、一览表、路线图、信息来源和页脚共用同一个居中内容容器与左右留白；切换视图时内容边界不能横向跳动。窄屏沿用独立的紧凑内边距。
- 顶部之后直接进入逐日时间线，不额外渲染“规划说明”或全局假设列表；会改变执行的约束放回对应事件。
- 不设置顶部日期标签、粘性日期导航或滚动高亮监听。日期是时间轴中的一级节点，事件时间是卡片前的二级节点，不为时间单独预留左栏。
- 提供“只看待预约”“只看交通”“只看付费项目”等筛选。
- 提供打印/导出入口；静态 HTML 不伪装成已经联网的 App。

## 时间轴卡片

- 时间轴是默认详细视图。景点研究、相邻交通、天气影响和费用不能只存在于一览表。
- 核心信息使用带字段名的定义列表或表格，不能把时长、区域、费用、预约、入口等值直接塞进无标题 Tag/Chip 让读者猜含义。Tag 只可用于“需预约”“可选”“待复核”等辅助状态。
- 执行信息默认展开。开放时间、停止入场、入口、内部时间轴、交通线路、门票和费用不允许放进“查看详情”折叠区。
- 没有真实且可合法复用的图片时省略图片区域，不显示渐变色块、图钉或其他假图片占位。
- 每张景点图显示来源、作者和许可，并可跳转原始文件页。小红书等社区内容以“近期体验参考”链接卡呈现，显示标题、作者、互动数与用途说明；临时 CDN 封面不作为行程图片热链。
- 景点卡右上角显示一个至少 44×44px 的天气图标按钮，带可读的 `aria-label` 和摘要 tooltip，点击打开该地点天气网站。天气摘要不再占用定义列表的一行；无天气入口时省略图标。
- 景点卡按“标题与时长区域 → 开放与预约 → 景区内怎么玩 → 注意事项”排序。“开放与预约”是一个完整的行前决策区，内部依次展示开放规则、预约行动与入口、票价与费用，不再在景点卡下方重复渲染独立的“预约与抢票”和“费用明细”卡片。预约说明与临时公告共用同一官方 URL 时合并为“官方预约与公告”，不得因链接去重而隐藏预约动作。已核验微信公众号时，在官网与公告旁显示绿色公众号入口：有官方微信预约说明文章时跳转文章，只有公众号名称时复制名称并提示用户去微信内搜索及进入对应菜单；不得构造不可验证的公众号主页链接或嵌入二维码。
- “景区内怎么玩”使用卡片内部的嵌套时间轴。入口信息并入首节点，出口和最晚离开时间并入末节点，不在时间轴上方另起重复卡片。每个节点展示开始/结束时间、名称、必达/可选、动作；只有研究结果真实提供节点看点或讲解时才显示“现场看点”，不使用通用占位文案。适用时再展示从上一点的移动、节点图片、内部交通、途中餐饮、链接和失败备选。
- 节点图片紧邻对应节点，沿用主图的作者、许可和原始页面规则。节点途中补给引用 `meal_options[]`，不把菜品、人均和排队信息重复写成自由文本。
- 景点费用继续区分基础门票、必选景交、可选项目、互斥套票和2人/全体基线小计。
- 交通：精确起终点、线路/车次、门到门时间、费用、换乘、推荐理由和备选。提前规划页面不展示“实时状态”行；需要临行处理的动态条件写成有时间点的复核任务。
- 中国境内普通交通段按宿主设备选择无需 Key 的高德页面：桌面浏览器使用 `ditu.amap.com/dir`，只有不含途经点的移动端驾车段使用 `m.amap.com/navigation/carmap`。每日完整路线统一使用 `ditu.amap.com/dir`，按顺序写入 `via[0]`、`via[1]` 等途经点，移动端不得降级到会丢失途经点的简化链接。不能用 iframe 宽度、CSS 缩放或宿主页 `meta viewport` 冒充移动 UA。路线图旁紧邻“在高德查看完整路线”链接。所有站点必须来自已核验 POI 坐标；酒店未定时可用明确标注的片区锚点，订房后必须重算。首次登录提示由用户自行关闭；iframe 失败时仍须保留外部路线链接。
- 默认地图只承担快速感知路线的职责，使用约 `300px` 的桌面高度和 `240px` 的窄屏高度；每张地图必须提供宿主页自己的“全屏查看”按钮。全屏时路线卡铺满视口、iframe 占据剩余空间，按钮改为“退出全屏”，并允许按 `Esc` 退出；不支持 Fullscreen API 时在新标签打开当前设备对应的高德路线。
- 路线 iframe 只在首次接近视口时加载；加载后停止观察，不因滚出视口而卸载和再次导航。
- 住宿：入住日期、片区/酒店、价格、行李寄存、去下一站耗时。
- 餐饮：事件标题后先显示 `selected_candidate_id` 对应的综合推荐，再将 `fallback_candidate_ids` 对应的备选餐厅渲染为可横向滚动的完整卡片列表；餐饮事件副标题不再重复推荐理由。综合推荐和备选卡都默认展开并可收起；备选卡保持稳定宽度，不因候选数量变多而压成窄列。每张卡直接显示地址、特色菜、平台评分、小红书证据或搜索入口、营业信息、前后两段路线和高德门店入口。时间窗已由时间轴表达，不再渲染第二次；不得展示内部评分、加分拆解、长篇选择理由、切换规则、页内排序、“选择这家”或“已选为本餐”。只有已取得且能改变提前安排的预约方式才进入餐厅卡。每张餐厅卡前后两段路线分别展示真实的“起点名称 → 终点名称”、双方具体地址、距离与门到门时间；路线标题本身作为高德入口，不在操作按钮区重复输出同名路线按钮，不得只显示“从上一站”或“去下一站”。每张卡最多保留一个“在高德查看门店”入口，不另渲染独立的“导航到店”，也不重复渲染来源数据中指向高德门店或导航的别名链接；餐饮事件级链接不在卡片下方再次输出。每餐另提供以上一行程锚点为中心的“在高德查看附近餐厅”入口，并与综合推荐的“在高德查看门店”一起放在主推荐卡底部，不单独悬在卡片顶部。高德返回评分但缺少评价量时展示“评价量未取得”，不把整个评分改成不可用。不得把小红书互动数或多个平台评分合成无来源的总分。
- 小红书存在满足门店身份与时效要求的原帖时，直接展示原帖标题、作者和链接；没有门店级原帖时只提供门店搜索入口，不得展示城市级美食主题分数或将主题笔记描述为门店口碑。所有面向旅行者的平台名统一显示为“高德”和“小红书”，不展示内部 provider ID。
- 风险：天气、高反、拥挤、晚点和临时关闭时的备选。

## 行程一览

- 一览视图使用小字号、紧凑行高和表格线，固定为“时间 / 地点 / 关键信息”三列，日期作为跨列分组行，不再复制图片、地图、来源、操作按钮和研究字段。
- 第三列按事件类型选择会改变执行的信息：景点展示特色、游览顺序、开放、进出口、最晚离开、预约、费用和备选；交通展示方式、线路、门到门耗时、费用和备选；餐饮只展示综合推荐门店、特色、菜系、人均、营业和绕行，不重复选择理由、备选与切换条件；住宿展示入住、价格、行李和下一站衔接。
- 窄屏仍保留表格语义，使用带焦点的横向滚动容器查看完整三列，不拆成卡片；打印时移除阴影与粘性表头。

## 路线图

- 路线图按行程日期分组，每天只渲染 `planning.daily_routes[]` 中与日期匹配的一条高德导览路线；进入该视图后不显示事件详情、费用、信息来源、页脚、图片或行程一览字段。
- `daily_routes[].stops[]` 按当天实际事件顺序列出住宿出发点、每个景点、主选正餐、其他停靠点和当晚住宿/结束点。第一站作为 `from`，最后一站作为 `to`，中间全部站点依次转换为 `via[n]`；页面同时显示编号站点带，便于用户确认没有漏站。
- 导览路线用于完整展示当天顺序，默认以驾车模式把全部停靠点串成一张图；公交、步行、打车等分段方式及各段时长仍以详细行程为准，不把导览图当作统一交通方式建议。
- 当天没有可展示的完整高德路线时显示明确空状态。路线图沿用地图懒加载、设备识别、全屏、外部链接兜底与窄屏规则。

## 操作按钮

每个按钮由 `action_links[]` 生成：

- `map`：地图定位或导航。
- `official`：景点/酒店/餐厅/承运方官网。
- `official_homepage`、`official_notice`、`official_booking`、`official_wechat`：景点官网、公告、网页预约和微信公众号预约说明入口，四者不可混用。
- `weather`、`weather_warning`：地点天气页和官方预警页。
- `ticket`：景点购票页。
- `train`：铁路查询/购票入口。
- `bus`：大巴查询/购票入口。
- `hotel`：酒店详情/预订入口。
- `restaurant`：餐厅详情/预约入口。
- `guide`、`image_source`：节点讲解和图片原始页面。
- `source`：查看支撑当前结论的信息来源。

按钮必须展示平台名。外部跳转统一新窗口打开并使用安全链接属性。价格旁显示“查询于 YYYY-MM-DD HH:mm，最终以平台为准”。页面只负责跳转；没有用户单独明确授权时，不自动选座、填乘客、提交订单或付款。

已核验高德 POI 的餐厅卡优先提供“在高德查看门店”和“在高德导航到店”。详情使用 `https://uri.amap.com/poidetail`，导航使用 `https://uri.amap.com/navigation`；移动端可尝试调起高德 App，桌面端保留 H5 页面。高德链接用于用户实时查看和自由选择，不代表高德为本行程背书。

## 汇总与派生

- 预算：从事件 `cost_items[]` 派生交通、住宿、门票、付费项目和餐饮小计；区分已确认、平台价、估算、待复核和可选。汇总可以放在行程末尾，但不能维护第二套金额。
- 待办：购票、订房、景点预约、餐厅预约及各自截止时间。
- 每日强度：步行、爬升、换乘次数、最早出发、最晚回酒店。
- 复核提醒：天气、余票、价格、开放时间和临时公告的再次检查时间。

## Explicit minimal share summary

For a public-facing summary, run `python3 scripts/export_share_summary.py itinerary.json share.html --selection share-selection.json` from this skill's directory. This is a separate optional export; the full private itinerary and its ordinary renderer remain unchanged. It is a selected highlights page, not a complete execution guide or an automatic anonymizer.

Create the selection with the exact labels intended for the audience:

```json
{
  "schema_version": "travel-share-selection/v1",
  "public_title": "Weekend highlights",
  "attractions": [{"id": "a1", "public_label": "Lakeside walk"}]
}
```

Only `public_title` (default: `Travel highlights`) and explicitly supplied `public_label` text enter the HTML. Attraction IDs are checked against actually used attractions but are not exported. The exporter does not copy the itinerary's original title, attraction names, dates, times, traveler details, hotel information, addresses, coordinates, private notes, documents, quote data, source links, query parameters, or unknown extension fields. Selection order is independent of the private schedule. Empty selection yields a generic page.

The summary contains no scripts, links, external images, fonts or embedded maps. Review the chosen public labels: text deliberately placed in the selection is published to the file exactly as supplied (HTML-escaped), and labels can still reveal a destination or identity. This boundary avoids copying private source fields; it cannot establish that human-authored public text is anonymous. The command only writes a local file and never authorizes or performs online publication. Keep the selection and complete source itinerary private.
