"""文件功能：注册只读 MCP Tools/Resources，并提供 stdio 与 Streamable HTTP 入口。"""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from wp_api_client import ApiClientError

from wp_mcp.backend import BackendGateway
from wp_mcp.settings import Settings

mcp = MCPServer("web-presentation-agent-kit")
_gateway: BackendGateway | None = None


def get_gateway() -> BackendGateway:
    """按进程懒加载 Backend 网关，避免导入模块时创建网络连接。"""

    global _gateway
    if _gateway is None:
        _gateway = BackendGateway(Settings.from_env())
    return _gateway


def _result(value: Any) -> str:
    """将 Backend 数据编码为不泄露凭证的 MCP 文本结果。"""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _call(operation: Any) -> str:
    """统一转换 Backend 错误，保留稳定错误码但不回显凭证和底层响应全文。"""

    try:
        return _result(operation())
    except ApiClientError as exc:
        raise RuntimeError(
            _result({
                "code": exc.code,
                "message": exc.message,
                "status_code": exc.status_code,
            })
        ) from exc


@mcp.tool()
def wp_list_workspaces() -> str:
    """列出当前 PAT 可访问的工作空间；写操作前必须先选择唯一空间。"""

    return _call(get_gateway().list_workspaces)


@mcp.tool()
def wp_get_operation_guide() -> str:
    """读取 Backend 当前发布的 External API v1 操作指南和参数 Schema。"""

    return _call(get_gateway().get_guides)


@mcp.tool()
def wp_get_standards(kind: Literal["page", "component"]) -> str:
    """读取页面或组件源码的当前开发规范。"""

    return _call(lambda: get_gateway().get_standards(kind))


@mcp.tool()
def wp_list_projects(workspace_id: int | None = None) -> str:
    """查询一个工作空间中的项目；不传参数时使用 WP_WORKSPACE_ID。"""

    return _call(lambda: get_gateway().list_projects(workspace_id))


@mcp.resource("wp://guides")
def guides_resource() -> str:
    """将当前操作指南作为可复用 MCP Resource 暴露。"""

    return wp_get_operation_guide()


def main() -> None:
    """解析传输参数并启动 MCP Server。"""

    parser = argparse.ArgumentParser(description="web-presentation External API v1 MCP Server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP 传输方式，默认 stdio",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP 监听地址")
    parser.add_argument("--port", type=int, default=8001, help="HTTP 监听端口")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        stateless_http=True,
        json_response=True,
    )
