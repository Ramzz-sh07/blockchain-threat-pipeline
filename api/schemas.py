from pydantic import BaseModel
from typing import Optional


class WalletRiskResponse(BaseModel):
    wallet:        str
    risk_score:    float
    rule_score:    float
    final_score:   float
    flagged:       bool
    triggered_rules: Optional[str] = ""


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
