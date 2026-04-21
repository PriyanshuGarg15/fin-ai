from fastapi import FastAPI, HTTPException
from models import LoanApplicationRequest, loanApplicationResponse
from uuid import uuid4
app = FastAPI()

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": "foundation", "day": 1, "hour": 0} 

@app.post("/createLoanApplication")
async def createLoanApplication(request: LoanApplicationRequest) -> loanApplicationResponse:
    if request.credit_score < 600:
        raise HTTPException(status_code=400, detail="Credit score must be greater than 600")    
    return loanApplicationResponse(
        leadId   = uuid4(), 
        eligibility_score= round(request.credit_score/900 if request.credit_score is not None else 0.5, 2),
        message="Loan application created successfully.")

@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    raise HTTPException(status_code=400, detail=str(exc))
