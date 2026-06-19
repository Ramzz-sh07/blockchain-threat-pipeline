"""
MongoDB connection and helper functions for storing/retrieving wallet risk scores.
"""
import os
from pymongo import MongoClient
from pymongo.collection import Collection

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("MONGO_DB_NAME", "blockchain_threats")

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    return get_client()[DB_NAME]


def get_wallets_collection() -> Collection:
    """Collection storing scored wallet risk data."""
    return get_db()["wallet_scores"]


def upsert_wallets(records: list[dict]):
    """
    Insert or update wallet score records.
    Each record must have a 'wallet' field used as the unique key.
    """
    collection = get_wallets_collection()
    for record in records:
        collection.update_one(
            {"wallet": record["wallet"]},
            {"$set": record},
            upsert=True,
        )


def get_wallet(wallet_address: str) -> dict | None:
    collection = get_wallets_collection()
    doc = collection.find_one({"wallet": wallet_address}, {"_id": 0})
    return doc


def get_flagged_wallets(limit: int = 50) -> list[dict]:
    collection = get_wallets_collection()
    cursor = collection.find({"flagged": True}, {"_id": 0}).sort("risk_score", -1).limit(limit)
    return list(cursor)


def get_all_wallets(limit: int = 1000) -> list[dict]:
    collection = get_wallets_collection()
    cursor = collection.find({}, {"_id": 0}).limit(limit)
    return list(cursor)


def count_wallets() -> int:
    return get_wallets_collection().count_documents({})


def create_indexes():
    """Run once to set up indexes for fast lookups."""
    collection = get_wallets_collection()
    collection.create_index("wallet", unique=True)
    collection.create_index("risk_score")
    collection.create_index("flagged")
