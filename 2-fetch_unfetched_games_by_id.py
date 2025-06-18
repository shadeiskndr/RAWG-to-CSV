#!/usr/bin/env python
"""
Fetch any RAWG game-IDs that are missing from the local SQLite database.

Steps
-----
1.  Inspect the existing DB and build a set of already-stored IDs
2.  For every ID in the desired range that is NOT present -> call the RAWG
    single-game endpoint
3.  Clean / normalise the returned JSON
4.  Insert the new rows in configurable batches
5.  Flush & exit gracefully on Ctrl-C
"""
from __future__ import annotations

import os
import re
import signal
import sqlite3
import sys
import time
from typing import Any, Iterable, List, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

# ---------------------------------------------------------------------------
#                              CONFIGURATION
# ---------------------------------------------------------------------------
load_dotenv()
API_KEY: str | None = os.getenv("RAWG_API_KEY")
if not API_KEY:
    raise ValueError("Please set the RAWG_API_KEY environment variable.")

BASE_URL = "https://api.rawg.io/api/games/"

DB_FILENAME = "game_data_live.db"     # target DB
START_ID: int = 1                        # inclusive
END_ID: int = 100                     # exclusive (goes up to END_ID-1)

BATCH_SIZE: int = 50                     # SQLite insertion batch size
MAX_DESCRIPTION_BYTES = 7_900            # keep in sync with other scripts
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
#                         DATABASE  SET-UP / EXISTING IDs
# ---------------------------------------------------------------------------
conn = sqlite3.connect(DB_FILENAME, check_same_thread=False)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS games (
        id              INTEGER PRIMARY KEY,
        slug            TEXT,
        name            TEXT,
        released        TEXT,
        background_image TEXT,
        rating          REAL,
        metacritic      INTEGER,
        playtime        INTEGER,
        platforms       TEXT,
        genres          TEXT,
        developers      TEXT,
        publishers      TEXT,
        tags            TEXT,
        description     TEXT
    )
"""
)
conn.commit()

cur.execute("SELECT id FROM games")
already_present_ids = {row[0] for row in cur.fetchall()}

# Build the list of IDs we still need
all_ids = set(range(START_ID, END_ID))
ids_to_fetch = sorted(all_ids - already_present_ids)
print(f"{len(ids_to_fetch)} unfetched IDs to retrieve ({START_ID}-{END_ID-1}).")

# ---------------------------------------------------------------------------
#                       TEXT-CLEANING  UTILITIES
# ---------------------------------------------------------------------------
def clean_text(text_data: str | None) -> str | None:
    """Strip HTML, collapse whitespace, ensure UTF-8."""
    if text_data in (None, ""):
        return text_data

    text_data = str(text_data)

    # remove HTML
    if "<" in text_data and ">" in text_data:
        try:
            text_data = BeautifulSoup(text_data, "html.parser").get_text()
        except Exception:
            pass

    # force UTF-8, drop bad chars
    try:
        text_data = text_data.encode("utf-8", "ignore").decode("utf-8")
    except Exception:
        text_data = re.sub(r"[^\x00-\x7F]+", "", text_data)

    text_data = re.sub(r"\s+", " ", text_data).strip()
    return text_data


def truncate_to_max_bytes(text: str | None, max_bytes: int) -> str | None:
    """Truncate string so its UTF-8 length ≤ max_bytes (adds “…”)."""
    if not text:
        return text
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[: max_bytes - 3].decode("utf-8", errors="ignore")
    return truncated + "..."


def none_if_empty(value: Any) -> Any:
    """Turn '', [], {}, None, or numeric 0 into None (for NULL in DB)."""
    if value in ("", [], {}, None):
        return None
    if isinstance(value, (int, float)) and value == 0:
        return None
    return value


# ---------------------------------------------------------------------------
#                        RAWG  API  HELPERS
# ---------------------------------------------------------------------------
def fetch_game_details(game_id: int, retries: int = 3, delay: float = 1) -> dict | None:
    url = f"{BASE_URL}{game_id}"
    params = {"key": API_KEY}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                # skip permanently if not found
                print(f"ID {game_id} not found (404).")
                return None
            print(f"ID {game_id}: bad status {r.status_code}")
            return None
        except requests.RequestException as exc:
            print(f"ID {game_id}: {exc!r}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None


# ---------------------------------------------------------------------------
#                         DATA  NORMALISATION
# ---------------------------------------------------------------------------
def extract_clean_row(details: dict) -> Tuple[Any, ...]:
    """Convert RAWG game-details JSON to a cleaned SQLite row tuple."""
    rating = details.get("rating")
    playtime = details.get("playtime")

    return (
        details.get("id"),
        none_if_empty(clean_text(details.get("slug"))),
        none_if_empty(clean_text(details.get("name"))),
        none_if_empty(details.get("released")),
        none_if_empty(details.get("background_image")),
        none_if_empty(rating),
        details.get("metacritic"),  # may legitimately be 0
        none_if_empty(playtime),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [
                        clean_text(p["platform"]["name"])
                        for p in details.get("platforms", [])
                        if p and p.get("platform")
                    ],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(g.get("name")) for g in details.get("genres", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(d.get("name")) for d in details.get("developers", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(p.get("name")) for p in details.get("publishers", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(t.get("name")) for t in details.get("tags", [])],
                )
            )
        ),
        none_if_empty(
            truncate_to_max_bytes(
                clean_text(details.get("description")), MAX_DESCRIPTION_BYTES
            )
        ),
    )


# ---------------------------------------------------------------------------
#               BATCH INSERTION  &  SIGNAL  HANDLING
# ---------------------------------------------------------------------------
def insert_batch(rows: Iterable[Tuple[Any, ...]]) -> None:
    cur.executemany(
        """
        INSERT OR IGNORE INTO games (
            id, slug, name, released, background_image,
            rating, metacritic, playtime, platforms, genres,
            developers, publishers, tags, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        list(rows),
    )
    conn.commit()


current_batch: List[Tuple[Any, ...]] = []


def flush_and_exit(signum=None, frame=None):
    if current_batch:
        print("\nFlushing remaining records before exit…")
        insert_batch(current_batch)
        current_batch.clear()
    conn.close()
    sys.exit(0)


signal.signal(signal.SIGINT, flush_and_exit)

# ---------------------------------------------------------------------------
#                                MAIN LOOP
# ---------------------------------------------------------------------------
try:
    for idx, game_id in enumerate(tqdm(ids_to_fetch, desc="Fetching"), 1):
        details = fetch_game_details(game_id)
        if not details:
            continue
        current_batch.append(extract_clean_row(details))

        if len(current_batch) >= BATCH_SIZE:
            insert_batch(current_batch)
            current_batch.clear()

        time.sleep(0.1)  # respect RAWG rate-limit

    # final flush
    if current_batch:
        insert_batch(current_batch)
        current_batch.clear()

    print(f"Finished! Added all missing games to '{DB_FILENAME}'.")
except Exception as exc:
    print(f"\nUnexpected error: {exc!r}")
    flush_and_exit()
