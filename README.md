# RAWG-to-CSV

## Overview

This project provides a pipeline to fetch video game data from the [RAWG API](https://rawg.io/apidocs), clean and store it in an SQLite database, and export it to CSV or JSON files in batches. The pipeline ensures all text is UTF-8 compatible and cleans HTML from descriptions, making the data suitable for downstream applications such as analytics, machine learning, or ingestion into other databases.

**Main Steps:**

1. Fetch game data from RAWG API (`1-fetch_games.py`)
2. Clean and store data in SQLite (`2-cleaned_json_to_sqlite.py`)
3. Export data to batched CSV/JSON files (`3-export_sqlite_to_csv_json.py`)
4. Optionally fetch missing games by ID (`4-fetch_unfetched_games.py`)

---

## Local Setup

### Set Up a Virtual Environment

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

### 3. Set RAWG API Key

- Copy `.env.example` to `.env` and fill in your RAWG API key, or set the environment variable in your shell:
  ```bash
  export RAWG_API_KEY=your_actual_rawg_api_key_here
  ```

---

## Pipeline Usage

### Step 1: Fetch Game Data from RAWG API

Fetches up to 4000 games (200 pages × 20 games per page) and saves detailed info to `fetched_games.json`.

```bash
python 1-fetch_games.py
```

- **Output:** `fetched_games.json`
- Handles interruptions gracefully (Ctrl+C will save progress).

---

### Step 2: Clean and Store Data in SQLite

Reads the raw JSON, cleans all text fields (removes HTML, enforces UTF-8), and inserts into `game_data_cleaned.db`.

```bash
python 2-cleaned_json_to_sqlite.py
```

- **Input:** `fetched_games.json` (or change `INPUT_JSON` at the top of the script)
- **Output:** `game_data_cleaned.db` (SQLite database)

---

### Step 3: Export Data to Batched CSV/JSON Files

Exports the cleaned SQLite data to batches of CSV and/or JSON files (default batch size: 500 records per file).

```bash
python 3-export_sqlite_to_csv_json.py --format both
```

- `--format` can be `csv`, `json`, or `both` (default: both)
- **Outputs:**
  - CSV files in `batched_csv_output/`
  - JSON files in `batched_json_output/`
- Each file contains up to 500 records.
- Descriptions are truncated to ~7900 bytes for compatibility.

---

### Step 4 (Optional): Fetch Unfetched Games by ID

If you have a list of game IDs (e.g., from another source) and want to fetch only those not already in your database:

1. Run:

```bash
python 4-fetch_unfetched_games.py
```

- **Output:** `newly_fetched_games.json` (can be merged and processed with Step 2)

---

## File/Script Overview

| Script/File                      | Purpose                                                   |
| -------------------------------- | --------------------------------------------------------- |
| `1-fetch_games.py`               | Fetches game data from RAWG API and saves as JSON.        |
| `2-cleaned_json_to_sqlite.py`    | Cleans JSON data and loads it into an SQLite database.    |
| `3-export_sqlite_to_csv_json.py` | Exports SQLite data to batched CSV and/or JSON files.     |
| `4-fetch_unfetched_games.py`     | Fetches details for game IDs not already in the database. |
| `.env.example`                   | Example environment file for RAWG API key.                |
| `fetched_games.json`             | Output of step 1: raw game data from RAWG API.            |
| `game_data_cleaned.db`           | Output of step 2: cleaned data in SQLite format.          |
| `newly_fetched_games.json`       | Output of step 3: newly fetched games by ID.              |
| `batched_csv_output/`            | Output directory for CSV batches.                         |
| `batched_json_output/`           | Output directory for JSON batches.                        |

---

## Notes & Tips

- **API Rate Limiting:** Scripts respect RAWG API rate limits (10 requests/sec). If you hit limits, increase sleep times.
- **Interruptions:** `1-fetch_games.py` saves progress on interruption (Ctrl+C).
- **Data Cleaning:** All text fields are cleaned for UTF-8 and HTML tags are removed from descriptions.
- **Batch Export:** Batch size and output directories can be changed at the top of `3-export_sqlite_to_csv_json.py`.
- **Custom Input/Output:** You can change input/output filenames by editing the constants at the top of each script.

---

## Example Workflow

1. Fetch games:
   ```bash
   python 1-fetch_games.py
   ```
2. Clean and load into SQLite:
   ```bash
   python 2-cleaned_json_to_sqlite.py
   ```
3. Export to CSV/JSON batches:
   ```bash
   python 3-export_sqlite_to_csv_json.py --format both
   ```
4. (Optional) Fetch missing games by ID:
   ```bash
   python 4-fetch_unfetched_games.py
   ```

---
