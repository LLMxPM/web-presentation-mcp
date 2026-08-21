# web-presentation MCP Server

这是 `web-presentation-agent-kit` 的 MCP 协议适配层。当前只实现只读工具，用于验证传输、认证上下文和 External API v1 契约；写工具和 OAuth 资源服务器验证应在只读链路稳定后按主仓 MCP 规划逐步加入。

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
