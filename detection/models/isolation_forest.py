"""
Isolation Forest anomaly detector for wallet feature vectors.
Trains on unlabelled data; anomaly score maps to 0-100 risk.
"""
import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from config.settings import MODEL_PATH

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "graph_in_degree", "graph_out_degree", "graph_diversity_score", "graph_fan_out_ratio",
    "temporal_tx_count", "temporal_burst_count", "temporal_night_fraction", "temporal_tx_velocity",
    "wallet_round_ratio", "wallet_value_conc", "wallet_age_seconds",
]


def train(df: pd.DataFrame, contamination: float = 0.05) -> tuple:
    """
    Train Isolation Forest on wallet feature DataFrame.
    Returns (model, scaler).
    """
    X = df[FEATURE_COLS].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    logger.info("IsolationForest trained on %d wallets", len(X))
    return model, scaler


def save(model, scaler, path: str = MODEL_PATH):
    joblib.dump({"model": model, "scaler": scaler, "features": FEATURE_COLS}, path)
    logger.info("Model saved to %s", path)


def load(path: str = MODEL_PATH) -> tuple:
    bundle = joblib.load(path)
    return bundle["model"], bundle["scaler"]


def score_wallets(df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """
    Score a DataFrame of wallet features.
    Adds 'anomaly_score' (raw IF score) and 'risk_score' (0-100).
    """
    X = df[FEATURE_COLS].fillna(0).values
    X_scaled = scaler.transform(X)

    # IF returns -1 (anomaly) or 1 (normal); decision_function gives raw score
    raw_scores = model.decision_function(X_scaled)   # more negative = more anomalous

    # Normalise to 0-100: invert so higher = riskier
    min_s, max_s = raw_scores.min(), raw_scores.max()
    risk = 100 * (1 - (raw_scores - min_s) / (max_s - min_s + 1e-9))

    result = df.copy()
    result["anomaly_score"] = raw_scores
    result["risk_score"]    = np.round(risk, 2)
    return result
