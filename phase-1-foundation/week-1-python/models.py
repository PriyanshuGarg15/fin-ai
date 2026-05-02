from pydantic import BaseModel, Field, field_validator
from enum import Enum

class LoanType(str, Enum):
    PERSONAL = "personal"
    NEWCAR = "newcar"
    USEDCAR = "usedcar"

class LoanApplicationRequest(BaseModel):
    mobileNo: str = Field(..., description="Unique identifier for the applicant")
    loan_type: LoanType
    loan_amount: float =Field(..., gt=0, le=1000000)
    monthly_income: float =Field(..., gt=0 )
    credit_score: float = Field(..., gt=300, le=850)

    @field_validator("loan_amount")
    @classmethod
    def loan_amount_limit(cls, v, info):
        if 'monthly_income' in info.data:
            if v > (60 * info.data.monthly_income):
                raise ValueError("Loan amount must not be more than 60x of monthly income")
        return v

class loanApplicationResponse(BaseModel):
    leadId: str = Field(...,
        description="Unique identifier for the loan application")
    eligibility_score: float
    message: str
    status: str