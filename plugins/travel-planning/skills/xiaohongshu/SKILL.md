---
name: xiaohongshu
description: 使用插件集成并锁定版本的 autoclaw-cc/xiaohongshu-skills 通用能力操作用户已登录的 Chrome，包括登录、搜索笔记、读取详情、用户主页，以及用户明确要求时的发布和互动。旅行研究默认只读。
---

# 小红书通用能力

本 Skill 复用 `autoclaw-cc/xiaohongshu-skills`，不重新实现它的浏览器自动化。

## 首次使用

在插件根目录运行：

```bash
python3 skills/xiaohongshu/scripts/setup.py install
python3 skills/xiaohongshu/scripts/setup.py status
```

上游能力已经随插件内置。初始化只安装锁定依赖，并返回内置 Skill 路由、Chrome 扩展目录和 CLI 命令。用户需要在 `chrome://extensions/` 开启开发者模式，并将返回的 `extension_path` 作为“已解压的扩展程序”加载。不得索要用户 Cookie、密码或浏览器配置文件。

## 执行规则

1. 运行 `python3 skills/xiaohongshu/scripts/setup.py upstream-skill` 取得插件内的上游路由入口。
2. 完整读取 `references/upstream/root.md`，再按意图读取 `references/upstream/xhs-auth.md`、`xhs-explore.md`、`xhs-publish.md`、`xhs-interact.md` 或 `xhs-content-ops.md`。这些文件是内部路由资料，不是独立安装的 Skill。
3. 上游文档中的 `python scripts/cli.py` 统一映射为 `python3 skills/xiaohongshu/scripts/cli.py`；只能通过该包装入口调用内置实现。
4. 搜索和读取属于外部网站操作，控制频率；遇到验证码、风控或账号提示立即停止并交给用户本人处理。
5. 旅行规划任务只调用 `check-login`、`search-feeds`、`get-feed-detail`、`user-profile` 等读取能力。发布、评论、回复、点赞、收藏和退出登录只在用户明确提出相应操作时执行，并遵守上游确认要求。
6. `xsecToken`、Cookie、二维码和临时媒体地址不得写入旅行 workspace、最终 JSON、HTML、日志或回答；旅行证据只保留公开原帖链接、标题、作者、发布时间、必要摘要和查询时间。

上游项目为 MIT 许可的非官方自动化工具。插件固定其 commit，但小红书页面和风控仍可能变化。
