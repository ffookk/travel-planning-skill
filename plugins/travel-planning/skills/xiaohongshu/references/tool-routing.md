# 工具路由

服务地址由插件固定为 `http://127.0.0.1:18060/mcp`。旅行研究优先使用下列只读工具：

| 意图 | MCP 工具 | 关键参数 |
| --- | --- | --- |
| 检查登录 | `check_login_status` | 无 |
| 获取扫码二维码 | `get_login_qrcode` | 无；二维码只用于当次登录，不归档 |
| 首页候选 | `list_feeds` | 无 |
| 搜索笔记 | `search_feeds` | `keyword`；可选 `filters.sort_by/note_type/publish_time/search_scope/location` |
| 笔记详情 | `get_feed_detail` | `feed_id`、`xsec_token`；旅行研究保持 `load_all_comments=false` |
| 用户主页 | `user_profile` | `user_id`、`xsec_token` |

旅行检索的过滤值使用上游中文枚举：排序为 `综合/最新/最多点赞/最多评论/最多收藏`，类型为 `不限/视频/图文`，时间为 `不限/一天内/一周内/半年内`，范围为 `不限/已看过/未看过/已关注`，位置为 `不限/同城/附近`。

以下均是写操作，只有用户明确要求相应动作时才能调用：`publish_content`、`publish_with_video`、`post_comment_to_feed`、`reply_comment_in_feed`、`like_feed`、`favorite_feed`。`delete_cookies` 会清除本地登录态，也需要用户明确要求。

The managed server and login browser receive the shared minimal runtime environment and their explicit `COOKIES_PATH`; other provider keys and unrelated environment secrets are omitted. Proxy or certificate exceptions use the named passthrough described in [live data tools](../../travel-planning/references/live-data-tools.md). Preserving home and desktop-session settings enables the existing browser login flow and does not create an operating-system sandbox.

Server and login output stays in the permission-restricted local `service.log`. Startup failures report the exit status without copying the log tail. `setup.py logs` reports the local log location and withholds raw lines, including when the legacy `--lines` option is supplied. Inspect the file privately when necessary; do not paste raw runtime logs into agent messages, research workspaces, or shared reports because they may contain account data or tokens. The login tool still opens its own browser for the user's interaction; its console output is redirected to this local log.
