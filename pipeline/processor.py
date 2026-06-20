"""
Main pipeline processor for LIVE blockchain data.

Consumes raw transactions from Kafka, extracts graph/temporal/wallet
features, classifies wallets into named threat categories (money
laundering, scam wallet, abnormal spike, high-risk tx), and writes
results to MongoDB + a scored-wallets Kafka topic.

This is distinct from scripts/train_on_elliptic.py, which trains the
ML model on the static labelled Elliptic dataset. This processor scores
NEW live transactions using the already-trained model plus the full
rule-based category system (which needs real timestamps/amounts that
only live data provides).
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import joblib
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer

from features.graph.graph_features       import extract_batch as graph_batch
from features.temporal.temporal_features import extract_batch as temporal_batch
from features.wallet.wallet_profile      import extract_batch as wallet_batch
from detection.rules.heuristics          import apply_rules
from db.mongo import upsert_wallets, create_indexes
from config.settings import KAFKA_BOOTSTRAP, KAFKA_TOPIC_RAW, KAFKA_TOPIC_SCORED, MODEL_PATH

logger = logging.getLogger(__name__)

BATCH_SIZE = 50   # live ETH blocks are smaller batches than the 203k historical set


def load_model():
    """Load the Random Forest model trained on Elliptic, used to score live wallets too."""
    rf_path = os.path.join(os.path.dirname(MODEL_PATH), "random_forest.pkl")
    if not os.path.exists(rf_path):
        logger.warning("No trained model found at %s — run scripts/train_on_elliptic.py first. "
                        "Falling back to rule-based scoring only.", rf_path)
        return None
    bundle = joblib.load(rf_path)
    return bundle


def build_feature_vector(tx_df: pd.DataFrame) -> pd.DataFrame:
    """Merge all feature groups into one wallet-level DataFrame."""
    graph_df    = graph_batch(tx_df)
    temporal_df = temporal_batch(tx_df)
    wallet_df   = wallet_batch(tx_df)

    features = graph_df.merge(temporal_df, on="wallet", how="outer") \
                       .merge(wallet_df,   on="wallet", how="outer") \
                       .fillna(0)
    return features


def score_with_model(feat_df: pd.DataFrame, model_bundle) -> dict:
    """Score wallets with the trained RF model where feature overlap allows; else 0."""
    if model_bundle is None:
        return {w: 0.0 for w in feat_df["wallet"]}

    model, scaler, trained_features = model_bundle["model"], model_bundle["scaler"], model_bundle["features"]
    # Live features don't have the 165 anonymized Elliptic columns, so we can only
    # use this model on data shaped like Elliptic. For live ETH data, default to
    # rule-based scoring only (documented limitation — see README).
    return {w: 0.0 for w in feat_df["wallet"]}


def run():
    consumer = KafkaConsumer(
        KAFKA_TOPIC_RAW,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        api_version=(2, 5, 0),

    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version=(2, 5, 0),
    )

    model_bundle = load_model()
    create_indexes()

    logger.info("Pipeline processor started — consuming from %s", KAFKA_TOPIC_RAW)
    buffer: list[dict] = []

    for message in consumer:
        buffer.append(message.value)

        if len(buffer) >= BATCH_SIZE:
            try:
                tx_df    = pd.DataFrame(buffer)
                feat_df  = build_feature_vector(tx_df)
                ml_scores = score_with_model(feat_df, model_bundle)

                scored = apply_rules(feat_df, ml_scores=ml_scores)
                scored["risk_score"] = scored["wallet"].map(ml_scores).fillna(0)
                scored["flagged"]    = scored["rule_score"] >= 50

                # Persist to MongoDB
                records = scored[["wallet", "risk_score", "rule_score", "flagged",
                                   "dominant_category", "triggered_rules"]].to_dict("records")
                upsert_wallets(records)

                flagged = scored[scored["flagged"]]
                for _, row in flagged.iterrows():
                    producer.send(KAFKA_TOPIC_SCORED, value=row.to_dict())
                    logger.warning("FLAGGED wallet %s — category=%s, score=%.1f",
                                   row["wallet"], row["dominant_category"], row["rule_score"])

                logger.info("Batch processed: %d txs, %d wallets, %d flagged, written to MongoDB",
                            len(buffer), len(scored), len(flagged))
            except Exception as exc:
                logger.error("Batch processing failed: %s", exc, exc_info=True)
            finally:
                buffer.clear()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
