"""
Weighted ensemble risk scorer.
Combines Isolation Forest score with rule-based flags into a final 0-100 score.
"""
import pandas as pd
from detection.models.isolation_forest import score_wallets, load
from detection.rules.heuristics import apply_rules
from config.settings import RISK_THRESHOLD

# Weight split between ML score and rule-based flags
ML_WEIGHT   = 0.65
RULE_WEIGHT = 0.35


def score(feature_df: pd.DataFrame) -> pd.DataFrame:
    model, scaler = load()

    # ML score (0-100)
    ml_df = score_wallets(feature_df, model, scaler)

    # Rule-based flag score (0-100, each triggered rule adds points)
    rule_df = apply_rules(feature_df)

    combined = ml_df.copy()
    combined["rule_score"]  = rule_df["rule_score"]
    combined["final_score"] = (
        ML_WEIGHT   * combined["risk_score"] +
        RULE_WEIGHT * combined["rule_score"]
    ).round(2)
    combined["flagged"] = combined["final_score"] >= RISK_THRESHOLD

    return combined[["wallet", "risk_score", "rule_score", "final_score", "flagged"]]
