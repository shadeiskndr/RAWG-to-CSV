#!/usr/bin/env python
"""
Fetch games from the RAWG API and store them directly in a SQLite database.

The script:
    • Streams pages from RAWG
    • Requests the full details for every game
    • Cleans / normalises the data (HTML stripping, whitespace, byte-length limits, …)
    • Inserts rows in batches into a SQLite database
    • Gracefully handles Ctrl-C and network errors
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

# ---------------------------------------------------------
#                       CONFIGURATION
# ---------------------------------------------------------
load_dotenv()
API_KEY: str | None = os.getenv("RAWG_API_KEY")
if not API_KEY:
    raise ValueError("Please set the RAWG_API_KEY environment variable.")

BASE_URL = "https://api.rawg.io/api/"
ENDPOINT = "games"

DB_FILENAME = "game_data_live.db"

# --- Easily tweakable knobs -----------------------------------------------
PAGE_SIZE: int = 40          # RAWG limit: 40 max
MAX_PAGES: int = 2         # total number of pages to loop through
BATCH_SIZE: int = 50         # SQLite insert batch size
MAX_DESCRIPTION_BYTES = 7_900
# --------------------------------------------------------------------------


# ---------------------------------------------------------
#                     DB  SET-UP
# ---------------------------------------------------------
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

# ---------------------------------------------------------
#                   HELPER UTILITIES
# ---------------------------------------------------------
def clean_text(text_data: str | None) -> str | None:
    """Strip HTML, collapse whitespace, ensure UTF-8."""
    if text_data in (None, ""):
        return text_data

    text_data = str(text_data)

    # Remove HTML tags quickly
    if "<" in text_data and ">" in text_data:
        try:
            text_data = BeautifulSoup(text_data, "html.parser").get_text()
        except Exception:
            pass

    # Normalise encoding & remove control chars
    try:
        text_data = text_data.encode("utf-8", "ignore").decode("utf-8")
    except Exception:
        text_data = re.sub(r"[^\x00-\x7F]+", "", text_data)

    text_data = re.sub(r"\s+", " ", text_data).strip()
    return text_data


def truncate_to_max_bytes(text: str | None, max_bytes: int) -> str | None:
    """Truncate text so its UTF-8 length ≤ max_bytes."""
    if not text:
        return text
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[: max_bytes - 3].decode("utf-8", errors="ignore")
    return truncated + "..."


def none_if_empty(value: Any) -> Any:
    """Return None for '', [], {}, or 0 (numeric) – else the original value."""
    if value in ("", [], {}, None):
        return None
    # treat numeric 0 / 0.0 as empty
    if isinstance(value, (int, float)) and value == 0:
        return None
    return value


# ---------------------------------------------------------
#            RAWG  API  HELPERS
# ---------------------------------------------------------
def fetch_games_page(page: int, retries: int = 3, delay: float = 1) -> List[dict]:
    url = f"{BASE_URL}{ENDPOINT}"
    params = {"key": API_KEY, "page": page, "page_size": PAGE_SIZE}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json().get("results", [])
            print(f"Page {page}: bad status {r.status_code}")
            return []
        except requests.RequestException as exc:
            print(f"Page {page}: {exc!r}")
            if attempt < retries - 1:
                time.sleep(delay)
    return []


def fetch_game_details(game_id: int, retries: int = 3, delay: float = 1) -> dict | None:
    url = f"{BASE_URL}{ENDPOINT}/{game_id}"
    params = {"key": API_KEY}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
            print(f"Game {game_id}: bad status {r.status_code}")
            return None
        except requests.RequestException as exc:
            print(f"Game {game_id}: {exc!r}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None


# ---------------------------------------------------------
#                  DATA  NORMALISATION
# ---------------------------------------------------------
def extract_clean_row(game_details: dict) -> Tuple[Any, ...]:
    """Convert RAWG game details dict to cleaned SQLite row tuple."""
    # Raw pulls
    rating = game_details.get("rating")
    playtime = game_details.get("playtime")
    metacritic = game_details.get("metacritic")

    row = (
        game_details.get("id"),
        none_if_empty(clean_text(game_details.get("slug"))),
        none_if_empty(clean_text(game_details.get("name"))),
        none_if_empty(game_details.get("released")),
        none_if_empty(game_details.get("background_image")),
        none_if_empty(rating),
        none_if_empty(metacritic),
        none_if_empty(playtime),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [
                        clean_text(p["platform"]["name"])
                        for p in game_details.get("platforms", [])
                        if p and p.get("platform")
                    ],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(g.get("name")) for g in game_details.get("genres", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(d.get("name")) for d in game_details.get("developers", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(p.get("name")) for p in game_details.get("publishers", [])],
                )
            )
        ),
        none_if_empty(
            ", ".join(
                filter(
                    None,
                    [clean_text(t.get("name")) for t in game_details.get("tags", [])],
                )
            )
        ),
        none_if_empty(
            truncate_to_max_bytes(
                clean_text(game_details.get("description")), MAX_DESCRIPTION_BYTES
            )
        ),
    )
    return row


# ---------------------------------------------------------
#           BATCH INSERT  &  SIGNAL  HANDLING
# ---------------------------------------------------------
def insert_batch(rows: Iterable[Tuple[Any, ...]]) -> None:
    """Insert batch of rows, ignoring duplicates."""
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

# ---------------------------------------------------------
#                        MAIN LOOP
# ---------------------------------------------------------
try:
    page_range = tqdm(range(1, MAX_PAGES + 1), desc="Pages")
    for page in page_range:
        page_games = fetch_games_page(page)
        if not page_games:
            break  # finished early

        for g in tqdm(page_games, desc=f"Games on page {page}", leave=False):
            details = fetch_game_details(g["id"])
            if not details:
                continue
            current_batch.append(extract_clean_row(details))

            if len(current_batch) >= BATCH_SIZE:
                insert_batch(current_batch)
                current_batch.clear()

            time.sleep(0.1)  # basic rate-limiting

        # allow Ctrl-C between pages
        time.sleep(0.2)

    # Final flush
    if current_batch:
        insert_batch(current_batch)

    print(f"All done! Data stored in '{DB_FILENAME}'.")
except Exception as exc:
    print(f"\nUnexpected error: {exc!r}")
    flush_and_exit()