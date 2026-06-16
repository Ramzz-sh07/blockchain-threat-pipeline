"""
Main pipeline processor.
Consumes raw transactions from Kafka, extracts features,
scores wallets, and writes results back to Kafka + DB.
"""
import json
import logging
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from features.graph.graph_features      import extract_batch as graph_batch
from features.temporal.temporal_features import extract_batch as temporal_batch
from features.wallet.wallet_profile      import extract_batch as wallet_batch
from detection.models.risk_scorer        import score
from config.settings import KAFKA_BOOTSTRAP, KAFKA_TOPIC_RAW, KAFKA_TOPIC_SCORED

logger = logging.getLogger(__name__)

BATCH_SIZE = 500   # process in rolling windows of N transactions


def build_feature_vector(tx_df: pd.DataFrame) -> pd.DataFrame:
    """Merge all feature groups into one wallet-level DataFrame."""
    graph_df    = graph_batch(tx_df)
    temporal_df = temporal_batch(tx_df)
    wallet_df   = wallet_batch(tx_df)

    features = graph_df.merge(temporal_df, on="wallet", how="outer") \
                       .merge(wallet_df,   on="wallet", how="outer") \
                       .fillna(0)
    return features


def run():
    consumer = KafkaConsumer(
        KAFKA_TOPIC_RAW,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    logger.info("Pipeline processor started — consuming from %s", KAFKA_TOPIC_RAW)
    buffer: list[dict] = []

    for message in consumer:
        buffer.append(message.value)

        if len(buffer) >= BATCH_SIZE:
            try:
                tx_df    = pd.DataFrame(buffer)
                feat_df  = build_feature_vector(tx_df)
                scored   = score(feat_df)
                flagged  = scored[scored["flagged"]]

                for _, row in flagged.iterrows():
                    producer.send(KAFKA_TOPIC_SCORED, value=row.to_dict())
                    logger.warning("FLAGGED wallet %s — score %.1f", row["wallet"], row["final_score"])

                logger.info("Batch processed: %d txs, %d wallets, %d flagged",
                            len(buffer), len(scored), len(flagged))
            except Exception as exc:
                logger.error("Batch processing failed: %s", exc)
            finally:
                buffer.clear()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
