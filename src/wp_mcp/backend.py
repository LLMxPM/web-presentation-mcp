"""文件功能：保留开发用 stdio 骨架的 Backend 映射，使用 MCP 仓内异步客户端。"""

from typing import Any

from wp_mcp.client import AsyncApiClient, RequestContext
from wp_mcp.settings import Settings


class BackendGateway:
    """单用户 stdio 开发网关；远程逐请求 OAuth 上下文仍按实施计划接入。"""

    def __init__(self, settings: Settings) -> None:
        """创建异步连接池与 stdio 身份，不导入 CLI 或共享 SDK。"""
        self.client = AsyncApiClient(settings.endpoint)
        self.context = RequestContext(token=settings.token, workspace_id=settings.workspace_id)

    async def list_workspaces(self) -> Any:
        """查询开发凭证获授权的工作空间。"""
        return await self.client.request("GET", "/workspaces", context=self.context)

    async def get_standards(self, kind: str) -> Any:
        """按既有公开路径读取当前用户的页面或组件规范。"""
        return await self.client.request("GET", f"/standards/{kind}", context=self.context)

    async def list_projects(self, workspace_id: int | None = None) -> Any:
        """查询指定空间的项目，空间覆盖仅作用于本次请求。"""
        context = self.context if workspace_id is None else RequestContext(self.context.token, workspace_id)
        return await self.client.request("GET", "/projects", context=context)

    async def get_mutation_job(self, job_id: str, wait: bool = False,
                               timeout_seconds: float = 20.0) -> Any:
        """查询或有界等待 Backend Job，不自建任务队列。"""
        if wait:
            return await self.client.poll_mutation_job(job_id, context=self.context,
                                                       timeout_seconds=timeout_seconds)
        return await self.client.request("GET", f"/jobs/mutations/{job_id}", context=self.context)

    async def cancel_mutation_job(self, job_id: str, idempotency_key: str) -> Any:
        """显式取消业务任务；始终复用调用方提供的幂等键。"""
        return await self.client.request("POST", f"/jobs/mutations/{job_id}/cancel",
                                         context=self.context, idempotency_key=idempotency_key)

    async def retry_mutation_job(self, job_id: str, idempotency_key: str) -> Any:
        """由 Backend 判断可重试性并返回新任务。"""
        return await self.client.request("POST", f"/jobs/mutations/{job_id}/retry",
                                         context=self.context, idempotency_key=idempotency_key)

    async def close(self) -> None:
        """释放开发网关的异步连接池。"""
        await self.client.close()
