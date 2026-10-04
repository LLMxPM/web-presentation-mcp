"""文件功能：验证 MCP 异步短等待的预算、网络错误和取消不改变 Backend 业务任务。"""

import asyncio

import httpx
import pytest

from wp_mcp.client import AsyncApiClient, RequestContext
from wp_mcp.errors import ApiClientError


def test_wait_returns_latest_pending_state_within_total_budget() -> None:
    """后续 HTTP 超过剩余预算时返回已知状态，不能把业务 Job 标记失败。"""
    async def scenario() -> None:
        count = 0

        async def handler(request):
            nonlocal count
            count += 1
            if count > 1:
                await asyncio.sleep(1)
            return httpx.Response(200, json={'status': 'running'})

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            result = await asyncio.wait_for(client.poll_mutation_job(
                'job', context=RequestContext('user', 1), timeout_seconds=0.03, interval=0,
            ), timeout=0.3)
            assert result == {'status': 'running'}
            assert count == 2
        finally:
            await client.close()

    asyncio.run(scenario())


def test_wait_stops_at_terminal_job_state() -> None:
    """查询成功但 Job 失败时保留业务失败状态，不抛出 HTTP 错误。"""
    async def scenario() -> None:
        states = iter(['pending', 'failed'])
        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={'status': next(states)})))
        try:
            assert await client.poll_mutation_job('job', context=RequestContext(), interval=0) == {'status': 'failed'}
        finally:
            await client.close()

    asyncio.run(scenario())


def test_canceled_wait_does_not_cancel_backend_job() -> None:
    """客户端等待被取消时停止当前 await，但不发送业务 cancel 请求。"""
    async def scenario() -> None:
        started = asyncio.Event()
        requests = []

        async def handler(request):
            requests.append(request.url.path)
            started.set()
            await asyncio.sleep(1)
            return httpx.Response(200, json={'status': 'running'})

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            task = asyncio.create_task(client.poll_mutation_job('job', context=RequestContext()))
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert requests == ['/api/v1/jobs/mutations/job']
        finally:
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize('exception,code', [
    (httpx.ReadTimeout('secret'), 'REQUEST_TIMEOUT'),
    (httpx.ConnectError('secret'), 'NETWORK_ERROR'),
])
def test_transport_errors_do_not_retry_writes_or_expose_low_level_text(exception, code) -> None:
    """响应未知的写入只发送一次，错误中不回显底层地址或凭证。"""
    async def scenario() -> None:
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            raise exception

        client = AsyncApiClient('https://backend.test', transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ApiClientError) as exc:
                await client.request('POST', '/pages', context=RequestContext('secret', 1),
                                     idempotency_key='same-key')
            assert count == 1
            assert exc.value.code == code and 'secret' not in exc.value.message
        finally:
            await client.close()

    asyncio.run(scenario())
