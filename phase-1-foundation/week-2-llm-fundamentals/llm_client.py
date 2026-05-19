import os
import asyncio
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI
from google import genai
from google.genai import types
from enum import Enum
from dataclasses import dataclass
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from typing import Optional
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class LLMProvider(str, Enum):
    GROQ = "GROQ"
    GEMINI = "GEMINI"


@dataclass
class LLMResponse:
    provider: LLMProvider
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    content: str


@dataclass
class UsageAccumulator:
    """Class to accumulate usage data for multiple requests"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: float = 0
    call_count: int = 0

    def record(self, response: LLMResponse):
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens
        self.total_cost_usd += response.cost_usd
        self.call_count += 1

    def summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "call_count": self.call_count,
            "average_cost_per_call": round(
                self.total_cost_usd / max(self.call_count, 1), 6
            ),
        }


PRICING = {
    "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
    "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-pro": {"input": 0.00125, "output": 0.005},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model, {"input": 0.0001, "output": 0.0005})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000


class LLMClient:
    def __init__(
        self,
        primary_provider: LLMProvider = LLMProvider.GROQ,
        fallback_provider: LLMProvider = LLMProvider.GEMINI,
        usage_accumulator: Optional[UsageAccumulator] = None,
    ):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.usage = usage_accumulator
        self._groq_client = AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
        )
        self._gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful fintech AI assistant.",
        model: Optional[str] = None,
        max_tokens: int = 200,
        temperature: float = 0.1,
    ) -> LLMResponse:

        try:
            response = await self._call_provider(
                self.primary, prompt, system, model, max_tokens, temperature
            )
            if self.usage:  # Fix: Ensure usage exists before recording
                self.usage.record(response)
            return response

        except Exception as primary_error:
            if self.fallback:
                logger.warning(
                    f"Primary provider {self.primary} failed: {primary_error}. Falling back to {self.fallback}"
                )
                response = await self._call_provider(
                    self.fallback, prompt, system, None, max_tokens, temperature
                )
                self.usage.record(response)
                return response
            raise

    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        system: str,
        model: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        start = time.perf_counter()
        if provider == LLMProvider.GROQ:
            # --- INTENTIONAL EXCEPTION ---
            # This forces Groq to fail so the Tenacity @retry and fallback logic kicks in!
            # raise ConnectionError("Simulated Groq Outage to test Gemini Fallback!")
            # -----------------------------
            m = model or "llama-3.1-8b-instant"
            response = await self._groq_client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            return LLMResponse(
                provider=provider,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms,
                cost_usd=calculate_cost(
                    m, response.usage.prompt_tokens, response.usage.completion_tokens
                ),
                content=response.choices[0].message.content,
            )
        else:
            m = model or "gemini-2.5-flash"
            response = await self._gemini_client.aio.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            latency_ms = (time.perf_counter() - start) * 1000
            return LLMResponse(
                provider=provider,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                latency_ms=latency_ms,
                cost_usd=calculate_cost(
                    m,
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                ),
                content=response.text,
            )


async def demo():
    usage = UsageAccumulator()
    client = LLMClient(usage_accumulator=usage)
    prompts = [
        "What is the standard KYC document required for a home loan in India?",
        "Explain what a DLQ (Dead Letter Queue) is in one sentence.",
        "What does 'sub-200ms p95 latency' mean in plain English?",
    ]
    for prompt in prompts:
        response = await client.complete(prompt)
        print(
            f"[{response.provider.value}] {response.latency_ms}ms | ${response.cost_usd} | {response.content[:100]}..."
        )
    print(f"\nSession totals: {usage.summary()}")


if __name__ == "__main__":
    asyncio.run(demo())
