"""
Rule-based heuristics for suspicious wallet behaviour.
Each rule adds a penalty to the rule_score (max 100).
"""
import pandas as pd


RULES = [
    # (column, operator, threshold, penalty_points, label)
    ("graph_fan_out_ratio",       ">",  10,   20, "high_fan_out"),
    ("temporal_burst_count",      ">=",  3,   25, "burst_activity"),
    ("temporal_night_fraction",   ">",  0.7,  15, "mostly_nocturnal"),
    ("wallet_round_ratio",        ">",  0.8,  20, "round_amounts"),
    ("graph_diversity_score",     "<",  0.05, 20, "low_diversity"),
    ("wallet_age_seconds",        "<",  86400, 15, "new_wallet"),    # < 1 day old
    ("temporal_tx_velocity",      ">",  50,   15, "high_velocity"),  # >50 tx/hr
]


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate rule set against feature DataFrame.
    Returns df with 'rule_score' and 'triggered_rules' columns.
    """
    result = df.copy()
    result["rule_score"]      = 0.0
    result["triggered_rules"] = ""

    for col, op, threshold, penalty, label in RULES:
        if col not in result.columns:
            continue

        if op == ">":
            mask = result[col] > threshold
        elif op == ">=":
            mask = result[col] >= threshold
        elif op == "<":
            mask = result[col] < threshold
        elif op == "<=":
            mask = result[col] <= threshold
        else:
            continue

        result.loc[mask, "rule_score"] += penalty
        result.loc[mask, "triggered_rules"] += label + ","

    # Cap at 100
    result["rule_score"] = result["rule_score"].clip(upper=100)
    result["triggered_rules"] = result["triggered_rules"].str.rstrip(",")
    return result
