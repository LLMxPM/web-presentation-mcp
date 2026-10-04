"""文件功能：验证 MCP 专用异步客户端的身份隔离、契约读取、幂等与传输错误。"""

import asyncio
from dataclasses import FrozenInstanceError

import httpx
import pytest

from wp_mcp.client import AsyncApiClient, RequestContext
from wp_mcp.errors import ApiClientError


def test_concurrent_requests_keep_identity_and_workspace_isolated() -> None:
    """共用连接池的交错请求必须各自保留 token/空间，不受另一请求覆盖。"""
    async def scenario() -> None:
        arrived = asyncio.Event()
        seen = []

        async def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.headers['Authorization'], request.headers['X-Workspace-ID']))
            if len(seen) == 2:
                arrived.set()
            await arrived.wait()
            return httpx.Response(200, json={'workspace': request.headers['X-Workspace-ID']})

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            results = await asyncio.gather(
                client.request('GET', '/projects', context=RequestContext('user-a', 1)),
                client.request('GET', '/projects', context=RequestContext('user-b', 2)),
            )
            assert results == [{'workspace': '1'}, {'workspace': '2'}]
            assert set(seen) == {('Bearer user-a', '1'), ('Bearer user-b', '2')}
            context = RequestContext('secret', 1)
            assert 'secret' not in repr(context)
            with pytest.raises(FrozenInstanceError):
                context.workspace_id = 2
        finally:
            await client.close()
        assert client._http.is_closed

    asyncio.run(scenario())


def test_public_openapi_and_subsequent_user_requests_do_not_share_cookies() -> None:
    """公开 OpenAPI 不携带身份；上游意外 Cookie 不得进入其他用户请求。"""
    async def scenario() -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            payload = {'paths': {}} if request.url.path == '/openapi.json' else {}
            return httpx.Response(200, json=payload, headers={'Set-Cookie': 'user=a; Path=/'})

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            await client.request('GET', '/workspaces', context=RequestContext('a', 1))
            assert await client.get_openapi_schema() == {'paths': {}}
            await client.request('GET', '/workspaces', context=RequestContext('b', 2))
            assert 'Authorization' not in requests[1].headers
            assert 'X-Workspace-ID' not in requests[1].headers
            assert all('Cookie' not in request.headers for request in requests)
            assert requests[2].headers['Authorization'] == 'Bearer b'
        finally:
            await client.close()

    asyncio.run(scenario())


def test_writes_require_and_preserve_explicit_idempotency_keys() -> None:
    """拒绝无键写入，允许同一请求用同键重放且不由客户端更换键。"""
    async def scenario() -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(202, json={'job_id': 'one'})

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ValueError, match='idempotency_key'):
                await client.request('POST', '/pages', context=RequestContext('user', 1))
            assert not requests
            for _ in range(2):
                await client.request('POST', '/pages', context=RequestContext('user', 1),
                                     json_data={'title': 'A'}, idempotency_key='original-key')
            assert [r.headers['Idempotency-Key'] for r in requests] == ['original-key'] * 2
        finally:
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize('response,code', [
    (httpx.Response(302, headers={'Location': 'https://outside.test'}), 'HTTP_ERROR'),
    (httpx.Response(500, text='<html>private data</html>'), 'HTTP_ERROR'),
    (httpx.Response(200, text='broken'), 'INVALID_JSON_RESPONSE'),
    (httpx.Response(200, headers={'Content-Type': 'application/json'}, text='{'), 'INVALID_JSON_RESPONSE'),
])
def test_redirect_and_non_json_are_not_followed_or_exposed(response, code) -> None:
    """网关 HTML 不冒充 DTO，带身份请求不会跟随跨域重定向。"""
    async def scenario() -> None:
        paths = []

        def handler(request):
            paths.append(str(request.url))
            return response

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ApiClientError) as exc:
                await client.request('GET', '/projects', context=RequestContext('secret', 1))
            assert exc.value.code == code
            assert 'private data' not in str(exc.value)
            assert paths == ['https://backend.test/api/v1/projects']
        finally:
            await client.close()

    asyncio.run(scenario())


def test_errors_keep_metadata_and_redact_nested_credentials() -> None:
    """保留错误码/字段与 request ID，错误响应中出现凭证时逐层脱敏。"""
    async def scenario() -> None:
        response = httpx.Response(409, json={'code': 'CONFLICT', 'message': 'secret failed',
                                           'data': {'field': ['secret']}},
                                 headers={'X-Request-ID': 'r1', 'Retry-After': '2'})
        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(lambda _: response))
        try:
            with pytest.raises(ApiClientError) as exc:
                await client.request('POST', '/pages', context=RequestContext('secret', 1),
                                     idempotency_key='key')
            error = exc.value
            assert error.code == 'CONFLICT'
            assert error.request_id == 'r1' and error.retry_after == '2'
            assert error.details == {'field': ['[redacted]']}
            assert 'secret' not in error.message
        finally:
            await client.close()

    asyncio.run(scenario())


def test_binary_api_returns_headers_and_rejects_outside_paths() -> None:
    """二进制保持原始内容和页面版本，不接受服务器路径或任意外域 URL。"""
    async def scenario() -> None:
        response = httpx.Response(200, content=b'png', headers={'X-Page-Version-No': '3'})
        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(lambda _: response))
        try:
            headers, content = await client.get_bytes('/pages/1/screenshot', context=RequestContext('a', 1))
            assert headers['X-Page-Version-No'] == '3' and content == b'png'
            for path in ('https://outside.test/image', '/../internal'):
                with pytest.raises(ValueError):
                    await client.get_bytes(path, context=RequestContext('a', 1))
        finally:
            await client.close()

    asyncio.run(scenario())
