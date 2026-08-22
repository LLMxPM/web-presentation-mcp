"""文件功能：验证 MCP 工具显式注册表与 Build 能力边界。"""

from __future__ import annotations

import asyncio

from wp_mcp.server import mcp


def test_tools_list_contains_mutations_and_no_build() -> None:
    """Mutation 与安全元数据工具必须公开，Build 工具不得注册。"""

    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "wp_get_operation_guide",
        "wp_update_entity",
        "wp_get_mutation_job",
        "wp_cancel_mutation_job",
        "wp_retry_mutation_job",
    } <= names
    assert not any("build" in name.lower() for name in names)
