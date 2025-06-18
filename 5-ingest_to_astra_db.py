"""
Stream all rows from videogames_filtered.db into a vector-enabled
Astra DB collection.

.env variables required
-----------------------
ASTRA_DB_API_ENDPOINT      = https://XXXXX-XXXXX.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN = ASTRADB_TOKEN
ASTRA_DB_COLLECTION_NAME   = games_vectors

Run:
    python 5-ingest_to_astra_db.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from typing import Dict, List

from astrapy import DataAPIClient
from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #

load_dotenv()

DB_FILE = "game_data_filtered.db"
TABLE_NAME = "games"

BATCH_SIZE = 20          # Astra Data API limit
MAX_RETRIES = 5

ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
ASTRA_COLLECTION = os.getenv("ASTRA_DB_COLLECTION_NAME")

if not all([ASTRA_ENDPOINT, ASTRA_TOKEN, ASTRA_COLLECTION]):
    sys.exit("❌  Missing Astra env vars (see header).")

# --------------------------------------------------------------------------- #
# Astra helpers
# --------------------------------------------------------------------------- #


def get_collection():
    client = DataAPIClient()
    db = client.get_database(ASTRA_ENDPOINT, token=ASTRA_TOKEN)
    return db.get_collection(ASTRA_COLLECTION)


def insert_batch(collection, docs: List[Dict]):
    """Insert with exponential-backoff retries."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            collection.insert_many(docs)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == MAX_RETRIES:
                raise
            wait = 2**attempt
            print(f"Astra insert error: {exc}. Retrying in {wait}s")
            time.sleep(wait)


# --------------------------------------------------------------------------- #
# SQLite helpers
# --------------------------------------------------------------------------- #


def fetch_rows(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE embedding IS NOT NULL")
    return cur.fetchall()


# --------------------------------------------------------------------------- #
# Row conversion
# --------------------------------------------------------------------------- #


def row_to_doc(row: sqlite3.Row) -> Dict:
    """Convert an sqlite row to a document dict ready for Astra."""
    vector = json.loads(row["embedding"]) if row["embedding"] else None
    if vector is None:
        raise ValueError("missing embedding")

    # Use slug as _id; fall back to deterministic string based on id
    slug = (row["slug"] or "").strip()
    doc_id = slug if slug else f"game_{row['id']}"

    # Copy all columns except 'embedding' into document
    doc = {k: row[k] for k in row.keys() if k != "embedding"}
    doc["_id"] = doc_id
    doc["$vector"] = vector  # reserved vector field

    return doc


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    if not os.path.exists(DB_FILE):
        sys.exit("❌  videogames_filtered_consoles.db not found – run previous scripts first.")

    conn = sqlite3.connect(DB_FILE)
    rows = fetch_rows(conn)
    total = len(rows)
    print(f"⚙️  Ingesting {total} rows into Astra collection '{ASTRA_COLLECTION}'…")

    collection = get_collection()

    batch: List[Dict] = []
    processed = 0

    for row in rows:
        try:
            batch.append(row_to_doc(row))
        except ValueError as err:
            print(f"Skipping row {row['id']} – {err}")
            continue

        if len(batch) == BATCH_SIZE:
            insert_batch(collection, batch)
            processed += len(batch)
            print(f"  • {processed}/{total} inserted")
            batch.clear()

    if batch:
        insert_batch(collection, batch)
        processed += len(batch)
        print(f"  • {processed}/{total} inserted")

    conn.close()
    print("✅  Ingestion complete.")


if __name__ == "__main__":
    main()
