"""
Generate OpenAI vector embeddings for every row in `videogames_filtered.db`.

Prerequisites
-------------
1.  Create a file named `.env` in the project root that contains
        OPENAI_API_KEY=sk-...
    (or export the variable in your shell).

2.  Install dependencies inside an activated virtual-env:
        pip install -r requirements.txt

Run:
    python 4-generate_embeddings.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from typing import Any, List

from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #

load_dotenv()  # Reads .env file into os.environ
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if client.api_key is None:
    sys.exit("❌  OPENAI_API_KEY not set (environment or .env file)")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DB_FILE = "game_data_filtered.db"
TABLE_NAME = "games"
EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100            # OpenAI allows up to 2048; pick a safe default

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def add_embedding_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({TABLE_NAME})")
    cols = {row[1] for row in cur.fetchall()}
    if "embedding" not in cols:
        cur.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN embedding TEXT")
        conn.commit()


def fetch_rows_without_embedding(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE embedding IS NULL")
    return cur.fetchall()


def build_inputs(rows: List[sqlite3.Row]) -> List[str]:
    """Return list of texts (name + description) for embedding."""
    inputs: List[str] = []
    for r in rows:
        name = (r["name"] or "").replace("\n", " ")
        description = (r["description"] or "").replace("\n", " ")
        combined = (name + "\n\n" + description).strip()
        inputs.append(combined)
    return inputs


def chunked(seq: List[Any], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def request_embeddings(texts: List[str]) -> List[List[float]]:
    """Make a single OpenAI embeddings request with simple retries."""
    retries = 5
    for attempt in range(retries):
        try:
            resp = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
            return [d.embedding for d in resp.data]
        except Exception as exc:  # pylint: disable=broad-except
            wait = 2**attempt
            print(f"openai error ({exc}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("Failed to get embeddings after retries")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    if not os.path.exists(DB_FILE):
        sys.exit("Filtered DB not found – run filter_videogames.py first.")

    conn = sqlite3.connect(DB_FILE)
    add_embedding_column(conn)

    rows = fetch_rows_without_embedding(conn)
    if not rows:
        print("All rows already have embeddings. Nothing to do.")
        conn.close()
        return

    print(f"Generating embeddings for {len(rows)} rows …")
    cur = conn.cursor()

    for batch in chunked(rows, BATCH_SIZE):
        texts = build_inputs(batch)
        vectors = request_embeddings(texts)

        cur.executemany(
            f"UPDATE {TABLE_NAME} SET embedding = ? WHERE id = ?",
            [(json.dumps(vec), r["id"]) for vec, r in zip(vectors, batch)],
        )
        conn.commit()
        print(f"Processed {len(batch)} rows …")

    conn.close()
    print("✅  Embedding generation complete.")


if __name__ == "__main__":
    main()
