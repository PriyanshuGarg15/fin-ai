import httpx
from typing import Any, Optional
from dataclasses import dataclass
from tenacity import (retry, stop_after_attempt, wait_exponential, before_sleep_log, retry_if_exception_type)
import logging
logger = logging.getLogger(__name__)
@dataclass
class HTTPResponse:
    status_code: int
    headers: dict
    data: Any
    latency: float

class HTTPClientError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"HTTP Error {status_code}: {message} at {url}")
    
class RateLimitError(HTTPClientError): pass
class ServerError(HTTPClientError): pass
class TimeoutError(HTTPClientError): pass

class AsyncHttpClient:
    def __init__(self, base_url: str, timeoutSeconds: int=10):
        self.base_url = base_url
        self.timeoutSeconds = timeoutSeconds
        self._client : Optional[httpx.AsyncClient]= None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url= self.base_url, timeout=self.timeoutSeconds)
        return self
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    @retry(
        retry=retry_if_exception_type(ServerError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get(self, path: str, params: dict = None)->HTTPResponse: # (url: str):
        import time
        start= time.perf_counter()
        try:
            response = await self._client.get(path, params=params)
            latency= (time.perf_counter() - start) *1000
            if response.status_code == 429:
                raise RateLimitError(response.status_code, response.text, response.url)
            if response.status_code >= 500:
                raise HTTPClientError(response.status_code, response.text, response.url)
            response.raise_for_status()
            return HTTPResponse(response.status_code, response.headers, response.json(), latency)
        except httpx.TimeoutException:
            raise TimeoutError(408, "Request timed out", f"{self.base_url}{path}")


            



