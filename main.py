import requests
import json

api_key = 'YOUR_RAWG_API_KEY'
base_url = 'https://api.rawg.io/api/'

endpoint = 'games'

all_games = []

page = 1  # Start at page #? to avoid duplicates

while page <= 200:  # Loop through all 200 pages
    # Define query parameters including the API key, page number, and page size
    params = {
        'key': api_key,
        'page': page,
        'page_size': 20  # Adjust the page size as needed
    }

    response = requests.get(f'{base_url}{endpoint}', params=params)

    if response.status_code == 200:
        data = response.json()
        games = data.get('results', [])

        if not games:
            break

        for game in games:
            game_id = game['id']
            # Fetch detailed information for each game
            game_details_response = requests.get(f'{base_url}{endpoint}/{game_id}', params={'key': api_key})
            if game_details_response.status_code == 200:
                game_details = game_details_response.json()
                game['description'] = game_details.get('description', 'No description available')
            else:
                game['description'] = 'Failed to retrieve description'

        all_games.extend(games)

        page += 1
    else:
        print(f'Failed to retrieve data from the API. Status code: {response.status_code}')
        break

num_games_retrieved = len(all_games)
print(f"Total number of games retrieved: {num_games_retrieved}")

with open('rawg_games.json', 'w') as json_file:
    json.dump(all_games, json_file, indent=4)

print("Data saved to 'rawg_games.json'")


