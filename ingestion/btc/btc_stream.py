"""
Bitcoin live transaction streamer via ZMQ raw-tx socket.
Emits decoded transactions to Kafka topic.
"""
import json
import logging
import struct
import requests
from kafka import KafkaProducer
from config.settings import BTC_RPC_HOST, BTC_RPC_PORT, BTC_RPC_USER, BTC_RPC_PASS, KAFKA_BOOTSTRAP, KAFKA_TOPIC_RAW

logger = logging.getLogger(__name__)

RPC_URL = f"http://{BTC_RPC_HOST}:{BTC_RPC_PORT}"


def rpc_call(method: str, params: list = None) -> dict:
    payload = {"jsonrpc": "1.0", "id": "btc-stream", "method": method, "params": params or []}
    resp = requests.post(RPC_URL, json=payload, auth=(BTC_RPC_USER, BTC_RPC_PASS), timeout=10)
    resp.raise_for_status()
    return resp.json()["result"]


def normalize_btc_tx(raw_tx: dict) -> dict:
    total_out = sum(v.get("value", 0) for v in raw_tx.get("vout", []))
    senders   = [i.get("txid", "") for i in raw_tx.get("vin", [])]
    receivers = [v["scriptPubKey"].get("address", "") for v in raw_tx.get("vout", []) if "address" in v.get("scriptPubKey", {})]
    return {
        "chain":      "BTC",
        "hash":       raw_tx["txid"],
        "from":       senders[0] if senders else "",
        "to":         receivers[0] if receivers else "",
        "value":      total_out,
        "input_count":  len(raw_tx.get("vin", [])),
        "output_count": len(raw_tx.get("vout", [])),
        "size":       raw_tx.get("size", 0),
    }


def stream_mempool_transactions():
    """Poll Bitcoin mempool for new transactions and push to Kafka."""
    producer   = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    seen: set[str] = set()

    logger.info("BTC streamer started — polling mempool")
    while True:
        try:
            mempool_txids = rpc_call("getrawmempool")
            new_txids     = [txid for txid in mempool_txids if txid not in seen]
            for txid in new_txids[:50]:   # batch cap to avoid flooding
                try:
                    raw = rpc_call("getrawtransaction", [txid, True])
                    data = normalize_btc_tx(raw)
                    producer.send(KAFKA_TOPIC_RAW, value=data)
                    seen.add(txid)
                except Exception as exc:
                    logger.warning("Skipped BTC tx %s: %s", txid, exc)
            import time; time.sleep(5)
        except Exception as exc:
            logger.error("Mempool poll error: %s", exc)
            import time; time.sleep(15)
