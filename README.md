# Blockchain Transaction Threat Detection Pipeline

A real-time wallet risk scoring system for Ethereum and Bitcoin. Monitors transactions, extracts behavioural and graph features, and flags suspicious wallets using a trained machine learning model.

## Results

Trained and evaluated on the [Elliptic Bitcoin Dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set) — 203,769 real Bitcoin transactions, 46,564 of them labelled (illicit/licit) by domain experts.

| Metric | Score |
|--------|-------|
| Precision (illicit class) | **0.98** |
| Recall (illicit class) | **0.90** |
| ROC-AUC | **0.996** |
| Accuracy | **0.99** |

Model: Random Forest (300 trees, balanced class weights) trained on 165 anonymized transaction features plus 4 custom graph-derived features (in/out degree, diversity score, fan-out ratio). A secondary unsupervised Isolation Forest layer is also trained to catch novel anomalous patterns not present in the labelled training data — mirroring how production fraud systems combine supervised detection with anomaly-based safety nets.

## Architecture

## Quickstart

```bash
git clone https://github.com/Ramzz-sh07/blockchain-threat-pipeline.git
cd blockchain-threat-pipeline
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Download the Elliptic dataset from Kaggle and place the 3 CSVs in data/raw/
# https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

python scripts/train_on_elliptic.py    # trains model, prints evaluation report
uvicorn api.main:app --reload          # starts REST API on :8000
streamlit run dashboard/app.py         # starts dashboard on :8501
```

Run `pytest tests/ -v` to verify the feature engineering and rule-based detection logic.

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/wallet/{address}` | Risk score for a specific wallet |
| `GET /api/v1/flagged?limit=N` | Top N highest-risk flagged wallets |

Full interactive docs at `localhost:8000/docs` once running.

## Features extracted

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

Note: the graph features above were validated on the Elliptic dataset; the temporal and wallet-profile extractors are built for live ETH/BTC streaming (see `ingestion/`) where real timestamps and amounts are available, which the anonymized Elliptic dataset does not expose.

## Project structure
## Tech stack

- **Streaming**: Kafka, Web3.py, Bitcoin JSON-RPC
- **Features**: Pandas, NetworkX
- **ML**: scikit-learn (Random Forest + Isolation Forest)
- **API**: FastAPI + Pydantic
- **Dashboard**: Streamlit + Plotly
- **Testing**: Pytest

## Design notes

The system combines two detection strategies deliberately:

1. **Supervised (Random Forest)** — trained on confirmed illicit/licit labels. High precision, but can only catch fraud patterns resembling what it's already seen.
2. **Unsupervised (Isolation Forest)** — trained on all transactions including unlabelled ones. Lower precision alone, but catches structurally unusual wallets that don't match any known fraud signature — useful against novel attack patterns.

In production, these would typically run as parallel signals feeding into a combined risk score, with the supervised model carrying more weight given its measured accuracy, and the unsupervised layer acting as a tripwire for analyst review.

## Roadmap

- [ ] Graph Neural Network (GNN) wallet embeddings for richer relational features
- [ ] Live ETH/BTC streaming pipeline tested end-to-end (currently built but requires Infura/node access)
- [ ] Address clustering (co-spend heuristic for BTC)
- [ ] Docker Compose setup for one-command deployment
- [ ] Model retraining pipeline with drift detection

## Dataset citation

Weber, M. et al. "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics." KDD 2019 Workshop.
