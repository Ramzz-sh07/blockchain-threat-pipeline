
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import networkx as nx
import joblib
from db.mongo import upsert_wallets, create_indexes
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models")
PROC_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")

NATIVE_FEATURE_COUNT = 165
GRAPH_FEATURE_COLS = ["graph_in_degree", "graph_out_degree", "graph_diversity_score", "graph_fan_out_ratio"]


def load_raw():
    logger.info("Loading Elliptic CSVs...")
    features = pd.read_csv(os.path.join(RAW_DIR, "elliptic_txs_features.csv"), header=None)
    classes  = pd.read_csv(os.path.join(RAW_DIR, "elliptic_txs_classes.csv"))
    edges    = pd.read_csv(os.path.join(RAW_DIR, "elliptic_txs_edgelist.csv"))

    features.columns = ["txId", "time_step"] + [f"f_{i}" for i in range(features.shape[1] - 2)]
    classes.columns   = ["txId", "class"]
    edges.columns     = ["txId1", "txId2"]

    logger.info("Features: %s | Classes: %s | Edges: %s", features.shape, classes.shape, edges.shape)
    return features, classes, edges


def build_graph(edges: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_edges_from(edges[["txId1", "txId2"]].itertuples(index=False, name=None))
    return G


def add_graph_features(features: pd.DataFrame, G: nx.DiGraph) -> pd.DataFrame:
    logger.info("Computing graph features from edgelist...")
    records = []
    for tx_id in features["txId"]:
        in_deg, out_deg = 0, 0
        diversity, fan_out = 0.0, 0.0
        if tx_id in G:
            in_deg  = G.in_degree(tx_id)
            out_deg = G.out_degree(tx_id)
            neighbors = set(G.predecessors(tx_id)) | set(G.successors(tx_id))
            total = in_deg + out_deg
            diversity = len(neighbors) / total if total > 0 else 0
            fan_out   = out_deg / (in_deg + 1)
        records.append({
            "txId": tx_id,
            "graph_in_degree": in_deg,
            "graph_out_degree": out_deg,
            "graph_diversity_score": round(diversity, 4),
            "graph_fan_out_ratio": round(fan_out, 4),
        })
    graph_df = pd.DataFrame(records)
    return features.merge(graph_df, on="txId", how="left")


def main():
    features, classes, edges = load_raw()
    G = build_graph(edges)
    feat_df = add_graph_features(features, G)
    feat_df = feat_df.merge(classes, on="txId", how="left")

    native_cols  = [f"f_{i}" for i in range(NATIVE_FEATURE_COUNT)]
    feature_cols = native_cols + GRAPH_FEATURE_COLS

    labelled = feat_df[feat_df["class"].isin(["1", "2"])].copy()
    labelled["y"] = (labelled["class"] == "1").astype(int)

    X = labelled[feature_cols].fillna(0).values
    y = labelled["y"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    logger.info("Training Random Forest on %d labelled transactions (%d illicit)...",
                len(X_train), y_train.sum())
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=20, class_weight="balanced",
        random_state=42, n_jobs=-1
    )
    rf.fit(X_train_scaled, y_train)

    y_pred  = rf.predict(X_test_scaled)
    y_proba = rf.predict_proba(X_test_scaled)[:, 1]

    logger.info("Random Forest evaluation on %d held-out transactions:", len(X_test))
    print(classification_report(y_test, y_pred, target_names=["licit", "illicit"]))
    auc = roc_auc_score(y_test, y_proba)
    logger.info("ROC-AUC: %.3f", auc)
    logger.info("Confusion matrix:\n%s", confusion_matrix(y_test, y_pred))

    logger.info("Training Isolation Forest on all %d transactions (unsupervised)...", len(feat_df))
    X_all = feat_df[feature_cols].fillna(0).values
    X_all_scaled = StandardScaler().fit_transform(X_all)
    iso = IsolationForest(n_estimators=200, contamination=0.1, random_state=42, n_jobs=-1)
    iso.fit(X_all_scaled)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(
        {"model": rf, "scaler": scaler, "features": feature_cols},
        os.path.join(MODEL_DIR, "random_forest.pkl"),
    )
    joblib.dump(
        {"model": iso, "scaler": scaler, "features": feature_cols},
        os.path.join(MODEL_DIR, "isolation_forest.pkl"),
    )
    logger.info("Models saved to data/models/")

    X_all_for_rf = scaler.transform(feat_df[feature_cols].fillna(0).values)
    risk_scores  = rf.predict_proba(X_all_for_rf)[:, 1] * 100

    os.makedirs(PROC_DIR, exist_ok=True)
    out = feat_df[["txId", "class"]].copy()
    out.columns = ["wallet", "true_class"]
    out["risk_score"] = np.round(risk_scores, 2)
    out["flagged"]    = out["risk_score"] >= 70
    out.to_csv(os.path.join(PROC_DIR, "wallet_scores.csv"), index=False)
    logger.info("Saved %d scored wallets to data/processed/wallet_scores.csv", len(out))
    logger.info("Flagged: %d wallets (risk_score >= 70)", out["flagged"].sum())

    # Write to MongoDB
    out["wallet"] = out["wallet"].astype(str)
    records = out.to_dict("records")
    logger.info("Writing %d wallet records to MongoDB...", len(records))
    create_indexes()
    upsert_wallets(records)
    logger.info("MongoDB write complete.")


if __name__ == "__main__":
    main()
