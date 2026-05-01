from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from models import LoanApplicationRequest, loanApplicationResponse
from uuid import uuid4
from logging_config import setup_logger, correlation_id_var
from http_client import AsyncHttpClient
import logging

app = FastAPI(title="Fintech AI Platform", version="0.1.0")
logger = setup_logger()

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "fintech-ai-platform"} 
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id= request.headers.get("X-Correlation-ID", str(uuid4()))
        correlation_id_var.set(correlation_id)
        response= await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
app.add_middleware(CorrelationIdMiddleware)

async def get_http_client():
    async with AsyncHttpClient("https://httpbin.org") as client:
        yield client

@app.post("/createLoanApplication",  response_model=loanApplicationResponse)
async def createLoanApplication(request: LoanApplicationRequest, client: AsyncHttpClient = Depends(get_http_client)) -> loanApplicationResponse:
    logger.info(f"Processing application for {request.mobileNo}")
    if request.credit_score < 600:
        logger.warning(f"Credit score too low: {request.credit_score}")
        raise HTTPException(status_code=422, detail="Credit score must be greater than 600")  
    app_id = str(uuid4())  
    logger.info(f"Application ID: {app_id} created successfully")
    return loanApplicationResponse(
        leadId= app_id, 
        status= "pending",
        eligibility_score= round(request.credit_score/900 if request.credit_score is not None else 0.5, 2),
        message= "Loan application created successfully.")

@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    raise HTTPException(status_code=400, detail=str(exc))