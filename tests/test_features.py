"""Unit tests for feature extraction."""
import pytest
import pandas as pd
from features.graph.graph_features       import extract_graph_features, build_transaction_graph
from features.temporal.temporal_features import extract_temporal_features
from features.wallet.wallet_profile      import extract_wallet_profile

SAMPLE_TXS = pd.DataFrame([
    {"from": "0xAlice", "to": "0xBob",   "value": 1.0,  "timestamp": 1_700_000_000},
    {"from": "0xAlice", "to": "0xCarol", "value": 1.0,  "timestamp": 1_700_000_060},
    {"from": "0xAlice", "to": "0xDave",  "value": 1.0,  "timestamp": 1_700_000_120},
    {"from": "0xBob",   "to": "0xAlice", "value": 2.5,  "timestamp": 1_700_001_000},
    {"from": "0xCarol", "to": "0xAlice", "value": 0.5,  "timestamp": 1_700_002_000},
])


def test_graph_features_alice():
    G = build_transaction_graph(SAMPLE_TXS)
    f = extract_graph_features(G, "0xAlice")
    assert f["graph_out_degree"] == 3
    assert f["graph_in_degree"]  == 2
    assert f["graph_fan_out_ratio"] >= 1


def test_graph_features_unknown_wallet():
    G = build_transaction_graph(SAMPLE_TXS)
    f = extract_graph_features(G, "0xNobody")
    assert all(v == 0 for v in f.values())


def test_temporal_features():
    f = extract_temporal_features(SAMPLE_TXS, "0xAlice")
    assert f["temporal_sent_count"] == 3
    assert f["temporal_recv_count"] == 2
    assert f["temporal_tx_count"]   == 5


def test_wallet_profile_round_ratio():
    f = extract_wallet_profile(SAMPLE_TXS, "0xAlice")
    # All sent values are exactly 1.0 — round ratio should be high
    assert f["wallet_round_ratio"] > 0.5
    assert f["wallet_total_sent"]  == pytest.approx(3.0)
