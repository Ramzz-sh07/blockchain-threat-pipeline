"""
Pull historical Ethereum blocks and transactions for a given range.
Useful for back-filling feature stores and model training.
"""
import logging
import time
from web3 import Web3
from config.settings import ETH_RPC_URL

logger = logging.getLogger(__name__)


def fetch_block_transactions(w3: Web3, block_number: int) -> list[dict]:
    block = w3.eth.get_block(block_number, full_transactions=True)
    txs   = []
    for tx in block.transactions:
        txs.append({
            "chain":     "ETH",
            "hash":      tx.hash.hex(),
            "from":      tx["from"],
            "to":        tx.get("to", ""),
            "value":     float(Web3.from_wei(tx.value, "ether")),
            "gas":       tx.gas,
            "gas_price": float(Web3.from_wei(tx.gasPrice, "gwei")),
            "block":     block_number,
            "timestamp": block.timestamp,
        })
    return txs


def fetch_range(start_block: int, end_block: int, delay: float = 0.1) -> list[dict]:
    """Fetch all transactions in [start_block, end_block] inclusive."""
    w3  = Web3(Web3.HTTPProvider(ETH_RPC_URL))
    all_txs = []
    for blk in range(start_block, end_block + 1):
        try:
            txs = fetch_block_transactions(w3, blk)
            all_txs.extend(txs)
            logger.info("Block %d: %d txs", blk, len(txs))
        except Exception as exc:
            logger.error("Error at block %d: %s", blk, exc)
        time.sleep(delay)   # be polite to the RPC node
    return all_txs
