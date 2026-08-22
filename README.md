# web-presentation MCP Server

这是 `web-presentation-agent-kit` 的 MCP 协议适配层。当前只实现只读工具，用于验证传输、认证上下文和 External API v1 契约；写工具和 OAuth 资源服务器验证应在只读链路稳定后按本仓实施计划逐步加入。

主仓负责维护 External API v1 的路径、Scope、DTO、错误码、幂等和任务语义，统一见 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md)。本目录只维护 MCP 协议适配、工具/资源注册、传输安全和本仓测试；详细实施计划见 [docs/mcp-implementation-plan.md](../docs/mcp-implementation-plan.md)。

## 启动

```powershell
$env:WP_ENDPOINT = "http://127.0.0.1:8000"
$env:WP_TOKEN = "wp_pat_xxx"
$env:WP_WORKSPACE_ID = "1"

uv run --project mcp-server wp-mcp
uv run --project mcp-server wp-mcp --transport streamable-http --port 8001
```

stdio 模式下 stdout 只输出 MCP JSON-RPC；日志不得写入 stdout。HTTP 模式上线前必须补充 Bearer Token 验证、audience/resource 校验、限流和 Host allowlist，不要把服务端环境 Token 当作远程多租户授权方案。

## 当前只读能力

- `wp_list_workspaces`
- `wp_get_operation_guide`
- `wp_get_standards`
- `wp_list_projects`
- `wp://guides`

所有 Backend 调用都经过共享 `web-presentation-api-client`，公共路径固定为 `/api/v1`。
