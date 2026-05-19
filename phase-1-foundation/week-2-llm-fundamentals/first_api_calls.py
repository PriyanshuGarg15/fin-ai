import os
import asyncio
import time
import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI
from google import genai
from google.genai import types

load_dotenv()

# Initializing LLM Clients
grok_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Using tiktoken for token counting
def count_tokens_tiktoken(prompt, model="gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(prompt))


async def call_groq(prompt: str) -> dict:
    time_start = time.perf_counter()
    response = await grok_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    latency_ms = (time.perf_counter() - time_start) * 1000
    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    cost = (in_tokens * 0.05 + out_tokens * 0.08) / 1_000_000

    return {
        "provider": "Groq (Llama 3.1 8B)",
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "latency_ms": round(latency_ms, 2),
        "cost_usd": f"{cost:.8f}",
        "content": response.choices[0].message.content,
    }


async def call_gemini(prompt: str) -> dict:
    time_start = time.perf_counter()
    model_id = "gemini-2.5-flash"
    response = await gemini_client.aio.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=200,
            temperature=0.1,
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
                ),
            ],
        ),
    )
    # Finding response finishin reason, becasue Gemini was cutting response abruptly.
    try:
        candidate = response.candidates[0]
        finish_reason = (
            candidate.finish_reason.name
            if hasattr(candidate.finish_reason, "name")
            else str(candidate.finish_reason)
        )
    except Exception:
        finish_reason = "UNKNOWN"

    content = (
        response.text
        + f"\n\n[DIAGNOSTIC WARNING: Output cut off! Reason: {finish_reason}]"
    )
    latency_ms = (time.perf_counter() - time_start) * 1000
    usage = response.usage_metadata
    in_tokens = usage.prompt_token_count
    out_tokens = usage.candidates_token_count
    cost = (in_tokens * 0.075 + out_tokens * 0.30) / 1_000_000
    return {
        "provider": "Gemini {model_id}",
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "latency_ms": round(latency_ms, 2),
        "cost_usd": f"{cost:.8f}",
        "content": content,
    }


async def main():
    prompt = "A loan applicant has a credit score of 720, monthly income of INR 80,000, and is requesting INR 500,000. In one sentence, assess their eligibility."
    print(f"Pre-call Tiktoken estimate: {count_tokens_tiktoken(prompt)} tokens")
    print("Running concurrent requests...\n")

    results = await asyncio.gather(call_groq(prompt), call_gemini(prompt))

    for res in results:
        print(f"--- {res['provider']} ---")
        print(f"Latency:  {res['latency_ms']}ms")
        print(
            f"Actual Tokens:     {res['input_tokens']} in / {res['output_tokens']} out"
        )
        print(f"Estimated Cost:    ${res['cost_usd']}")
        print(f"Response: {res['content'].strip()}\n")


if __name__ == "__main__":
    asyncio.run(main())
