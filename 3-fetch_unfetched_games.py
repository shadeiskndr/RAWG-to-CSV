import sqlite3
import requests
import json
import time
import os

# --- CONFIGURATION ---
DB_FILENAME = 'game_data_cleaned.db'
CANDIDATE_IDS_FILE = 'all_candidate_ids.txt'  # One game id per line
OUTPUT_FILE = 'newly_fetched_games.json'
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
BASE_URL = 'https://api.rawg.io/api/games/'

if not RAWG_API_KEY:
    raise ValueError("Please set the RAWG_API_KEY environment variable.")

# --- 1. Get already fetched IDs from SQLite ---
conn = sqlite3.connect(DB_FILENAME)
cursor = conn.cursor()
cursor.execute('SELECT id FROM games')
fetched_ids = set(row[0] for row in cursor.fetchall())
conn.close()

# --- 2. Load candidate IDs ---
with open(CANDIDATE_IDS_FILE, 'r') as f:
    candidate_ids = set(int(line.strip()) for line in f if line.strip().isdigit())

# --- 3. Determine IDs to fetch ---
ids_to_fetch = candidate_ids - fetched_ids
print(f"{len(ids_to_fetch)} new game IDs to fetch.")

# --- 4. Fetch details for unfetched IDs ---
new_games = []
for idx, game_id in enumerate(ids_to_fetch, 1):
    url = f"{BASE_URL}{game_id}"
    params = {'key': RAWG_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            new_games.append(response.json())
            print(f"Fetched {game_id} ({idx}/{len(ids_to_fetch)})")
        else:
            print(f"Failed to fetch {game_id}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {game_id}: {e}")
    time.sleep(0.1)  # Respect API rate limit

# --- 5. Save new data ---
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(new_games, f, indent=4)

print(f"Saved {len(new_games)} new games to {OUTPUT_FILE}")
