"""文件功能：装配 MCP 开发用 stdio 骨架；远程身份接入完成前拒绝 HTTP 启动。"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
import json
from typing import Any, AsyncIterator, Awaitable, Callable, Literal

from mcp.server.mcpserver import MCPServer

from wp_mcp.backend import BackendGateway
from wp_mcp.errors import ApiClientError
from wp_mcp.settings import Settings

_gateway: BackendGateway | None = None


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[None]:
    """在 stdio 应用生命周期创建和关闭连接池，不供远程多用户复用身份。"""
    global _gateway
    gateway = BackendGateway(Settings.from_env())
    _gateway = gateway
    try:
        yield None
    finally:
        await gateway.close()
        _gateway = None


mcp = MCPServer("web-presentation-mcp", lifespan=lifespan)


def get_gateway() -> BackendGateway:
    """返回由生命周期初始化的 stdio 网关，禁止脱离生命周期懒建连接池。"""
    if _gateway is None:
        raise RuntimeError("MCP 生命周期尚未初始化")
    return _gateway


async def _call(operation: Callable[[], Awaitable[Any]]) -> str:
    """等待业务调用并转换开发文本结果，不传播凭证或底层响应全文。"""
    try:
        result = await operation()
    except ApiClientError as exc:
        raise RuntimeError(json.dumps({
            "code": exc.code, "message": exc.message, "status_code": exc.status_code,
            "details": exc.details, "request_id": exc.request_id, "retry_after": exc.retry_after,
        }, ensure_ascii=False)) from exc
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


@mcp.tool()
async def wp_list_workspaces() -> str:
    """列出 stdio 开发凭证允许访问的工作空间。"""
    return await _call(get_gateway().list_workspaces)


@mcp.tool()
async def wp_get_standards(kind: Literal["page", "component"]) -> str:
    """读取页面或组件源码规范。"""
    return await _call(lambda: get_gateway().get_standards(kind))


@mcp.tool()
async def wp_list_projects(workspace_id: int | None = None) -> str:
    """查询指定工作空间的项目；未指定时使用 stdio 开发配置。"""
    return await _call(lambda: get_gateway().list_projects(workspace_id))


@mcp.tool()
async def wp_get_mutation_job(job_id: str, wait: bool = False, timeout_seconds: float = 20.0) -> str:
    """查询 Backend Job，等待超时返回最新非终态。"""
    return await _call(lambda: get_gateway().get_mutation_job(job_id, wait, timeout_seconds))


@mcp.tool()
async def wp_cancel_mutation_job(job_id: str, idempotency_key: str) -> str:
    """显式取消业务任务，网络重放需复用同一幂等键。"""
    return await _call(lambda: get_gateway().cancel_mutation_job(job_id, idempotency_key))


@mcp.tool()
async def wp_retry_mutation_job(job_id: str, idempotency_key: str) -> str:
    """请求 Backend 创建重试任务，保留原版本基线。"""
    return await _call(lambda: get_gateway().retry_mutation_job(job_id, idempotency_key))


def main() -> None:
    """仅开放 stdio 开发入口；远程 transport 依赖 OAuth 与隔离验收。"""
    parser = argparse.ArgumentParser(description="Web Presentation MCP 开发骨架（远程服务待实施）")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    args = parser.parse_args()
    if args.transport != "stdio":
        parser.error("远程多用户认证尚未实现，请完成 docs/mcp-implementation-plan.md 验收后启用 HTTP")
    mcp.run(transport="stdio")
