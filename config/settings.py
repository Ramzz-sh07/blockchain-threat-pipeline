"""
Central config — loaded from .env or environment variables.
Copy .env.example to .env and fill in your keys.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Ethereum ──────────────────────────────────────────────
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "https://mainnet.infura.io/v3/YOUR_KEY")
ETH_WS_URL  = os.getenv("ETH_WS_URL",  "wss://mainnet.infura.io/ws/v3/YOUR_KEY")

# ── Bitcoin ───────────────────────────────────────────────
BTC_RPC_HOST = os.getenv("BTC_RPC_HOST", "localhost")
BTC_RPC_PORT = int(os.getenv("BTC_RPC_PORT", "8332"))
BTC_RPC_USER = os.getenv("BTC_RPC_USER", "")
BTC_RPC_PASS = os.getenv("BTC_RPC_PASS", "")

# ── Kafka ─────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC_RAW = "raw-transactions"
KAFKA_TOPIC_SCORED = "scored-wallets"

# ── Database ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/blockchain_threats")

# ── Model ─────────────────────────────────────────────────
RISK_THRESHOLD   = float(os.getenv("RISK_THRESHOLD", "70"))   # flag wallets scoring >= this
MODEL_PATH       = os.getenv("MODEL_PATH", "data/models/isolation_forest.pkl")

# ── API ───────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
