import os
import requests
import json
import time
from tqdm import tqdm
import signal
import sys
from dotenv import load_dotenv
load_dotenv()

# Load API key from environment variable
api_key = os.getenv('RAWG_API_KEY')
if not api_key:
    raise ValueError("Please set the RAWG_API_KEY environment variable.")

base_url = 'https://api.rawg.io/api/'
endpoint = 'games'
output_file = 'fetched_games.json'
all_games = []

def fetch_game_details(game_id, retries=3, delay=1):
    url = f'{base_url}{endpoint}/{game_id}'
    params = {'key': api_key}
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                game_details = response.json()
                return {
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
            else:
                print(f'Failed to retrieve details for game ID {game_id}. Status code: {response.status_code}')
                return None
        except requests.RequestException as e:
            print(f'Error fetching game {game_id}: {e}')
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None

def fetch_games(page, retries=3, delay=1):
    url = f'{base_url}{endpoint}'
    params = {
        'key': api_key,
        'page': page,
        'page_size': 20
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                print(f'Failed to retrieve data from the API. Status code: {response.status_code}')
                return []
        except requests.RequestException as e:
            print(f'Error fetching games on page {page}: {e}')
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return []

def save_progress():
    with open(output_file, 'w') as json_file:
        json.dump(all_games, json_file, indent=4)
    print(f"Progress saved to '{output_file}'.")

def signal_handler(sig, frame):
    print("\nInterrupted! Saving progress before exit...")
    save_progress()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

try:
    for page in tqdm(range(1, 201), desc="Pages"):
        games = fetch_games(page)
        time.sleep(0.1)
        if not games:
            break
        for game in tqdm(games, desc=f"Games on page {page}", leave=False):
            game_details = fetch_game_details(game['id'])
            if game_details:
                all_games.append(game_details)
            time.sleep(0.1)  # Rate limiting: 10 requests/sec
        save_progress()  # Save after each page
except Exception as e:
    print(f"An error occurred: {e}")
    save_progress()
    sys.exit(1)

num_games_retrieved = len(all_games)
print(f"Total number of games retrieved: {num_games_retrieved}")

save_progress()
print(f"Data saved to '{output_file}'")
