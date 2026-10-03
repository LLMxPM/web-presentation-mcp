# web-presentation MCP Server（规划中）

本目录已有实现仍为历史骨架，尚未完成远程多用户能力的实现、验收和发布。当前可用入口为 `wp` CLI；不要将骨架启动成功或工具名称检查通过视作远程服务可交付。

远程多用户方案与 A0～A9 工作包见 [MCP 服务实施计划](../docs/mcp-implementation-plan.md)，包括工具/API 映射、认证隔离、同步/异步客户端分工、任务与幂等、部署和测试。平台授权与 API 工作见[主仓 M0～M7 计划](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/mcp-implementation-plan.md)。

首期目标为远程授权、只读与创作闭环、预览/截图和单项归档；批量确认、上传、Resources 和正式多副本支持按后续工作包验收。内部助手迁移标准 API 不作为前置工作。
