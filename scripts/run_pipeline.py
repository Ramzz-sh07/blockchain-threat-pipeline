"""
Entry point: starts all pipeline components.
In production these would be separate processes/containers.
"""
import logging
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def main():
    from ingestion.eth.eth_stream import stream_pending_transactions
    from ingestion.btc.btc_stream import stream_mempool_transactions
    from pipeline.processor import run as run_processor

    threads = [
        threading.Thread(target=stream_pending_transactions, name="eth-stream", daemon=True),
        threading.Thread(target=stream_mempool_transactions, name="btc-stream", daemon=True),
        threading.Thread(target=run_processor,              name="processor",   daemon=True),
    ]

    for t in threads:
        t.start()
        logging.info("Started thread: %s", t.name)

    logging.info("All components running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logging.info("Shutdown requested.")

if __name__ == "__main__":
    main()
