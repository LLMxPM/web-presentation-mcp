"""文件功能：验证 MCP Server 的环境配置解析不回显敏感凭证。"""

from wp_mcp.settings import Settings


def test_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("WP_ENDPOINT", "https://backend.test")
    monkeypatch.setenv("WP_TOKEN", "pat_secret")
    monkeypatch.setenv("WP_WORKSPACE_ID", "42")

    settings = Settings.from_env()

    assert settings.endpoint == "https://backend.test"
    assert settings.token == "pat_secret"
    assert settings.workspace_id == 42
