import sqlite3
import requests
import json
import time
import os
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURATION ---
DB_FILENAME = 'game_data_cleaned.db'
OUTPUT_FILE = 'newly_fetched_games.json'
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
BASE_URL = 'https://api.rawg.io/api/games/'

START_ID = 1         # Change as needed
END_ID = 2000      # Change as needed (exclusive, so goes up to END_ID-1)

if not RAWG_API_KEY:
    raise ValueError("Please set the RAWG_API_KEY environment variable.")

# --- 1. Get already fetched IDs from SQLite ---
conn = sqlite3.connect(DB_FILENAME)
cursor = conn.cursor()
cursor.execute('SELECT id FROM games')
fetched_ids = set(row[0] for row in cursor.fetchall())
conn.close()

# --- 2. Determine IDs to fetch (all missing IDs in the range) ---
all_ids = set(range(START_ID, END_ID))
ids_to_fetch = all_ids - fetched_ids
print(f"{len(ids_to_fetch)} new game IDs to fetch (from {START_ID} to {END_ID-1}).")

# --- 3. Fetch details for unfetched IDs ---
new_games = []
for idx, game_id in enumerate(sorted(ids_to_fetch), 1):
    url = f"{BASE_URL}{game_id}"
    params = {'key': RAWG_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            game_details = response.json()
            filtered = {
                'id': game_details.get('id'),
                'slug': game_details.get('slug'),
                'name': game_details.get('name'),
                'released': game_details.get('released'),
                'background_image': game_details.get('background_image'),
                'rating': game_details.get('rating'),
                'metacritic': game_details.get('metacritic'),
                'playtime': game_details.get('playtime'),
                'parent_platforms': game_details.get('parent_platforms'),
                'genres': game_details.get('genres'),
                'description': game_details.get('description', 'No description available')
            }
            new_games.append(filtered)
            print(f"Fetched {game_id} ({idx}/{len(ids_to_fetch)})")
        elif response.status_code == 404:
            print(f"Game ID {game_id} not found (404).")
        else:
            print(f"Failed to fetch {game_id}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {game_id}: {e}")
    time.sleep(0.1)  # Respect API rate limit

# --- 4. Save new data ---
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(new_games, f, indent=4)

print(f"Saved {len(new_games)} new games to {OUTPUT_FILE}")
