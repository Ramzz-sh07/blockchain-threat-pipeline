# Blockchain Transaction Threat Detection Pipeline

A real-time wallet risk scoring system for Ethereum and Bitcoin. Streams live blockchain data through Kafka, stores results in MongoDB, scores wallets with a trained ML model, and serves results via FastAPI and a Streamlit dashboard.

## Live system — verified working

- **Live Ethereum ingestion**: connects to Ethereum mainnet via Infura, polls confirmed blocks in real time, normalizes and publishes transactions to Kafka. Verified against real mainnet data (block ~25.35M, real wallet addresses and values).
- **Kafka streaming**: `raw-transactions` topic receiving live messages, verified via console consumer.
- **MongoDB**: 203,769 scored wallet records persisted and queried live by the API.
- **ML model**: trained on the Elliptic Bitcoin dataset (203,769 real transactions, 46,564 labelled).

## Results

| Metric | Score |
|--------|-------|
| Precision (illicit class) | **0.98** |
| Recall (illicit class) | **0.90** |
| ROC-AUC | **0.996** |
| Accuracy | **0.99** |

Model: Random Forest (300 trees, balanced class weights) trained on 165 anonymized transaction features plus 4 custom graph-derived features (in/out degree, diversity score, fan-out ratio). A secondary unsupervised Isolation Forest layer is also trained to catch novel anomalous patterns outside the labelled training data.

## Architecture
## Quickstart

```bash
git clone https://github.com/Ramzz-sh07/blockchain-threat-pipeline.git
cd blockchain-threat-pipeline
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Install and start MongoDB + Kafka (Mac, via Homebrew)
brew tap mongodb/brew && brew install mongodb-community
brew install kafka
brew services start mongodb-community
brew services start kafka
kafka-topics --create --topic raw-transactions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Set up environment
cp .env.example .env
# Add a free Infura key (infura.io) to ETH_RPC_URL and ETH_WS_URL in .env

# Download the Elliptic dataset from Kaggle into data/raw/
# https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

python scripts/train_on_elliptic.py    # trains model, writes to MongoDB
uvicorn api.main:app --reload          # REST API on :8000, reads from MongoDB
streamlit run dashboard/app.py         # dashboard on :8501

# Optional: run live ETH streaming
python3 -c "from ingestion.eth.eth_stream import stream_confirmed_blocks; stream_confirmed_blocks()"
```

Run `pytest tests/ -v` to verify the feature engineering and rule-based detection logic (6/6 passing).

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/wallet/{address}` | Risk score for a specific wallet (from MongoDB) |
| `GET /api/v1/flagged?limit=N` | Top N highest-risk flagged wallets (from MongoDB) |
| `GET /api/v1/stats` | Total wallets tracked in the database |

Full interactive docs at `localhost:8000/docs` once running.

## Project structure
## Tech stack

- **Streaming**: Kafka, Web3.py (Infura), Bitcoin JSON-RPC
- **Database**: MongoDB
- **Features**: Pandas, NetworkX
- **ML**: scikit-learn (Random Forest + Isolation Forest)
- **API**: FastAPI + Pydantic
- **Dashboard**: Streamlit + Plotly
- **Testing**: Pytest

## Design notes

**Why confirmed blocks instead of the mempool?** Infura's free tier doesn't expose `eth_newPendingTransactionFilter` (mempool watching is a paid-tier feature on most node providers). The streamer instead polls newly confirmed blocks — arguably a more reliable signal anyway, since pending transactions can be replaced or dropped before confirmation. Production fraud systems commonly prioritize confirmed-chain data for this reason.

**Why two detection models?** A supervised Random Forest, trained on confirmed illicit/licit labels, gives high precision but can only catch fraud patterns resembling what it's already seen. An unsupervised Isolation Forest, trained on all transactions including unlabelled ones, adds a second signal for structurally unusual wallets that don't match any known fraud pattern — useful against novel attack techniques.

**Why Streamlit instead of Power BI?** Both demonstrate the same underlying skill — building a live dashboard against an API. Power BI is Windows-first software with real friction on Mac (no native app, limited web-version connectivity to local APIs), so Streamlit was used to keep the dashboard fully functional and self-contained within the same Python stack as the rest of the project.

## Roadmap

- [ ] Graph Neural Network (GNN) wallet embeddings for richer relational features
- [ ] Bitcoin live streaming (ingestion code written, requires a running BTC full node or hosted RPC)
- [ ] Address clustering (co-spend heuristic for BTC)
- [ ] Docker Compose setup for one-command deployment
- [ ] Model retraining pipeline with drift detection
- [ ] Power BI dashboard (Windows environment)

## Dataset citation

Weber, M. et al. "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics." KDD 2019 Workshop.
