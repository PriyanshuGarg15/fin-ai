import instructor
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)
load_dotenv()

# implementation with OpenAI
structured_client = instructor.from_openai(
    AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
    ),
    mode=instructor.Mode.TOOLS,
)

# implementation with Groq direct
structured_client2 = instructor.from_provider(
    "groq/llama-3.1-8b-instant", async_client=True
)

# --- GEMINI CLIENT INITIALIZATION ---
# Wrap the new Google GenAI SDK with Instructor
structured_client3 = instructor.from_provider(
    "google/gemini-2.5-flash", async_client=True
)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class LoanEligibilityAssessment(BaseModel):
    """Structured output for loan eligibility — every field must be populated"""

    applicant_id: str
    reasoning: str = Field(
        ...,
        description="First, calculate the FOIR percentage. Then check if the credit score meets the minimum. Explain the logic before deciding eligibility.",
    )
    is_eligible: bool
    risk_level: Literal["low", "medium", "high", "very_high"]
    recommended_loan_amount: float = Field(..., ge=0)
    recommended_tenure_months: int = Field(..., ge=6, le=360)
    key_positive_factors: list[str] = Field(..., min_length=1, max_length=5)
    key_risk_factors: list[str] = Field(..., max_length=5)
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    @field_validator("recommended_loan_amount")
    @classmethod
    def amount_must_be_positive_if_eligible(cls, v, info):
        # info.data contains the previously parsed fields (like is_eligible)
        if info.data.get("is_eligible") and v == 0:
            raise ValueError(
                "Eligible applicants must have a non-zero recommended amount"
            )
        return v


async def assess_loan_eligibility(applicant_data: dict) -> LoanEligibilityAssessment:
    """
    Uses LLM to assess loan eligibility with structured, validated output.
    """
    prompt = f"""
    Assess loan eligibility for the following applicant:
    
    Applicant ID: {applicant_data["applicant_id"]}
    Monthly Income: INR {applicant_data["monthly_income"]:,}
    Credit Score: {applicant_data.get("credit_score", "Not provided")}
    Employment Type: {applicant_data.get("employment_type", "Salaried")}
    Requested Amount: INR {applicant_data["requested_amount"]:,}
    Requested Tenure: {applicant_data.get("tenure_months", 36)} months
    Existing EMIs: INR {applicant_data.get("existing_emis", 0):,}/month
    
    Provide a structured eligibility assessment following standard Indian lending norms:
    - FOIR (Fixed Obligation to Income Ratio) should not exceed 50%
    - Minimum credit score for personal loans: 650
    - Loan amount typically max 60x monthly income
    """

    # 2. Changed from Anthropic's .messages to OpenAI's .chat.completions
    # return await structured_client.chat.completions.create(
    #     model="llama-3.1-8b-instant", # Using Groq's fast model
    #     messages=[{"role": "user", "content": prompt}],
    #     response_model=LoanEligibilityAssessment, # Instructor catches this!
    #     max_retries=3 # If the LLM fails validation, Instructor will retry up to 3 times automatically
    # )

    return await structured_client3.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        response_model=LoanEligibilityAssessment,
        max_retries=3,
    )


async def main():
    test_cases = [
        {
            "applicant_id": "APP001",
            "monthly_income": 80000,
            "credit_score": 720,
            "employment_type": "Salaried",
            "requested_amount": 500000,
            "tenure_months": 36,
            "existing_emis": 10000,
        },
        {
            "applicant_id": "APP002",
            "monthly_income": 45000,
            "credit_score": 580,
            "employment_type": "Self-employed",
            "requested_amount": 800000,
            "tenure_months": 60,
            "existing_emis": 25000,
        },
    ]
    for applicant in test_cases:
        print(f"\nProcessing {applicant['applicant_id']}...")
        result = await assess_loan_eligibility(applicant)

        # Notice how we access `result` using dot-notation like a normal Python object!
        print(f"=== {result.applicant_id} ===")
        print(
            f"Eligible: {result.is_eligible} | Risk: {result.risk_level} | Confidence: {result.confidence_score}"
        )
        print(
            f"Recommended: INR {result.recommended_loan_amount:,.0f} for {result.recommended_tenure_months} months"
        )
        print(f"Positives: {result.key_positive_factors}")
        print(f"Risks: {result.key_risk_factors}")
        print(f"Reasoning: {result.reasoning[:150]}...")


if __name__ == "__main__":
    asyncio.run(main())
