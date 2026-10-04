# web-presentation-mcp

Web Presentation 的独立 MCP 服务仓库，维护协议适配、工具/API 映射、专用异步 HTTP 客户端和服务交付。2026-10-04 从原 `web-presentation-agent-kit/mcp-server` 拆出，保留该子目录 Git 历史。

**当前状态：开发骨架，远程多用户 MCP 尚未交付。** 已完成拆仓、独立异步客户端与 stdio 生命周期调整。OAuth 请求身份、完整 binding、操作手册、结构化输出、预览/截图工具、生产部署和真实宿主验收仍待实施；本仓测试通过不代表远程可用。

## 仓库关系

| 仓库 | 职责 |
| --- | --- |
| [web-presentation](https://github.com/LLMxPM/web-presentation) | 平台、OAuth、权限、External API、业务任务与 Gateway 集成 |
| [web-presentation-cli](https://github.com/LLMxPM/web-presentation-cli) | `wp`、PAT/Profile、同步客户端、本地文件和配套 Skill |
| 本仓 | MCP、异步客户端、逐请求授权适配、媒体结果、独立部署 |

两端分别维护客户端，仅共同消费 [External API v1 契约](https://github.com/LLMxPM/web-presentation/blob/dev/docs/developer/reference/external-agent-api.md)。MCP 不依赖 CLI/API Client 包，不执行 `wp`，不导入 Backend 内部实现，也不访问数据库、Redis、Runtime 或 Renderer。

## 本地开发

需要 Python 3.11+ 和 `uv`：

```powershell
uv sync --frozen
uv run pytest
uv run wp-mcp --help
uv build --out-dir .tmp/dist
```

当前仅保留单用户 stdio 开发入口，使用 `WP_ENDPOINT`、`WP_TOKEN` 和可选 `WP_WORKSPACE_ID`；不要把 Token 写入仓库或发送给模型。`--transport streamable-http` 会拒绝启动，待远程认证与隔离验收后再开放。历史中失效的 `get_operation_guide()` 调用和静态元数据写入白名单已移除，正式工具从新 binding 与当前 OpenAPI 派生。

`src/wp_mcp/client.py` 使用 `httpx.AsyncClient`，逐请求接收不可变身份/空间，支持 JSON、二进制、公开 OpenAPI 和 Job 短等待。等待预算耗尽返回最新状态；写入要求显式幂等键，断连不会取消 Backend Job。该 HTTP 基础不承担 OAuth 令牌验证。

## 目录与后续工作

```text
web-presentation-mcp/
├── src/wp_mcp/          # MCP 骨架与仓内异步客户端
├── tests/               # 独立回归测试
├── docs/                # MCP 实施规划与拆仓记录
├── .github/workflows/   # 独立 CI，不发布未验收服务
├── LICENSE              # Apache-2.0，与 CLI 相同
├── pyproject.toml
└── uv.lock
```

[MCP 实施计划](docs/mcp-implementation-plan.md) 维护 A0～A9；[拆仓记录](docs/repository-split.md) 记录本次范围。平台授权与 API 工作见[主仓 M0～M7 计划](https://github.com/LLMxPM/web-presentation/blob/dev/docs/developer/mcp-implementation-plan.md)。两仓独立维护客户端，不再以共享 SDK 提取或发布为前置工作。首期仍优先远程多用户授权和创作闭环，stdio 骨架不代替该目标。

## License

采用 Apache License 2.0，完整协议与 CLI 一致，见 [LICENSE](LICENSE)。
