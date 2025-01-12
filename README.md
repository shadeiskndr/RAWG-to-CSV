<h1 align="center">
  RAWG-to-CSV
</h1>

## Overview

This project fetches game data from the RAWG API, processes and cleans it (including removing HTML and ensuring UTF-8 compatibility), stores it in an SQLite database, and finally exports it to either a single Excel file or multiple batched CSV files. The primary goal is to produce clean, structured game data suitable for downstream applications, such as the AI Game Recommender web-app mentioned previously, or for ingestion into databases like Astra DB which require valid UTF-8 encoding.

The process is divided into several Python scripts: `main.py` (fetching), `main_model.py` (cleaning and storing), `DataFrame.py` (exporting to a single Excel file), and `DataFrame2.py` (exporting to batched CSV files).

## How to Run

1.  **Install Python:** Ensure you have Python 3 installed.
2.  **Clone Repository:** Clone this repository to a local folder.
    ```bash
    git clone https://github.com/shadeiskndr/RAWG-to-CSV.git
    ```
    ```bash
    cd RAWG-to-CSV
    ```
3.  **Set up Virtual Environment (Recommended):**
    - Create the environment:
      ```bash
      python3 -m venv venv
      ```
      _(Use `python` or `py` if `python3` doesn't work)_
    - Activate the environment:
      - Linux/macOS:
        ```bash
        source venv/bin/activate
        ```
      - Windows (cmd):
        ```bash
        .\venv\Scripts\activate.bat
        ```
      - Windows (PowerShell):
        ```bash
        .\venv\Scripts\Activate.ps1
        ```
4.  **Install Dependencies:** Install the required packages using pip.
    ```bash
    pip install requests colorama beautifulsoup4 pandas openpyxl
    ```
5.  **Set RAWG API Key:** **Crucially, edit `main.py`** and replace `'YOUR_RAWG_API_KEY'` with your actual API key from RAWG.
6.  **Check Filenames (Optional but Recommended):** The scripts `main_model.py`, `DataFrame.py`, and `DataFrame2.py` use constants near the top for input JSON (`INPUT_JSON`) and database (`DB_FILENAME`) filenames. Ensure these match your intended workflow (e.g., `main_model.py` reads the JSON created by `main.py`, and `DataFrame.py`/`DataFrame2.py` read the database created by `main_model.py`). The defaults are set to reasonable values (`rawg_games.json`, `game_data_cleaned.db`).
7.  **Run the Scripts Sequentially:**
    - Fetch data from RAWG API:
      ```bash
      python3 main.py
      ```
    - Clean data and store in SQLite DB:
      ```bash
      python3 main_model.py
      ```
    - **Option A:** Export all data to a single Excel file (`excelGameData.xlsx` or similar):
      ```bash
      python3 DataFrame.py
      ```
    - **Option B:** Export data to batched CSV files (e.g., `game_data_batch_1.csv`, `game_data_batch_2.csv` in `batched_csv_output/` directory):
      ```bash
      python3 DataFrame2.py
      ```

## Step-by-Step Process

### 1. Fetching Data from RAWG API (`main.py`)

- **Configuration:** Imports `requests` and `json`. Sets up the user's API key (must be edited) and base URL for the RAWG API.
- **Initialization:** Initializes an empty list `all_games`. Starts fetching from page 1.
- **Data Fetching Loop:**
  - Loops through API pages (1 to 200 by default).
  - Sends GET requests to fetch game lists.
  - For each game, sends another GET request to fetch detailed info, including the description.
  - Handles potential errors during API calls.
  - Appends fetched game data to the `all_games` list.
- **Saving Data:** Saves the raw fetched data (list of game dictionaries) to a JSON file (default: `rawg_games.json`).

### 2. Processing, Cleaning, and Storing Data in SQLite (`main_model.py`)

- **Configuration:** Imports `sqlite3`, `json`, `colorama`, `BeautifulSoup` (from `bs4`), and `re`. Defines constants for the input JSON filename (`INPUT_JSON`) and the output SQLite database filename (`DB_FILENAME`).
- **Loading JSON Data:** Loads the raw game data from the specified `INPUT_JSON` file (e.g., `rawg_games.json`).
- **Data Cleaning & Extraction:**
  - Iterates through each game in the loaded JSON data.
  - Extracts specific fields (ID, slug, name, released, background image, rating, metacritic, playtime, platforms, genres, description).
  - **Applies `clean_text` function:** This function is applied to text fields (`name`, `slug`, `description`, platform names, genre names) to:
    - Remove HTML tags using BeautifulSoup.
    - **Ensure UTF-8 Compatibility:** Uses an `encode('utf-8', 'ignore').decode('utf-8')` strategy to remove or replace characters that are not valid UTF-8. This is crucial for preventing errors in systems like Astra DB.
    - Remove extra whitespace.
  - Processes platform and genre lists into comma-separated strings.
  - Stores the cleaned, extracted data in a list (`extracted_data`).
- **Inserting Data into SQLite:**
  - Connects to the SQLite database specified by `DB_FILENAME` (e.g., `game_data_cleaned.db`).
  - Creates a `games` table if it doesn't exist, with appropriate columns for the cleaned data.
  - Inserts the cleaned data from `extracted_data` into the `games` table using `INSERT OR IGNORE` to handle potential duplicates based on the game ID.
  - Commits changes and closes the database connection.

### 3. Exporting Data to Single Excel File (`DataFrame.py`)

- **Configuration:** Imports `sqlite3`, `pandas`. Defines the `DB_FILENAME` constant to connect to the correct database. Defines the output Excel filename (`EXCEL_FILE`).
- **Reading Data from SQLite:**
  - Connects to the SQLite database (`DB_FILENAME`) containing the _cleaned_ data.
  - Reads the entire `games` table into a Pandas DataFrame.
  - Closes the database connection.
- **Exporting Data to Excel:** Exports the DataFrame to a single Excel file (e.g., `game_data_cleaned.xlsx`) using `df.to_excel()`.

### 4. Exporting Data to Batched CSV Files (`DataFrame2.py`)

- **Configuration:** Imports `sqlite3`, `pandas`, `math`, `os`. Defines constants for `DB_FILENAME`, the base name for output CSVs (`OUTPUT_CSV_BASE_NAME`), the output directory (`OUTPUT_DIR`), and the number of records per file (`BATCH_SIZE`).
- **Reading Data in Batches:**
  - Connects to the SQLite database (`DB_FILENAME`).
  - Counts total records for progress indication.
  - Uses `pd.read_sql_query` with the `chunksize` parameter to read data from the `games` table in batches (memory efficient).
- **Exporting Batches to CSV:**
  - For each chunk (batch) of data read:
    - Constructs a unique filename (e.g., `game_data_batch_1.csv`).
    - Exports the chunk to its CSV file using `df.to_csv()`.
    - **Crucially specifies `encoding='utf-8'`** to ensure the output CSV is compatible with systems expecting UTF-8.
    - Uses `index=False` as the database ID column is usually sufficient.
  - Saves files to the specified `OUTPUT_DIR`.
  - Closes the database connection.

## Summary

- **`main.py`**: Fetches raw game data from the RAWG API and saves it to a JSON file.
- **`main_model.py`**: Reads the raw JSON data, cleans text fields (removing HTML, ensuring UTF-8 compatibility), extracts relevant information, and inserts the _cleaned_ data into an SQLite database.
- **`DataFrame.py`**: Reads the _cleaned_ data from the SQLite database and exports it all to a single Excel file.
- **`DataFrame2.py`**: Reads the _cleaned_ data from the SQLite database and exports it into multiple, smaller CSV files (batches), ensuring UTF-8 encoding for compatibility.

These scripts together form a pipeline for fetching, cleaning, processing, storing, and exporting game data from the RAWG API into formats suitable for analysis or ingestion into other systems.
