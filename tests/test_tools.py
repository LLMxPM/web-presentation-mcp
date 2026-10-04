"""文件功能：验证 MCP stdio 骨架的工具边界，并拒绝尚未实现的远程入口。"""

from __future__ import annotations

import asyncio

from wp_mcp.server import mcp


def test_tools_list_contains_mutations_and_no_build() -> None:
    """开发查询与任务工具已注册，正式 guide 与 Build 工具仍不披露。"""

    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "wp_list_workspaces",
        "wp_get_standards",
        "wp_get_mutation_job",
        "wp_cancel_mutation_job",
        "wp_retry_mutation_job",
    } <= names
    assert not any("build" in name.lower() for name in names)
    assert "wp_get_operation_guide" not in names


def test_remote_transport_is_not_exposed_before_authentication(monkeypatch) -> None:
    """开发骨架不能以共享环境 PAT 启动远程多用户 HTTP 服务。"""
    import pytest
    from wp_mcp.server import main

    monkeypatch.setattr("sys.argv", ["wp-mcp", "--transport", "streamable-http"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
