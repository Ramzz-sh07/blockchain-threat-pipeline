"""
Wallet profile features: balance, age, value distribution, round-amount ratio.
"""
import pandas as pd
import numpy as np


def extract_wallet_profile(df: pd.DataFrame, wallet: str) -> dict:
    sent     = df[df["from"] == wallet]
    received = df[df["to"]   == wallet]

    total_sent     = sent["value"].sum()
    total_received = received["value"].sum()
    net_balance    = total_received - total_sent
    all_values     = pd.concat([sent["value"], received["value"]])

    # Round-amount ratio: suspiciously clean transfer amounts (e.g. exactly 1.0 ETH)
    if len(all_values) > 0:
        round_mask  = all_values.apply(lambda v: float(v) == round(float(v), 2) and float(v) > 0)
        round_ratio = round_mask.mean()
    else:
        round_ratio = 0.0

    # Value concentration: what fraction of total value is in the top 20% of txs
    if len(all_values) >= 5:
        threshold  = all_values.quantile(0.8)
        conc_ratio = all_values[all_values >= threshold].sum() / (all_values.sum() + 1e-9)
    else:
        conc_ratio = 0.0

    # Wallet age in seconds (span between first and last tx)
    timestamps = []
    if "timestamp" in df.columns:
        s_ts = sent["timestamp"].tolist()
        r_ts = received["timestamp"].tolist()
        timestamps = s_ts + r_ts
    wallet_age = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0

    return {
        "wallet_total_sent":     round(float(total_sent), 6),
        "wallet_total_received": round(float(total_received), 6),
        "wallet_net_balance":    round(float(net_balance), 6),
        "wallet_tx_count":       len(sent) + len(received),
        "wallet_round_ratio":    round(float(round_ratio), 4),
        "wallet_value_conc":     round(float(conc_ratio), 4),
        "wallet_age_seconds":    int(wallet_age),
    }


def extract_batch(df: pd.DataFrame) -> pd.DataFrame:
    wallets = pd.concat([df["from"], df["to"]]).dropna().unique()
    records = [{"wallet": w, **extract_wallet_profile(df, w)} for w in wallets]
    return pd.DataFrame(records)
