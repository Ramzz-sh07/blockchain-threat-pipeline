"""
FastAPI application entry point.
Run with: uvicorn api.main:app --reload
"""
from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="Blockchain Threat Detection API",
    description="Real-time wallet risk scoring for ETH and BTC transactions.",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Blockchain Threat Detection API — see /docs"}
