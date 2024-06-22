import requests
import json

api_key = 'YOUR_RAWG_API_KEY'
base_url = 'https://api.rawg.io/api/'

endpoint = 'games'

all_games = []

page = 1

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
                # Extract only the desired fields
                filtered_game = {
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
                all_games.append(filtered_game)
            else:
                print(f'Failed to retrieve details for game ID {game_id}. Status code: {game_details_response.status_code}')

        page += 1
    else:
        print(f'Failed to retrieve data from the API. Status code: {response.status_code}')
        break

num_games_retrieved = len(all_games)
print(f"Total number of games retrieved: {num_games_retrieved}")

with open('scanned_rawg_games2.json', 'w') as json_file:
    json.dump(all_games, json_file, indent=4)

print("Data saved to 'scanned_rawg_games2.json'")
