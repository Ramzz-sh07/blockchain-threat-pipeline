"""
Rule-based heuristics for suspicious wallet behaviour, organized into
named threat categories rather than raw individual rule flags.

Categories:
- money_laundering : layering patterns (high fan-out, low counterparty diversity)
- scam_wallet       : new-wallet + high-velocity + round-amount rug-pull signature
- high_risk_tx      : driven primarily by the ML model's risk score
- abnormal_spike    : sudden burst of transaction activity
"""
import pandas as pd

# Each category has its own weighted rules. Points are summed and capped at 100.
CATEGORY_RULES = {
    "money_laundering": [
        ("graph_fan_out_ratio",   ">",  10,   40),
        ("graph_diversity_score", "<",  0.05, 35),
        ("wallet_round_ratio",    ">",  0.8,  25),
    ],
    "scam_wallet": [
        ("wallet_age_seconds",      "<", 86400, 40),   # < 1 day old
        ("temporal_tx_velocity",    ">", 50,    35),
        ("wallet_round_ratio",      ">", 0.8,   25),
    ],
    "abnormal_spike": [
        ("temporal_burst_count",  ">=", 3,  60),
        ("temporal_tx_velocity",  ">",  50, 40),
    ],
}


def _score_category(row: pd.Series, rules: list) -> tuple[float, list]:
    score = 0.0
    triggered = []
    for col, op, threshold, points in rules:
        if col not in row:
            continue
        value = row[col]
        fired = (
            (op == ">"  and value > threshold) or
            (op == ">=" and value >= threshold) or
            (op == "<"  and value < threshold) or
            (op == "<=" and value <= threshold)
        )
        if fired:
            score += points
            triggered.append(col)
    return min(score, 100), triggered


def classify_wallet(row: pd.Series, ml_risk_score: float = 0.0) -> dict:
    """
    Score a single wallet's feature row against all threat categories.
    Returns a dict with per-category scores and the dominant category.
    """
    results = {}
    for category, rules in CATEGORY_RULES.items():
        score, triggered = _score_category(row, rules)
        results[category] = {"score": score, "triggered_signals": triggered}

    # high_risk_tx is driven by the ML model directly, not hand-written rules
    results["high_risk_tx"] = {"score": ml_risk_score, "triggered_signals": ["ml_model"] if ml_risk_score >= 70 else []}

    # Dominant category = highest scoring one (only if above a minimum threshold)
    dominant = max(results.items(), key=lambda kv: kv[1]["score"])
    dominant_category = dominant[0] if dominant[1]["score"] >= 50 else None

    return {
        "categories": results,
        "dominant_category": dominant_category,
        "rule_score": max(r["score"] for r in results.values()),
    }


def apply_rules(df: pd.DataFrame, ml_scores: dict | None = None) -> pd.DataFrame:
    """
    Evaluate the full category rule set against a feature DataFrame.
    ml_scores: optional dict mapping wallet -> ml risk_score, used for the
    high_risk_tx category.
    """
    ml_scores = ml_scores or {}
    result = df.copy()
    result["rule_score"] = 0.0
    result["dominant_category"] = None
    result["triggered_rules"] = ""

    category_cols = {cat: [] for cat in list(CATEGORY_RULES.keys()) + ["high_risk_tx"]}

    for idx, row in result.iterrows():
        wallet = row.get("wallet", "")
        ml_score = ml_scores.get(wallet, 0.0)
        classification = classify_wallet(row, ml_score)

        result.at[idx, "rule_score"] = classification["rule_score"]
        result.at[idx, "dominant_category"] = classification["dominant_category"]
        result.at[idx, "triggered_rules"] = ",".join(
            sig for cat in classification["categories"].values() for sig in cat["triggered_signals"]
        )
        for cat, data in classification["categories"].items():
            category_cols[cat].append(data["score"])

    for cat, scores in category_cols.items():
        result[f"score_{cat}"] = scores

    return result
