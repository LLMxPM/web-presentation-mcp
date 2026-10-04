# CLI / MCP 仓库拆分记录

日期：2026-10-04。

- 原 `web-presentation-agent-kit` 改名为 [web-presentation-cli](https://github.com/LLMxPM/web-presentation-cli)，保留仓库历史、`wp` 命令和 PyPI 包名。
- 新建公开 [web-presentation-mcp](https://github.com/LLMxPM/web-presentation-mcp)，用 `git subtree split --prefix=mcp-server` 保留 MCP 子目录历史；迁移源为 `5f9489a`，子目录历史头为 `730b3282a52768048d8333dd84432e3fb259bb5c`。
- 两仓使用相同 Apache-2.0 LICENSE。CLI 保留仓内同步客户端；MCP 维护仓内异步客户端，不依赖或发布共享 SDK。
- MCP A0～A9 计划迁到 MCP 仓库；主仓 M0～M7 计划继续只维护授权、API、Gateway 和验收交接。
- CLI 移除 MCP workspace 成员、源码与测试，重新生成 uv.lock；同步更新仓库链接、包元数据和 PyPI Trusted Publisher 说明。本次不发布新的 CLI/Skill 版本。
- MCP 移除 CLI 客户端依赖，增加异步 HTTP 基础和独立 CI。历史失效 guide 与静态写字段白名单不再披露；远程认证和完整创作闭环仍待实施，HTTP 暂不开放。
- 平台现行文档、CLI 跨仓测试路径与 workflow 同步新仓名；历史归档保留当时仓库名称和验收证据。

本次只完成拆仓和客户端独立基础，不能将其视作远程 MCP 上线验收。两仓都以 Backend External API v1 和当前 OpenAPI 为事实源，各自执行消费者契约回归。
