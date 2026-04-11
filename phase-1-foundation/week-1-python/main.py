from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": "foundation", "day": 1, "hour": 0} 
