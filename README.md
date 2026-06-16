# Blockchain Transaction Threat Detection Pipeline

A real-time wallet risk scoring system for Ethereum and Bitcoin. Monitors live transactions, extracts behavioural features, and flags suspicious wallets using a combination of unsupervised ML and rule-based heuristics.

## Architecture

```
Blockchain nodes (ETH + BTC)
        │
        ▼
  Kafka message bus  (raw-transactions topic)
        │
        ▼
  Feature engineering
  ├── Graph features    (fan-out ratio, diversity, degree)
  ├── Temporal features (velocity, burst detection, nocturnality)
  └── Wallet profile    (balance, age, round-amount ratio)
        │
        ▼
  Detection layer
  ├── Isolation Forest  (unsupervised anomaly scoring)
  └── Rule-based flags  (heuristic penalty system)
        │
        ▼
  Risk score aggregator (weighted ensemble → 0-100 score)
        │
   ┌────┴────┐
   ▼         ▼
FastAPI    Streamlit
REST API   Dashboard
```

## Quickstart

```bash
# 1. Clone and set up environment
git clone https://github.com/YOUR_USERNAME/blockchain-threat-pipeline.git
cd blockchain-threat-pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env
# Edit .env with your Infura key and DB credentials

# 3. Run tests
pytest tests/ -v

# 4. Start the pipeline processor
python scripts/run_pipeline.py

# 5. Start the API
uvicorn api.main:app --reload

# 6. Launch dashboard
streamlit run dashboard/app.py
```

## Features extracted per wallet

| Category | Feature | Description |
|----------|---------|-------------|
| Graph | fan_out_ratio | High = distributes to many recipients (mixing signal) |
| Graph | diversity_score | Low = always transacts with same counterparties |
| Temporal | burst_count | Number of 5+ transactions within a 60-minute window |
| Temporal | night_fraction | Fraction of activity between midnight–6am UTC |
| Temporal | tx_velocity | Transactions per hour |
| Wallet | round_ratio | Fraction of transactions with suspiciously round amounts |
| Wallet | value_concentration | Fraction of total value in top 20% of transactions |
| Wallet | age_seconds | Time between first and last observed transaction |

## Datasets for training / evaluation

- [Elliptic Bitcoin Dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set) — 200k labelled BTC transactions
- [Ethereum Fraud Detection](https://www.kaggle.com/datasets/vagifa/ethereum-frauddetection-dataset) — labelled ETH wallet activity

## Project structure

```
blockchain-threat-pipeline/
├── ingestion/          # ETH and BTC data collectors
├── features/           # Feature engineering modules
├── detection/          # ML models and rule engine
├── pipeline/           # Kafka stream processor
├── api/                # FastAPI REST endpoints
├── dashboard/          # Streamlit monitoring UI
├── tests/              # Pytest unit tests
├── notebooks/          # Exploration and training notebooks
├── scripts/            # Helper scripts
└── config/             # Settings and environment loader
```

## Tech stack

- **Streaming**: Kafka, Web3.py, Bitcoin RPC
- **Features**: Pandas, NetworkX
- **ML**: scikit-learn (Isolation Forest)
- **API**: FastAPI + Pydantic
- **Dashboard**: Streamlit + Plotly
- **Database**: PostgreSQL

## Roadmap

- [ ] Graph Neural Network (GNN) wallet embeddings
- [ ] DeFi flash loan attack detector
- [ ] Address clustering (co-spend heuristic for BTC)
- [ ] Docker Compose setup for one-command deployment
