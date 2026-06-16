import pandas as pd
from fastapi import APIRouter, HTTPException
from api.schemas import WalletRiskResponse, HealthResponse
from features.graph.graph_features      import extract_graph_features, build_transaction_graph
from detection.models.risk_scorer       import score

router = APIRouter()

# In production this would query your DB / feature store.
# For the portfolio demo, we use a lightweight in-memory lookup.
_score_cache: dict[str, dict] = {}


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@router.get("/wallet/{address}", response_model=WalletRiskResponse)
def get_wallet_risk(address: str):
    """Return the latest risk score for a wallet address."""
    if address in _score_cache:
        return _score_cache[address]
    raise HTTPException(status_code=404, detail=f"No data found for wallet {address}")


@router.get("/flagged")
def get_flagged_wallets(limit: int = 50):
    """Return the top N highest-scoring flagged wallets."""
    flagged = [v for v in _score_cache.values() if v.get("flagged")]
    flagged.sort(key=lambda x: x["final_score"], reverse=True)
    return {"count": len(flagged), "wallets": flagged[:limit]}


def update_cache(scored_df: pd.DataFrame):
    """Called by the pipeline to keep the API cache fresh."""
    for _, row in scored_df.iterrows():
        _score_cache[row["wallet"]] = row.to_dict()
