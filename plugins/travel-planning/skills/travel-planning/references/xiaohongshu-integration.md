# 小红书通用能力集成

只在需要近期体验、昼夜效果、拥挤、入口体验、餐厅口味/份量/排队/服务体感、避坑、包车或行李实测时读取本文档。小红书是体验来源，不是票价、营业承诺、开放、预约、安全或交通规则的权威来源。

## 集成形态

插件复用 MIT 许可的 [`autoclaw-cc/xiaohongshu-skills`](https://github.com/autoclaw-cc/xiaohongshu-skills)，固定 commit `b043748282a57e347c52f517dfb59819121134ab`。它通过 Chrome 扩展连接用户自己已登录的浏览器，提供认证、搜索、详情、用户主页、发布和互动等通用能力。

插件不把所有数据源强制改造成 MCP。小红书沿用上游 Skill/CLI，飞常准沿用 MCP，高德同时使用官方 MCP 与 Web 服务 API，天气沿用公开 API；旅行 Skill 负责跨来源编排。

旅行研究默认只使用登录检查、搜索、详情和用户主页等读取能力。发布、评论、回复、点赞、收藏、退出登录等状态变更只有在用户明确提出对应操作时才能执行。

## 安装

```bash
python3 skills/xiaohongshu/scripts/setup.py install
python3 skills/xiaohongshu/scripts/setup.py status
```

固定版本的上游 Skill 路由、CLI 源码和 Chrome 扩展已直接包含在 `skills/xiaohongshu/`。安装器默认把锁定的 Python 虚拟环境放入用户数据目录 `~/.local/share/travel-planning/xiaohongshu-skills/`，并在新目录尚不存在时兼容复用旧目录；也可通过 `TRAVEL_XHS_HOME` 指定其他目录。根据命令返回的 `extension_path`，由用户本人在 `chrome://extensions/` 开启开发者模式并加载已解压扩展。不要索要 Cookie、密码、短信验证码或浏览器配置文件。

使用前读取上游 Skill 路由：

```bash
python3 skills/xiaohongshu/scripts/setup.py upstream-skill
```

## 常用读取能力

```bash
python3 skills/xiaohongshu/scripts/cli.py check-login

python3 skills/xiaohongshu/scripts/cli.py search-feeds \
  --keyword "西湖 10月 日落 入口 避坑" \
  --sort-by 最新 --publish-time 半年内

python3 skills/xiaohongshu/scripts/cli.py get-feed-detail \
  --feed-id "<feed-id>" --xsec-token "<本次搜索返回的临时令牌>"
```

`feed_id` 与 `xsec_token` 只用于当前浏览器查询链。Agent 不得在回答中展示令牌，也不得把令牌、Cookie、二维码、评论全集或临时图片地址写入旅行 workspace、HTML、JSON、日志或版本库。

需要纳入行程时，只归档公开原帖标识或可用链接、标题、作者、互动量、发布时间、短摘要、查询时间和交叉判断。不得复制整篇笔记、评论或未授权图片。

## 研究规则

1. 每个会影响行程的体验判断尽量查看至少 3 条近期内容，并标注一致、冲突和疑似推广。
2. 当季玩法使用“地点 + 月份/季节”；昼夜安排加入“日出/日落/夜景”；入口加入具体门名；偏远交通加入“包车/司导/路况/行李/加价/避坑”。
3. 社区结论统一标记 `community_reported`，置信度最高为 `medium`。
4. 开放时间、停入时间、票价、预约、入口是否开放、道路管制和司机资质必须另找官方或运营方来源。
5. 遇到验证码、设备验证、风控或账号提示时立即停止，由用户本人在官方页面处理，不重试绕过。
6. 自动能力不可用时，执行 `fallback --kind xiaohongshu --keywords "..."`，把精确检索词和小红书入口交给用户，不用搜索引擎摘要冒充笔记内容。
7. 正常正餐的主选交叉至少 3 篇近 12 个月独立笔记，备选至少 2 篇；互动数只作为传播信号，不能改写成餐厅评分。

## 上游能力边界

上游还包含发布和互动能力，这是通用 Skill 的组成部分，不代表旅行规划自动获得写权限。旅行任务不得因为插件已安装就自行发布、评论、点赞、收藏或退出登录。
