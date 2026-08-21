"""文件功能：封装 MCP 对 Backend External API v1 的只读访问。"""

from __future__ import annotations

from typing import Any

from wp_api_client import ApiClient

from wp_mcp.settings import Settings


class BackendGateway:
    """MCP Server 使用的 Backend 网关，不暴露数据库或内部 Service。"""

    def __init__(self, settings: Settings) -> None:
        self.client = ApiClient(
            endpoint=settings.endpoint,
            token=settings.token,
            workspace_id=settings.workspace_id,
            user_agent="web-presentation-mcp-server/0.1.0",
        )

    def list_workspaces(self) -> Any:
        """查询当前 PAT 可访问的工作空间。"""

        return self.client.get("/workspaces")

    def get_guides(self) -> Any:
        """查询当前 Backend 发布的操作指南和参数 Schema。"""

        return self.client.get("/guides")

    def get_standards(self, kind: str) -> Any:
        """查询页面或组件的当前开发规范。"""

        return self.client.get(f"/standards/{kind}")

    def list_projects(self, workspace_id: int | None = None) -> Any:
        """查询指定工作空间内的项目。"""

        return self.client.get("/projects", workspace_id=workspace_id)

    def close(self) -> None:
        """释放底层 HTTP 连接池。"""

        self.client.close()
