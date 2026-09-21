# 小红书 MCP 集成

只在需要近期体验、昼夜效果、拥挤、入口体验、餐厅口味/份量/排队/服务体感、避坑、包车或行李实测时读取本文档。小红书是体验来源，不是票价、营业承诺、开放、预约、安全或交通规则的权威来源。

## 集成形态

插件复用 Apache-2.0 许可的 [`xpzouying/xiaohongshu-mcp`](https://github.com/xpzouying/xiaohongshu-mcp)，固定 `v2.5.0` / commit `6583124dfda92312b6bc19a042a6acfae63fe498`。它在 `http://127.0.0.1:18060/mcp` 提供标准 Streamable HTTP MCP，并运行自己下载和管理的独立浏览器，不控制用户的 Chrome，也不需要 Chrome 扩展。

旅行研究默认只使用登录检查、搜索、详情和用户主页等读取能力。发布、评论、回复、点赞、收藏、删除 Cookie 等状态变更只有在用户明确提出对应操作时才能执行。

## 安装、启动与登录

```bash
python3 skills/xiaohongshu/scripts/setup.py install
python3 skills/xiaohongshu/scripts/setup.py start
python3 skills/xiaohongshu/scripts/setup.py status
```

安装器从上游 GitHub Release 下载服务和登录工具，按 `references/upstream.lock.json` 中的 SHA256 校验后存入 `~/.local/share/travel-planning/xiaohongshu-mcp/`。也可用 `TRAVEL_XHS_MCP_HOME` 指定其他目录。首次启动时上游会再下载并校验约 150 MB 的独立浏览器。

检查真实登录态：

```bash
python3 skills/travel-planning/scripts/research_sources.py xhs-health
python3 skills/travel-planning/scripts/research_sources.py xhs-login-status
```

若返回 `login_required`：

```bash
python3 skills/xiaohongshu/scripts/setup.py stop
python3 skills/xiaohongshu/scripts/setup.py login
python3 skills/xiaohongshu/scripts/setup.py start
```

`login` 会打开上游自己的可见浏览器窗口，由用户本人使用小红书 App 扫码。不要索要 Cookie、密码、短信验证码或浏览器配置文件。同一账号不要同时登录其他网页端，否则 MCP 的 Cookie 可能失效；手机 App 可正常使用。

## 常用读取能力

主 Agent 直接使用已注册的 MCP 工具：

- `check_login_status`
- `list_feeds`
- `search_feeds`
- `get_feed_detail`
- `user_profile`

命令行适配器仍提供脱敏后的旅行研究输出：

```bash
python3 skills/travel-planning/scripts/research_sources.py xhs-search \
  --keyword "西湖 10月 日落 入口 避坑" \
  --sort-by latest --publish-time half_year

python3 skills/travel-planning/scripts/research_sources.py xhs-detail \
  --note-id "<feed-id>"
```

搜索返回的 `xsec_token` 只保存在权限为 `0600` 的用户数据缓存中，并仅用于后续详情调用。Agent 不得在回答中展示令牌，也不得把令牌、Cookie、二维码、评论全集或临时媒体地址写入旅行 workspace、HTML、JSON、日志或版本库。

## 研究规则

1. 每个会影响行程的体验判断尽量查看至少 3 条近期内容，并标注一致、冲突和疑似推广。
2. 当季玩法使用“地点 + 月份/季节”；昼夜安排加入“日出/日落/夜景”；入口加入具体门名；偏远交通加入“包车/司导/路况/行李/加价/避坑”。
3. 社区结论统一标记 `community_reported`，置信度最高为 `medium`。
4. 开放时间、停入时间、票价、预约、入口是否开放、道路管制和司机资质必须另找官方或运营方来源。
5. 遇到验证码、设备验证、风控或账号提示时立即停止，由用户本人处理，不重试绕过。
6. 自动能力不可用时，执行 `fallback --kind xiaohongshu --keywords "..."`，把精确检索词和小红书入口交给用户，不用搜索引擎摘要冒充笔记内容。
7. 正常正餐的主选交叉至少 3 篇近 12 个月独立笔记，备选至少 2 篇；互动数只作为传播信号，不能改写成餐厅评分。
