"""Unit tests for detection rules."""
import pandas as pd
from detection.rules.heuristics import apply_rules

FEATURE_DF = pd.DataFrame([
    {
        "wallet": "0xSuspicious",
        "graph_fan_out_ratio":      15,    # triggers high_fan_out
        "temporal_burst_count":      4,    # triggers burst_activity
        "temporal_night_fraction":   0.9,  # triggers mostly_nocturnal
        "wallet_round_ratio":        0.95, # triggers round_amounts
        "graph_diversity_score":     0.02, # triggers low_diversity
        "wallet_age_seconds":        3600, # triggers new_wallet
        "temporal_tx_velocity":      60,   # triggers high_velocity
    },
    {
        "wallet": "0xNormal",
        "graph_fan_out_ratio":      1.2,
        "temporal_burst_count":      0,
        "temporal_night_fraction":   0.3,
        "wallet_round_ratio":        0.2,
        "graph_diversity_score":     0.6,
        "wallet_age_seconds":        9_000_000,
        "temporal_tx_velocity":      0.5,
    },
])


def test_suspicious_wallet_score():
    result = apply_rules(FEATURE_DF)
    sus = result[result["wallet"] == "0xSuspicious"].iloc[0]
    assert sus["rule_score"] == 100   # all rules fire, capped at 100


def test_normal_wallet_score():
    result = apply_rules(FEATURE_DF)
    norm = result[result["wallet"] == "0xNormal"].iloc[0]
    assert norm["rule_score"] == 0
