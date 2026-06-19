from fastapi import APIRouter, HTTPException
from api.schemas import WalletRiskResponse, HealthResponse
from db.mongo import get_wallet, get_flagged_wallets, count_wallets

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@router.get("/wallet/{address}", response_model=WalletRiskResponse)
def get_wallet_risk(address: str):
    """Return the latest risk score for a wallet address, from MongoDB."""
    doc = get_wallet(address)
    if doc:
        return {
            "wallet": doc["wallet"],
            "risk_score": doc.get("risk_score", 0.0),
            "rule_score": 0.0,
            "final_score": doc.get("risk_score", 0.0),
            "flagged": doc.get("flagged", False),
            "triggered_rules": "",
        }
    raise HTTPException(status_code=404, detail=f"No data found for wallet {address}")


@router.get("/flagged")
def get_flagged(limit: int = 50):
    """Return the top N highest-risk flagged wallets, from MongoDB."""
    docs = get_flagged_wallets(limit=limit)
    wallets = [
        {
            "wallet": d["wallet"],
            "risk_score": d.get("risk_score", 0.0),
            "rule_score": 0.0,
            "final_score": d.get("risk_score", 0.0),
            "flagged": d.get("flagged", False),
            "triggered_rules": "",
        }
        for d in docs
    ]
    return {"count": len(wallets), "wallets": wallets}


@router.get("/stats")
def get_stats():
    """Total wallets tracked in the database."""
    return {"total_wallets": count_wallets()}
