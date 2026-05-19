from openai import AsyncOpenAI
import time
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()


class LLMObservabilityCollector:
    """
    Lightweight observability collector — mirrors CloudWatch custom metrics pattern.
    In production this would emit to CloudWatch/Datadog/LangSmith.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def push(self, log: dict):
        self.calls.append(log)

    def publish(self) -> dict:
        if not self.calls:
            print("No calls recorded")
            return 1
        latencies = [c["latency_ms"] for c in self.calls]
        costs = [c["cost_usd"] for c in self.calls]
        token_counts = [c["total_tokens"] for c in self.calls]
        latencies.sort()
        print("\n=== LLM Observability Report ===")
        print(f"Total calls: {len(self.calls)}")
        print(f"Latency P50: {latencies[len(latencies) // 2]:.0f}ms")
        print(f"Latency P95: {latencies[int(len(latencies) * 0.95)]:.0f}ms")
        print(f"Latency Max: {max(latencies):.0f}ms")
        print(f"Total cost: ${sum(costs):.6f}")
        print(f"Avg cost/call: ${sum(costs) / len(costs):.6f}")
        print(f"Avg tokens/call: {sum(token_counts) / len(token_counts):.0f}")
        return 1


collector = LLMObservabilityCollector()


async def stream_with_Observability(prompt: str, label: str) -> str:
    """Stream LLM response and collect full observability metrics"""
    start = time.perf_counter()
    full_response = []
    input_tokens = 0
    output_tokens = 0
    print(f"\n[{label}] Streaming: ", end="", flush=True)
    client = AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
    )
    stream = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        stop=None,
        stream=True,
        max_completion_tokens=300,
        stream_options={"include_usage": True},
        messages=[{"role": "user", "content": prompt}],
    )
    async for chunk in stream:
        if len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
            text = chunk.choices[0].delta.content
            print(text, end="", flush=True)
            full_response.append(text)
        if chunk.usage is not None:
            input_tokens = chunk.usage.prompt_tokens
            output_tokens = chunk.usage.completion_tokens
    latency_ms = (time.perf_counter() - start) * 1000
    cost_usd = (input_tokens * 0.05 + output_tokens * 0.08) / 1_00_000
    collector.push(
        {
            "label": label,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
        }
    )
    print(
        f"\n[{label}] Done: {latency_ms:.0f}ms | {input_tokens}+{output_tokens} tokens | ${cost_usd:.6f}"
    )
    return "".join(full_response)


async def main():
    tasks = [
        (
            "Summarize the KYC requirements for home loans in India in 3 bullet points",
            "task-kyc",
        ),
        ("What is FOIR and why is it important in lending?", "task-foir"),
        ("Explain what an NBFC is in one paragraph", "task-nbfc"),
        ("What is eNACH and how does it work in Indian fintech?", "task-enach"),
    ]
    # Run sequentially to see streaming in action clearly
    for prompt, label in tasks:
        await stream_with_Observability(prompt, label)
    collector.publish()


if __name__ == "__main__":
    asyncio.run(main())
