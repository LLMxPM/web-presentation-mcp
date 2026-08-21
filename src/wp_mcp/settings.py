"""文件功能：读取 MCP Server 连接 Backend 所需的环境配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """MCP Server 的最小运行配置。"""

    endpoint: str
    token: str | None
    workspace_id: int | None

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置；不在异常或日志中回显 Token。"""

        raw_workspace_id = os.getenv("WP_WORKSPACE_ID")
        workspace_id = int(raw_workspace_id) if raw_workspace_id else None
        return cls(
            endpoint=os.getenv("WP_ENDPOINT", "http://127.0.0.1:8000"),
            token=os.getenv("WP_TOKEN"),
            workspace_id=workspace_id,
        )
