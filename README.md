# Travel Planning Plugin

面向 Codex 与 Claude Code 的旅行研究插件仓库。仓库通过 `.agents/plugins/marketplace.json` 暴露一个位于 `plugins/travel-planning/` 的插件，把行程规划 Skill、通用小红书能力、飞猪/飞常准、地图、天气和页面生成工具打包为一个交付单元，同时保留各数据源最合适的原生接入方式。

| 能力 | 复用方式 |
| --- | --- |
| 小红书 | 固定版本 `xpzouying/xiaohongshu-mcp`，本地 Streamable HTTP MCP + 独立浏览器 |
| 飞猪 FlyAI | 插件内单一 `flyai` Skill + 固定版本官方 CLI，连接供应商 MCP API |
| 飞常准 | 单一 `variflight` Skill + Aviation 与 Tripmatch stdio MCP Server |
| 高德 | `amap-maps` Skill + 官方 stdio MCP Server + Web 服务 API |
| OpenStreetMap、Open-Meteo | 公开 API |
| 行程生成 | 插件内 `travel-planning` Skill 与 Python 工具 |

插件统一的是安装、发现、权限说明和旅行编排，不强制把已有 CLI 或 API 重写成 MCP。

## 插件入口

- 仓库市场：`.agents/plugins/marketplace.json`
- 项目启用配置：`.codex/config.toml`
- 插件目录：`plugins/travel-planning/`
- Codex：`plugins/travel-planning/.codex-plugin/plugin.json`
- Claude Code：`plugins/travel-planning/.claude-plugin/plugin.json`
- 可移植清单：`plugins/travel-planning/plugin.json`
- MCP 声明：`plugins/travel-planning/.mcp.json`
- Skills：`plugins/travel-planning/skills/`
- 插件级 Provider 启动器与环境加载：`plugins/travel-planning/scripts/providers/`、`plugins/travel-planning/scripts/runtime_env.py`
- 可提交的环境变量模板：`plugins/travel-planning/config/sources.example.env`
- 本机开发配置：`config/sources.local.env`（已忽略，位于可安装插件目录之外）

插件清单注册四个 MCP Server：高德地图 `amap-maps`、飞常准 `variflight-aviation`、`variflight-tripmatch`，以及本机 `xiaohongshu-mcp`。源码开发时，插件级启动器读取仓库根目录的本机配置；安装包回退到用户级 `~/.config/travel-planning/sources.local.env`，并兼容读取旧的 `~/.config/travel-itinerary-page/sources.local.env`。各 Provider 凭证彼此隔离；高德同时兼容已有的 `AMAP_API_KEY`，并只向官方 MCP 进程映射为 `AMAP_MAPS_API_KEY`。Skill 目录不保存环境配置或 Provider 启动器。

生成路线候选前，主 Skill 会在小红书已配置且登录态可用时执行一次有上限的目的地玩法与美食主题预研；它只影响路线比较和后续候选加分，不替代具体门店、营业或价格核验。路线确认、进入深度规划前，主 Skill 再运行统一 `preflight`：三个 MCP 执行协议握手、工具发现与只读上游探测，飞猪、Open-Meteo 和小红书也分别验证真实运行态。调用方通过重复的 `--require` 标记本次行程必需来源；必需来源失败时命令返回非零，非必需来源失败则明确降级并保留 fallback。

## 小红书首次初始化

```bash
cd plugins/travel-planning
python3 skills/xiaohongshu/scripts/setup.py install
python3 skills/xiaohongshu/scripts/setup.py start
python3 skills/xiaohongshu/scripts/setup.py status
```

安装器下载并校验固定 `v2.5.0` 的上游发布包。服务使用自己的独立浏览器，不需要 Chrome 扩展。检查 MCP 协议和登录态：

```bash
cd plugins/travel-planning
python3 skills/travel-planning/scripts/research_sources.py xhs-login-status
```

若返回 `login_required`，先运行 `setup.py stop`，再运行 `setup.py login`，由用户在上游登录工具打开的窗口中扫码，完成后重新 `setup.py start`。二进制、Cookie 与进程状态位于 `~/.local/share/travel-planning/xiaohongshu-mcp/`（可用 `TRAVEL_XHS_MCP_HOME` 覆盖），不会进入插件源码。

插件按供应商或用户任务域暴露五个 Skill：`travel-planning` 负责跨来源旅行编排，`xiaohongshu`、`flyai`、`amap-maps`、`variflight` 分别负责对应通用能力。高德、飞常准和小红书 Skill 只引导已注册 MCP 的工具选择与参数约束；小红书旅行研究默认只读，发布和互动必须来自用户明确请求。

## 验证

```bash
python3 /Users/mater/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/travel-planning
(cd plugins/travel-planning && python3 -m unittest discover -s tests -p 'test_*.py')
```

## 打包

```bash
make package
```

产物位于 `output/travel-planning-marketplace.zip`。它是一个可分发的本地 marketplace bundle，结构如下：

```text
travel-planning-marketplace/
├── .agents/plugins/marketplace.json
├── plugins/travel-planning/
└── README.md
```

`.agents/plugins/marketplace.json` 用于让 Codex 发现并安装插件；仓库自身的 `.codex/config.toml` 不进入压缩包，因为它只负责当前开发项目的启用状态，不应覆盖接收方配置。

Codex CLI 当前接收本地 marketplace 目录而不是 ZIP 文件本身。接收方先解压，再执行：

```bash
codex plugin marketplace add /absolute/path/to/travel-planning-marketplace
codex plugin add travel-planning@local --json
```

也可以直接把 ZIP 的绝对路径交给 Codex，并要求它“解压到持久目录，然后注册 marketplace 并安装 `travel-planning@local`”。

打包文件清单由 Git 生成：已跟踪文件和未被忽略的新文件会进入 ZIP，`.gitignore`、`.git/info/exclude` 以及全局 Git ignore 命中的文件不会进入 ZIP。

如需覆盖默认路径：

```bash
make package \
  PLUGIN_DIR=plugins/travel-planning \
  PACKAGE_OUTPUT=output/custom-name.zip \
  BUNDLE_NAME=custom-marketplace
```
