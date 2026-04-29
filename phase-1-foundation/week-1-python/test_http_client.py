import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch
from http_client import AsyncHttpClient, ServerError, RateLimitError

@pytest.mark.asyncio
async def test_successful_get():
    async with AsyncHttpClient("https://httpbin.org") as client:
        response = await client.get("/get", params={"test": "1"})
        assert response.status_code == 200
        assert "args" in response.data
        assert response.latency > 0

@pytest.mark.asyncio
async def test_rate_limit_raises():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        async with AsyncHttpClient("https://example.com") as client:
            with pytest.raises(RateLimitError):
                await client.get("/api")