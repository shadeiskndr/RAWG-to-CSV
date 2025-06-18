# RAWG-to-VectorDB

## Overview

This project provides a robust pipeline to fetch video game data from the [RAWG API](https://rawg.io/apidocs), clean and store it in an SQLite database, filter by platform, generate OpenAI vector embeddings, and ingest the results into a vector-enabled Astra DB collection. The pipeline ensures all text is UTF-8 compatible, strips HTML from descriptions, and is suitable for downstream analytics, search, or AI applications.

**Pipeline Steps:**

1. Fetch game data from RAWG API into SQLite (`1-fetch_games_by_page.py`)
2. Optionally fetch missing games by ID (`2-fetch_unfetched_games_by_id.py`)
3. Filter games by platform (e.g., PlayStation) into a new SQLite DB (`3-filter_games_by_platform.py`)
4. Generate OpenAI vector embeddings for each game (`4-generate_embeddings.py`)
5. Ingest the enriched data into Astra DB (`5-ingest_to_astra_db.py`)

---

## Local Setup

### 1. Set Up a Virtual Environment

```bash
python3 -m venv venv
```

- Activate on Windows (Git Bash):
  ```bash
  source venv/Scripts/activate
  ```
- Activate on Windows (cmd):
  ```bash
  .\venv\Scripts\activate.bat
  ```
- Activate on Windows (PowerShell):
  ```bash
  .\venv\Scripts\Activate.ps1
  ```
- Activate on Linux/macOS:
  ```bash
  source venv/bin/activate
  ```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

- Copy `.env.example` to `.env` and fill in your API keys and Astra DB info:
  ```bash
  cp .env.example .env
  ```
  Edit `.env` and set:
  - `RAWG_API_KEY`
  - `OPENAI_API_KEY`
  - `ASTRA_DB_API_ENDPOINT`
  - `ASTRA_DB_APPLICATION_TOKEN`
  - `ASTRA_DB_COLLECTION_NAME`

---

## Pipeline Usage

### Step 1: Fetch Game Data from RAWG API

Fetches pages of games from the RAWG API, retrieves full details for each game, cleans and normalizes the data, and stores it directly in `game_data_live.db` (SQLite).

```bash
python 1-fetch_games_by_page.py
```

- **Output:** `game_data_live.db`
- Handles interruptions gracefully (Ctrl+C will flush and exit safely).
- You can adjust `PAGE_SIZE`, `MAX_PAGES`, and `BATCH_SIZE` at the top of the script.

---

### Step 2 (Optional): Fetch Unfetched Games by ID

If you want to fill gaps in your database (e.g., for specific IDs), this script checks which IDs are missing in `game_data_live.db` and fetches them individually.

```bash
python 2-fetch_unfetched_games_by_id.py
```

- **Output:** Adds missing games to `game_data_live.db`
- Configure the ID range (`START_ID`, `END_ID`) at the top of the script.

---

### Step 3: Filter Games by Platform

Filters games in `game_data_live.db` by platform keyword(s) (e.g., "PlayStation") and writes the filtered, cleaned results to `game_data_filtered.db`.

```bash
python 3-filter_games_by_platform.py
```

- **Output:** `game_data_filtered.db`
- Edit `PLATFORM_KEYWORDS` in the script to filter for different platforms.

---

### Step 4: Generate OpenAI Embeddings

Generates OpenAI vector embeddings for each row in `game_data_filtered.db` and stores them in a new `embedding` column.

```bash
python 4-generate_embeddings.py
```

- **Output:** Adds an `embedding` column to `game_data_filtered.db`
- Requires `OPENAI_API_KEY` in your `.env`
- Uses the `text-embedding-3-large` model by default.

---

### Step 5: Ingest to Astra DB

Streams all rows from `game_data_filtered.db` (with embeddings) into your Astra DB vector collection.

```bash
python 5-ingest_to_astra_db.py
```

- **Output:** Data ingested into your Astra DB collection
- Requires Astra DB environment variables in your `.env`
- Handles batching and retries for robust ingestion.

---

## File/Script Overview

| Script/File                        | Purpose                                                 |
| ---------------------------------- | ------------------------------------------------------- |
| `1-fetch_games_by_page.py`         | Fetches games from RAWG API and stores them in SQLite.  |
| `2-fetch_unfetched_games_by_id.py` | Fetches missing games by ID and adds them to SQLite.    |
| `3-filter_games_by_platform.py`    | Filters games by platform and outputs a new SQLite DB.  |
| `4-generate_embeddings.py`         | Generates OpenAI embeddings for each game.              |
| `5-ingest_to_astra_db.py`          | Ingests the enriched data into Astra DB.                |
| `.env.example`                     | Example environment file for API keys and Astra config. |
| `requirements.txt`                 | Python dependencies.                                    |
| `game_data_live.db`                | Main SQLite database with all fetched games.            |
| `game_data_filtered.db`            | Filtered SQLite database (e.g., PlayStation only).      |

---

## Notes & Tips

- **API Rate Limiting:** Scripts respect RAWG and OpenAI rate limits. If you hit limits, increase sleep times in the scripts.
- **Interruptions:** All scripts handle Ctrl+C gracefully and flush pending data.
- **Data Cleaning:** All text fields are cleaned for UTF-8 and HTML tags are removed from descriptions.
- **Custom Filtering:** Change `PLATFORM_KEYWORDS` in `3-filter_games_by_platform.py` to filter for other platforms.
- **Embeddings:** Embeddings are stored as JSON arrays in the `embedding` column.
- **Astra DB:** Make sure your Astra DB collection is vector-enabled and the environment variables are set.

---

## Example Workflow

1. Fetch games:
   ```bash
   python 1-fetch_games_by_page.py
   ```
2. (Optional) Fetch missing games by ID:
   ```bash
   python 2-fetch_unfetched_games_by_id.py
   ```
3. Filter by platform:
   ```bash
   python 3-filter_games_by_platform.py
   ```
4. Generate embeddings:
   ```bash
   python 4-generate_embeddings.py
   ```
5. Ingest to Astra DB:
   ```bash
   python 5-ingest_to_astra_db.py
   ```

---
