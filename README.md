<h1 align="center">
  RAWG-to-CSV
</h1>

## Overview

This report explains the process of fetching game data from the RAWG API, processing it, storing it in an SQLite database, and finally exporting it to an Excel file. The process is divided into three main scripts: main.py, main_model.py, and DataFrame.py. The CSV file obtained from the script is used for my AI Game Recommender web-app.

## How to Run

- Install Python
- Clone this repository into a folder.
- Open up the terminal within the folder in VSCode
- Install dependencies with "pip install"
- Run the scripts e.g. "py main.py"

## Step-by-Step Process

### Fetching Data from RAWG API (main.py)

Configuration: The script starts by importing necessary libraries (requests and json) and setting up the API key and base URL for the RAWG API.

Initialization: An empty list all_games is initialized to store the fetched game data. The script is set to start fetching from page 1 to avoid duplicates.

Data Fetching Loop:

- The script loops through pages 1 to 200.
- For each page, it sends a GET request to the RAWG API endpoint for games.
- If the response is successful (status code 200), it extracts the game data from the response.
- For each game, it fetches detailed information including a description.
- If the detailed information fetch fails, a default message is added.
- The fetched game data is appended to the all_games list.
- If the API request fails, an error message is printed, and the loop breaks.

Saving Data: The fetched game data is saved to a JSON file named rawg_games.json.

### Processing and Storing Data in SQLite (main_model.py)

Configuration: The script imports necessary libraries (sqlite3, json, and colorama for colored output).

Loading JSON Data: The script loads the JSON data from the file scanned_rawg_games2.json.

Data Extraction:

- The script extracts specific fields (ID, slug, name, released date, background image, rating, metacritic score, playtime, platforms, genres, and description) from the JSON data.
- It processes the parent platforms and genres to create comma-separated strings.
- The extracted data is stored in a list extracted_data.

Printing Data: The script prints the extracted data in a formatted manner using box-like borders.

Inserting Data into SQLite:

- The script connects to an SQLite database named game_data.db.
- It creates a table games if it doesn't exist.
- The extracted data is inserted into the games table.
- The changes are committed, and the database connection is closed.

### Exporting Data to Excel (DataFrame.py)

Configuration: The script imports necessary libraries (sqlite3, pandas).

Reading Data from SQLite:

- The script connects to the SQLite database game_data.db.
- It reads the data from the games table into a Pandas DataFrame.
- The database connection is closed.

Exporting Data to Excel: The script sets the DataFrame index and exports the data to an Excel file named game_data_new.xlsx.

## Summary

main.py: Fetches game data from the RAWG API and saves it to a JSON file.
main_model.py: Reads the JSON data, processes it, prints it in a formatted manner, and inserts it into an SQLite database.
DataFrame.py: Reads the data from the SQLite database and exports it to an Excel file.
These scripts together form a pipeline for fetching, processing, storing, and exporting game data from the RAWG API.
