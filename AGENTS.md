# AGENTS.md

## 仓库定位

`web-presentation-mcp` 是独立 MCP 仓库，2026-10-04 从原 `web-presentation-agent-kit/mcp-server` 拆出，保留该子目录历史和 Apache-2.0 协议。本仓维护协议、工具映射、专用异步客户端、部署与实施规划。CLI、同步客户端和 Skill 由 [web-presentation-cli](https://github.com/LLMxPM/web-presentation-cli) 维护。

当前仅完成拆仓、独立异步 HTTP 基础与开发用 stdio 骨架。远程 OAuth、binding、创作闭环、结构化结果、镜像和真实客户端验收仍按 [实施计划](docs/mcp-implementation-plan.md) 推进，不能声明远程服务可用。

## 基础规范

- 使用中文进行协作、提交说明和文档编写。
- 使用 `uv`、根 `.venv` 与唯一 `uv.lock` 管理依赖和运行环境。
- 源文件开头写明功能；函数用中文说明职责、输入输出和关键约束；复杂文件按职责拆分。
- 不依赖 CLI 客户端包、Click 或 Skill，不通过子进程调用 `wp`；允许少量 HTTP 适配重复，不发布共享 SDK。
- 不导入 Backend 内部 `app` 或工具目录，不连接数据库、Redis、Runtime、Renderer 或 Chromium。
- 业务参数与权限以 Backend `/api/v1`、OpenAPI、capabilities 和 standards 为准，不维护静态业务 DTO 镜像。
- 远程认证、工具 Schema、真实 HTTP 与逐请求身份隔离验收通过后才能启用 HTTP。stdio 环境 PAT 仅用于单用户开发，不能作为远程身份回退。
- 连接池可共用，token、工作空间、Cookie 与幂等键必须逐请求隔离；写入不透明重试、传输取消不等于业务 Job 取消。
- 项目通常已启动，不反复启动平台服务；跨仓 E2E 使用专属账号与数据。

## 模块边界

- `src/wp_mcp/client.py`、`errors.py`：专用异步 HTTP、JSON/二进制、幂等、错误和短等待。
- `backend.py`、`settings.py`：历史 stdio 配置与映射，不能用于远程用户身份。
- `server.py`：SDK 生命周期和开发入口；后续按计划拆分远程 auth、context、bindings、guides、results。
- `docs/`：MCP 实施和交付；平台授权与 API 候选契约只引用主仓。
- `tests/`：客户端、工具与入口回归；未来增加真实 HTTP、OAuth 和主仓契约对拍。

## 验证

```powershell
uv sync --frozen
uv run pytest
uv run wp-mcp --help
uv build --out-dir .tmp/dist
```

独立安装必须不依赖相邻 CLI。客户端测试覆盖并发身份/空间、显式幂等键、公开契约无凭证、下载/重定向、短等待、取消及连接释放。当前测试通过仅证明拆仓基础，不代表 A0～A9 或真实远程交付验收通过。
