import asyncio
import os
import json
from dotenv import load_dotenv
from prompts_registry import registry
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
)


async def evaluate_applicant(version_name: str, applicant_data: dict) -> str:
    """Runs the specified prompt version against the LLM"""
    prompt_obj = registry.get(version_name)

    user_message = f"""
    Evaluate the following applicant:
    {json.dumps(applicant_data, indent=2)}
    
    Respond in JSON format using exactly this sequence of keys to enforce step-by-step calculation:
    1. "reasoning" (string, first calculate the haircut, then the FOIR, then evaluate against rules)
    2. "calculated_foir_percentage" (number)
    3. "is_eligible" (boolean)
    """

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt_obj.system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return json.loads(response.choices[0].message.content)


async def main():
    tricky_applicant = {
        "applicant_id": "APP_SELF_EMP_01",
        "monthly_income": 100000,
        "existing_emis": 45000,
        "credit_score": 680,
        "employment_type": "Self-employed",
    }
    print("Evaluating Applicant: {tricky_applicant['applicant_id']}")
    print("Profile: Self-Employed, Income: 100k, EMIs: 45k\n")
    # Run both prompts concurrently!
    print("Running evaluations via Groq...")
    v1_task = evaluate_applicant("loan_eligibility_v1", tricky_applicant)
    v2_task = evaluate_applicant("loan_eligibility_v2", tricky_applicant)

    v1_result, v2_result = await asyncio.gather(v1_task, v2_task)

    # Print Side-by-Side Comparison
    print("=" * 80)
    print(f"{'METRIC':<20} | {'V1 (BASELINE)':<25} | {'V2 (HAIRCUT RULES)':<25}")
    print("=" * 80)

    print(
        f"{'Eligible?':<20} | {str(v1_result.get('is_eligible')):<25} | {str(v2_result.get('is_eligible')):<25}"
    )
    print(
        f"{'Calculated FOIR':<20} | {str(v1_result.get('calculated_foir_percentage')) + '%':<25} | {str(v2_result.get('calculated_foir_percentage')) + '%':<25}"
    )

    print("-" * 80)
    print("V1 Reasoning:")
    print(v1_result.get("reasoning"))
    print("\nV2 Reasoning:")
    print(v2_result.get("reasoning"))
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
