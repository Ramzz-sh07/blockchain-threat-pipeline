"""
Temporal features: transaction velocity, burst patterns, time-of-day signals.
"""
import pandas as pd
import numpy as np


def extract_temporal_features(df: pd.DataFrame, wallet: str) -> dict:
    """
    df must have columns: from, to, timestamp (Unix), value
    """
    sent     = df[df["from"] == wallet].copy()
    received = df[df["to"]   == wallet].copy()
    all_txs  = pd.concat([sent, received]).sort_values("timestamp")

    if all_txs.empty:
        return _empty_temporal_features()

    all_txs["dt"] = pd.to_datetime(all_txs["timestamp"], unit="s", utc=True)
    hours = all_txs["dt"].dt.hour

    # Inter-transaction gap stats (seconds)
    timestamps = all_txs["timestamp"].values
    gaps       = np.diff(timestamps) if len(timestamps) > 1 else np.array([0])

    # Burst detection: transactions within any 60-minute window
    bursts = 0
    for i, ts in enumerate(timestamps):
        window = timestamps[(timestamps >= ts) & (timestamps < ts + 3600)]
        if len(window) >= 5:
            bursts += 1

    # Nocturnality: fraction of txs between midnight and 6am UTC
    night_frac = (hours < 6).mean()

    # Sending velocity (txs per hour over the observed window)
    obs_hours = max((timestamps[-1] - timestamps[0]) / 3600, 1)
    tx_velocity = len(all_txs) / obs_hours

    return {
        "temporal_tx_count":       len(all_txs),
        "temporal_sent_count":     len(sent),
        "temporal_recv_count":     len(received),
        "temporal_gap_mean_s":     round(float(gaps.mean()), 2),
        "temporal_gap_min_s":      round(float(gaps.min()), 2),
        "temporal_gap_std_s":      round(float(gaps.std()), 2) if len(gaps) > 1 else 0,
        "temporal_burst_count":    bursts,
        "temporal_night_fraction": round(float(night_frac), 4),
        "temporal_tx_velocity":    round(float(tx_velocity), 4),
    }


def extract_batch(df: pd.DataFrame) -> pd.DataFrame:
    wallets = pd.concat([df["from"], df["to"]]).dropna().unique()
    records = [{"wallet": w, **extract_temporal_features(df, w)} for w in wallets]
    return pd.DataFrame(records)


def _empty_temporal_features() -> dict:
    keys = ["tx_count","sent_count","recv_count","gap_mean_s","gap_min_s",
            "gap_std_s","burst_count","night_fraction","tx_velocity"]
    return {f"temporal_{k}": 0 for k in keys}
