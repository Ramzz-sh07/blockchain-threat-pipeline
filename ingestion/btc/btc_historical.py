"""
Fetch historical Bitcoin transactions for a block range.
"""
import logging
import time
from ingestion.btc.btc_stream import rpc_call

logger = logging.getLogger(__name__)


def fetch_block_transactions(block_hash: str) -> list[dict]:
    block = rpc_call("getblock", [block_hash, 2])   # verbosity=2 includes tx data
    txs   = []
    for tx in block.get("tx", []):
        total_out = sum(v.get("value", 0) for v in tx.get("vout", []))
        txs.append({
            "chain":        "BTC",
            "hash":         tx["txid"],
            "value":        total_out,
            "input_count":  len(tx.get("vin", [])),
            "output_count": len(tx.get("vout", [])),
            "block":        block["height"],
            "timestamp":    block["time"],
            "size":         tx.get("size", 0),
        })
    return txs


def fetch_range(start_height: int, end_height: int, delay: float = 0.2) -> list[dict]:
    all_txs = []
    for height in range(start_height, end_height + 1):
        try:
            block_hash = rpc_call("getblockhash", [height])
            txs        = fetch_block_transactions(block_hash)
            all_txs.extend(txs)
            logger.info("BTC block %d: %d txs", height, len(txs))
        except Exception as exc:
            logger.error("Error at block %d: %s", height, exc)
        time.sleep(delay)
    return all_txs
