"""
Ethereum live transaction streamer.
Connects via WebSocket, emits pending transactions to Kafka.
"""
import json
import logging
from web3 import Web3
from kafka import KafkaProducer
from config.settings import ETH_WS_URL, KAFKA_BOOTSTRAP, KAFKA_TOPIC_RAW

logger = logging.getLogger(__name__)


def get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def normalize_eth_tx(tx) -> dict:
    """Convert a Web3 transaction object to a flat dict."""
    return {
        "chain": "ETH",
        "hash":  tx.hash.hex(),
        "from":  tx["from"],
        "to":    tx.get("to", ""),
        "value": float(Web3.from_wei(tx.value, "ether")),
        "gas":   tx.gas,
        "gas_price": float(Web3.from_wei(tx.gasPrice, "gwei")),
        "block": tx.get("blockNumber"),
        "input_data": tx.input.hex()[:64],   # first 32 bytes only
    }


def stream_pending_transactions():
    """
    Subscribe to newPendingTransactions filter and push each tx to Kafka.
    Run this in a dedicated process / thread.
    """
    w3       = Web3(Web3.WebsocketProvider(ETH_WS_URL))
    producer = get_producer()

    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to ETH node: {ETH_WS_URL}")

    logger.info("ETH streamer connected — listening for pending transactions")
    tx_filter = w3.eth.filter("pending")

    while True:
        for tx_hash in tx_filter.get_new_entries():
            try:
                tx   = w3.eth.get_transaction(tx_hash)
                data = normalize_eth_tx(tx)
                producer.send(KAFKA_TOPIC_RAW, value=data)
                logger.debug("ETH tx published: %s", data["hash"])
            except Exception as exc:
                logger.warning("Skipped tx %s: %s", tx_hash.hex(), exc)
