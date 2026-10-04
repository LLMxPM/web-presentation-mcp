"""文件功能：定义 MCP 专用 HTTP 客户端错误，屏蔽凭证与非 JSON 网关响应。"""

from typing import Any

import httpx


class ApiClientError(Exception):
    """保存稳定错误码、HTTP 状态和服务端诊断标识，不携带用户凭证。"""

    def __init__(self, message: str, *, code: str, status_code: int = 500,
                 details: Any = None, request_id: str | None = None,
                 retry_after: str | None = None) -> None:
        """接收经过脱敏的业务错误，供 MCP 结果适配层处理。"""
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.request_id = request_id
        self.retry_after = retry_after


def response_error(response: httpx.Response, token: str | None) -> ApiClientError:
    """解析服务端 JSON 错误；HTML、底层网络文本和凭证明文不向模型传播。"""
    message = f"HTTP {response.status_code} 请求失败"
    code = "HTTP_ERROR"
    details = None
    if "application/json" in response.headers.get("content-type", ""):
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            message = str(payload.get("message") or message)
            code = str(payload.get("code") or code)
            details = payload.get("data", payload.get("detail"))
    if token:
        message = message.replace(token, "[redacted]")
        code = code.replace(token, "[redacted]")
        # 任意嵌套字段可能携带令牌；错误详情逐值脱敏而非输出响应全文。
        details = redact(details, token)
    return ApiClientError(message, code=code, status_code=response.status_code,
                          details=details, request_id=response.headers.get("X-Request-ID"),
                          retry_after=response.headers.get("Retry-After"))


def redact(value: Any, token: str) -> Any:
    """递归清除当前请求凭证，保留错误字段路径和原始结构。"""
    if isinstance(value, str):
        return value.replace(token, "[redacted]")
    if isinstance(value, list):
        return [redact(item, token) for item in value]
    if isinstance(value, dict):
        return {str(key).replace(token, "[redacted]"): redact(item, token)
                for key, item in value.items()}
    return value
