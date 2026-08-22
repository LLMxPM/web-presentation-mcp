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

    def get_guides(self, operation_key: str | None = None) -> Any:
        """查询 Guides 索引或指定 operation 的精确契约。"""

        return self.client.get_operation_guide(operation_key)

    def get_standards(self, kind: str) -> Any:
        """查询页面或组件的当前开发规范。"""

        return self.client.get(f"/standards/{kind}")

    def list_projects(self, workspace_id: int | None = None) -> Any:
        """查询指定工作空间内的项目。"""

        return self.client.get("/projects", workspace_id=workspace_id)

    def update_entity(
        self,
        resource_type: str,
        target_id: int,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> Any:
        """更新页面或组件公开的安全元数据字段。"""

        allowed_fields = {
            "page": {"title", "summary", "speaker_notes"},
            "component": {"name", "summary"},
        }
        if resource_type not in allowed_fields:
            raise ValueError("resource_type 仅支持 page 或 component")
        unexpected = set(payload) - allowed_fields[resource_type]
        if unexpected or not payload:
            raise ValueError(f"payload 字段不合法: {sorted(unexpected)}")
        return self.client.patch(
            f"/{resource_type}s/{target_id}",
            json_data=payload,
            idempotency_key=idempotency_key,
        )

    def get_mutation_job(self, job_id: str, wait: bool = False, timeout_seconds: float = 60.0) -> Any:
        """查询或等待 Mutation Job。"""

        if wait:
            return self.client.poll_mutation_job(job_id, timeout_seconds=timeout_seconds)
        return self.client.get_mutation_job(job_id)

    def cancel_mutation_job(self, job_id: str, idempotency_key: str | None = None) -> Any:
        """请求取消 Mutation Job。"""

        return self.client.cancel_mutation_job(job_id, idempotency_key=idempotency_key)

    def retry_mutation_job(self, job_id: str, idempotency_key: str | None = None) -> Any:
        """人工重试 retryable failed Mutation Job。"""

        return self.client.retry_mutation_job(job_id, idempotency_key=idempotency_key)

    def close(self) -> None:
        """释放底层 HTTP 连接池。"""

        self.client.close()
