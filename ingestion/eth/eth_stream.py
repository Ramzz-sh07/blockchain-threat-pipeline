"""
Ethereum live transaction streamer.

Note: Infura's free tier does not support eth_newPendingTransactionFilter
(mempool watching), which is a paid-tier feature on most node providers.
Instead, this streamer polls for newly CONFIRMED blocks and extracts their
transactions — a more stable signal anyway, since pending transactions can
be replaced or dropped before confirmation. This is a standard approach in
production fraud-detection systems that prioritize confirmed-chain data.
"""
import json
import logging
import time
from web3 import Web3
from kafka import KafkaProducer
from config.settings import ETH_WS_URL, ETH_RPC_URL, KAFKA_BOOTSTRAP, KAFKA_TOPIC_RAW

logger = logging.getLogger(__name__)


def get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version=(2, 5, 0),
    )

def get_web3() -> Web3:
    """Create a Web3 instance connected via HTTP (works on free tier)."""
    return Web3(Web3.HTTPProvider(ETH_RPC_URL))


def normalize_eth_tx(tx, block_timestamp: int) -> dict:
    """Convert a Web3 transaction object to a flat dict."""
    return {
        "chain": "ETH",
        "hash":  tx.hash.hex(),
        "from":  tx["from"],
        "to":    tx.get("to", "") or "",
        "value": float(Web3.from_wei(tx.value, "ether")),
        "gas":   tx.gas,
        "gas_price": float(Web3.from_wei(tx.gasPrice, "gwei")),
        "block": tx.get("blockNumber"),
        "timestamp": block_timestamp,
        "input_data": tx.input.hex()[:64] if tx.input else "",
    }


def stream_confirmed_blocks(poll_interval: int = 12):
    """
    Poll for new confirmed blocks (Ethereum produces a block roughly every
    12 seconds) and push each transaction to Kafka. Run this in a dedicated
    process / thread.
    """
    w3       = get_web3()
    producer = get_producer()

    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to ETH node: {ETH_RPC_URL}")

    last_block = w3.eth.block_number
    logger.info("ETH streamer connected — starting from block %d", last_block)

    while True:
        try:
            latest = w3.eth.block_number
            if latest > last_block:
                for block_num in range(last_block + 1, latest + 1):
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    logger.info("Block %d: %d transactions", block_num, len(block.transactions))
                    for tx in block.transactions:
                        try:
                            data = normalize_eth_tx(tx, block.timestamp)
                            producer.send(KAFKA_TOPIC_RAW, value=data)
                        except Exception as exc:
                            logger.warning("Skipped tx %s: %s", tx.hash.hex(), exc)
                last_block = latest
        except Exception as exc:
            logger.error("Block poll error: %s", exc)
        time.sleep(poll_interval)


# Backward-compatible alias
stream_pending_transactions = stream_confirmed_blocks
