"""文件功能：提供 MCP 专用异步 HTTP 客户端，逐请求传递身份、空间和幂等键。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

from wp_mcp.errors import ApiClientError, response_error


@dataclass(frozen=True)
class RequestContext:
    """一个请求的不可变凭证与工作空间；认证验证由后续 OAuth 适配层负责。"""

    token: str | None = field(default=None, repr=False)
    workspace_id: int | None = None


class AsyncApiClient:
    """共用网络连接池，不在客户端对象上保存用户 token 或默认工作空间。"""

    def __init__(self, endpoint: str, *, timeout_seconds: float = 30.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        """使用受信 Backend 根地址建立异步连接池；transport 仅供测试注入。"""
        parsed = urlsplit(endpoint)
        if (parsed.scheme not in {"http", "https"} or not parsed.netloc
                or parsed.username or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or timeout_seconds <= 0):
            raise ValueError("endpoint 必须为不含凭证和路径的 Backend 根地址，timeout 必须大于 0")
        self.timeout_seconds = timeout_seconds
        self._http = httpx.AsyncClient(base_url=endpoint.rstrip("/"), transport=transport,
                                      timeout=timeout_seconds, follow_redirects=False)

    async def _response(self, method: str, path: str, *, context: RequestContext,
                        json_data: Any = None, params: Mapping[str, Any] | None = None,
                        idempotency_key: str | None = None,
                        timeout_seconds: float | None = None) -> httpx.Response:
        """发送受信 API 相对路径；拒绝重定向，公开契约不携带用户身份。"""
        if (not path.startswith("/") or path.startswith("//") or "\\" in path
                or any(part in {".", ".."} for part in path.split("/"))
                or "?" in path or "#" in path):
            raise ValueError("仅允许 Backend API 相对路径")
        public = path == "/openapi.json" and method == "GET"
        if not public and not path.startswith("/api/v1/"):
            raise ValueError("业务路径必须位于 /api/v1")
        if method not in {"GET", "HEAD"} and not idempotency_key:
            raise ValueError("写请求必须显式提供 idempotency_key")
        headers = {"Accept": "application/json", "User-Agent": "web-presentation-mcp-server/0.1.0"}
        if not public:
            if context.token:
                headers["Authorization"] = f"Bearer {context.token}"
            if context.workspace_id is not None:
                headers["X-Workspace-ID"] = str(context.workspace_id)
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
        timeout = min(timeout_seconds or self.timeout_seconds, self.timeout_seconds)
        request = self._http.build_request(method, path, headers=headers, json=json_data,
                                           params=params, timeout=timeout)
        # 即使上游意外设置 Cookie，也不能在后续用户请求中复用。
        request.headers.pop("Cookie", None)
        try:
            response = await self._http.send(request)
        except httpx.TimeoutException as exc:
            raise ApiClientError("请求服务端超时", code="REQUEST_TIMEOUT", status_code=504) from exc
        except httpx.RequestError as exc:
            raise ApiClientError("无法连接服务端", code="NETWORK_ERROR", status_code=503) from exc
        if not response.is_success:
            raise response_error(response, context.token)
        return response

    async def request(self, method: str, path: str, *, context: RequestContext,
                      json_data: Any = None, params: Mapping[str, Any] | None = None,
                      idempotency_key: str | None = None,
                      timeout_seconds: float | None = None) -> Any:
        """解析 JSON API；不自动重试写入，也不把非 JSON 响应视作成功 DTO。"""
        response = await self._response(method, f"/api/v1{path}", context=context,
                                        json_data=json_data, params=params,
                                        idempotency_key=idempotency_key,
                                        timeout_seconds=timeout_seconds)
        return self._json(response)

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        """处理无响应体与 JSON；契约异常使用明确错误而非返回网关文本。"""
        if response.status_code == 204:
            return {}
        if "application/json" in response.headers.get("content-type", ""):
            try:
                return response.json()
            except ValueError:
                pass
        raise ApiClientError("服务端未返回有效 JSON", code="INVALID_JSON_RESPONSE",
                             status_code=502)

    async def get_openapi_schema(self) -> dict[str, Any]:
        """从 Backend 根路径读取公开契约，不带用户 token、空间或 Cookie。"""
        response = await self._response("GET", "/openapi.json", context=RequestContext())
        document = self._json(response)
        if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
            raise ApiClientError("OpenAPI 文档缺少 paths", code="INVALID_OPENAPI", status_code=502)
        return document

    async def get_bytes(self, path: str, *, context: RequestContext) -> tuple[httpx.Headers, bytes]:
        """读取 API 二进制与版本 Headers；媒体类型由工具结果适配层验证。"""
        response = await self._response("GET", f"/api/v1{path}", context=context)
        return response.headers, response.content

    async def poll_mutation_job(self, job_id: str, *, context: RequestContext,
                                timeout_seconds: float = 20.0, interval: float = 1.0) -> dict[str, Any]:
        """在有界预算内轮询；预算耗尽返回最新状态，断连不调用业务取消 API。"""
        if timeout_seconds <= 0 or interval < 0:
            raise ValueError("timeout 必须大于 0，interval 不能为负数")
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        latest: dict[str, Any] | None = None
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0 and latest is not None:
                return latest
            try:
                async with asyncio.timeout(max(remaining, 0)):
                    latest = await self.request("GET", f"/jobs/mutations/{job_id}", context=context,
                                                timeout_seconds=remaining)
            except (TimeoutError, ApiClientError) as exc:
                if latest is not None and (isinstance(exc, TimeoutError) or exc.code == "REQUEST_TIMEOUT"):
                    return latest
                if isinstance(exc, TimeoutError):
                    raise ApiClientError("任务查询超时", code="REQUEST_TIMEOUT", status_code=504) from exc
                raise
            if latest.get("status") in {"succeeded", "failed", "canceled"}:
                return latest
            await asyncio.sleep(min(interval, max(deadline - asyncio.get_running_loop().time(), 0)))

    async def close(self) -> None:
        """关闭网络连接池；由 MCP 应用生命周期或测试负责调用。"""
        await self._http.aclose()
