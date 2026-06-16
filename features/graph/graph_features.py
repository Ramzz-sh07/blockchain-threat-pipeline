"""
Graph-based wallet features using NetworkX.
Builds a directed transaction graph and extracts structural metrics.
"""
import networkx as nx
import pandas as pd
import numpy as np


def build_transaction_graph(df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed graph from a transactions DataFrame.
    Expected columns: from, to, value
    """
    G = nx.DiGraph()
    for _, row in df.iterrows():
        if row["from"] and row["to"]:
            G.add_edge(row["from"], row["to"], weight=row["value"])
    return G


def extract_graph_features(G: nx.DiGraph, wallet: str) -> dict:
    """
    Compute graph metrics for a single wallet address.
    Returns a flat dict of features.
    """
    if wallet not in G:
        return _empty_graph_features()

    in_degree   = G.in_degree(wallet)
    out_degree  = G.out_degree(wallet)
    in_weights  = [d["weight"] for _, _, d in G.in_edges(wallet, data=True)]
    out_weights = [d["weight"] for _, _, d in G.out_edges(wallet, data=True)]

    # Ratio of unique counterparties to total transactions (diversity score)
    neighbors      = set(G.predecessors(wallet)) | set(G.successors(wallet))
    total_txs      = in_degree + out_degree
    diversity      = len(neighbors) / total_txs if total_txs > 0 else 0

    # Fan-out ratio: high = wallet distributes to many recipients (mixing signal)
    fan_out = out_degree / (in_degree + 1)

    return {
        "graph_in_degree":       in_degree,
        "graph_out_degree":      out_degree,
        "graph_total_degree":    total_txs,
        "graph_in_value_sum":    sum(in_weights),
        "graph_out_value_sum":   sum(out_weights),
        "graph_in_value_mean":   np.mean(in_weights) if in_weights else 0,
        "graph_out_value_mean":  np.mean(out_weights) if out_weights else 0,
        "graph_unique_neighbors": len(neighbors),
        "graph_diversity_score": round(diversity, 4),
        "graph_fan_out_ratio":   round(fan_out, 4),
    }


def extract_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Extract graph features for every unique wallet in the DataFrame."""
    G       = build_transaction_graph(df)
    wallets = pd.concat([df["from"], df["to"]]).dropna().unique()
    records = [{"wallet": w, **extract_graph_features(G, w)} for w in wallets]
    return pd.DataFrame(records)


def _empty_graph_features() -> dict:
    keys = ["in_degree","out_degree","total_degree","in_value_sum","out_value_sum",
            "in_value_mean","out_value_mean","unique_neighbors","diversity_score","fan_out_ratio"]
    return {f"graph_{k}": 0 for k in keys}
