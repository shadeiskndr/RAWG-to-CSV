import sqlite3
import json
from colorama import Fore, Style, init
from bs4 import BeautifulSoup
import re

# Initialize colorama
init(autoreset=True)

# Load the JSON data from the file
try:
    with open('scanned_rawg_games.json', 'r') as json_file:
        game_data = json.load(json_file)
except FileNotFoundError:
    print(Fore.RED + "JSON file not found. Make sure it exists in the current directory.")
    exit(1)
except json.JSONDecodeError:
    print(Fore.RED + "Error decoding JSON data. Check the format of the JSON file.")
    exit(1)

# Function to clean the description data
def clean_description(description):
    if description:
        # Remove HTML tags
        soup = BeautifulSoup(description, 'html.parser')
        text = soup.get_text()

        # Remove unwanted characters (e.g., �)
        text = re.sub(r'[�]', '', text)

        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    return description

# Initialize a list to store the extracted data
extracted_data = []

# Extract the specified fields for all games
for index, game in enumerate(game_data, start=1):
    game_id = game.get('id')
    game_slug = game.get('slug')
    game_name = game.get('name')
    game_released = game.get('released')
    game_year = game_released.split('-')[0] if game_released else None
    game_background_image = game.get('background_image')
    game_rating = game.get('rating', None)
    game_metacritic = game.get('metacritic', None)
    game_playtime = game.get('playtime', None)

    # Extract parent platforms
    parent_platforms = game.get('parent_platforms', [])
    game_parent_platforms_list = [platform['platform']['name'] for platform in parent_platforms if 'platform' in platform and 'name' in platform['platform']]
    game_parent_platforms = ', '.join(game_parent_platforms_list)

    # Extract genres
    genres = game.get('genres', [])
    game_genres_list = [genre['name'] for genre in genres if 'name' in genre]
    game_genres = ', '.join(game_genres_list)

    game_description = clean_description(game.get('description'))

    # Create a dictionary with the extracted data for this game
    game_info = {
        "Index": index,
        "ID": game_id,
        "Slug": game_slug,
        "Name": game_name,
        "Date Released": game_released,
        "Year Released": game_year,  # Store only the year
        "Background Image": game_background_image,
        "Rating": game_rating,
        "Metacritic": game_metacritic,
        "Playtime": game_playtime,
        "Platforms": game_parent_platforms,
        "Genres": game_genres,
        "Description": game_description,
    }

    # Append the game data to the list
    extracted_data.append(game_info)

# Define the box characters
horizontal_line = "─"  # U+2500
vertical_line = "│"  # U+2502
top_left_corner = "┌"  # U+250C
top_right_corner = "┐"  # U+2510
bottom_left_corner = "└"  # U+2514
bottom_right_corner = "┘"  # U+2518

# Print the extracted data with a box-like border
for game_info in extracted_data:
    index_str = str(game_info['Index'])

    if game_info['Index'] == 1:
        # Highlight index 1 with red text
        index_str = Fore.RED + index_str

    # Calculate the width of the box based on the length of the text
    box_width = len(index_str) + 2

    # Create the top border of the box
    top_border = f"{top_left_corner}{horizontal_line * box_width}{top_right_corner}"

    # Create the middle line with text and box
    middle_line = f"{vertical_line} {index_str} {vertical_line}"

    # Create the bottom border of the box
    bottom_border = f"{bottom_left_corner}{horizontal_line * box_width}{bottom_right_corner}"

    # Print the box
    print(top_border)
    print(middle_line)
    print(bottom_border)

    # Print the game information
    print(f"Game ID: {game_info['ID']}")
    print(f"Slug: {game_info['Slug']}")
    print(f"Name: {game_info['Name']}")
    print(f"Date Released: {game_info['Date Released']}")
    print(f"Year Released: {game_info['Year Released']}")
    print(f"Background Image: {game_info['Background Image']}")
    print(f"Rating: {game_info['Rating']}")
    print(f"Metacritic: {game_info['Metacritic']}")
    print(f"Playtime: {game_info['Playtime']}")
    print(f"Platforms: {game_info['Platforms']}")
    print(f"Genres: {game_info['Genres']}")
    print(f"Description: {game_info['Description']}")

    # Add some space between boxes
    print("\n")

# SQLite database setup
conn = sqlite3.connect('game_data3.db')
cursor = conn.cursor()

# Create a games table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY,
        slug TEXT,
        name TEXT,
        datereleased TEXT,
        yearreleased TEXT,
        background_image TEXT,
        rating REAL,
        metacritic INTEGER,
        playtime INTEGER,
        platforms TEXT,
        genres TEXT,
        description TEXT
    )
''')

# Insert data into the games table
for game_info in extracted_data:
    cursor.execute('''
        INSERT OR IGNORE INTO games (
            id, slug, name, datereleased, yearreleased, background_image, rating, metacritic, playtime, platforms,
            genres, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        game_info['ID'],
        game_info['Slug'],
        game_info['Name'],
        game_info['Date Released'],
        game_info['Year Released'],
        game_info['Background Image'],
        game_info['Rating'],
        game_info['Metacritic'],
        game_info['Playtime'],
        game_info['Platforms'],
        game_info['Genres'],
        game_info['Description'],
    ))

# Commit the changes and close the database connection
conn.commit()
conn.close()

print(Fore.GREEN + "Data successfully inserted into the database.")
