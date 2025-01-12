import sqlite3
import pandas as pd
import math
import os

# --- Configuration ---
# Database filename (should match the output of main_model.py)
DB_FILENAME = 'game_data_cleaned.db'
# Base name for output CSV files
OUTPUT_CSV_BASE_NAME = 'game_data_batch'
# Directory to save the CSV files (optional, creates if not exists)
OUTPUT_DIR = 'batched_csv_output'
# Number of records per CSV file
BATCH_SIZE = 500

# --- Create output directory if it doesn't exist ---
if OUTPUT_DIR and not os.path.exists(OUTPUT_DIR):
    print(f"Creating output directory: '{OUTPUT_DIR}'")
    os.makedirs(OUTPUT_DIR)

# --- Database Connection ---
print(f"Connecting to database '{DB_FILENAME}'...")
try:
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor() # Use cursor for counting
except sqlite3.OperationalError as e:
    print(f"Error connecting to database: {e}")
    print(f"Make sure the database file '{DB_FILENAME}' exists and the path is correct.")
    exit(1)

# --- Get Total Record Count (for progress indication) ---
try:
    cursor.execute('SELECT COUNT(*) FROM games')
    total_records = cursor.fetchone()[0]
    print(f"Found {total_records} total records in the 'games' table.")
    if total_records == 0:
        print("Database table is empty. No CSV files will be generated.")
        conn.close()
        exit(0)
    num_batches = math.ceil(total_records / BATCH_SIZE)
    print(f"Will create approximately {num_batches} batch file(s).")
except sqlite3.OperationalError as e:
    print(f"Error counting records: {e}")
    print("Ensure the 'games' table exists in the database.")
    conn.close()
    exit(1)

# --- Process in Batches ---
query = 'SELECT * FROM games'
batch_num = 1
print(f"\nReading data from '{DB_FILENAME}' and exporting in batches of {BATCH_SIZE}...")

try:
    # Use pandas read_sql_query with chunksize for memory efficiency
    for chunk_df in pd.read_sql_query(query, conn, chunksize=BATCH_SIZE):
        # Define the output filename for this batch
        output_filename = f"{OUTPUT_CSV_BASE_NAME}_{batch_num}.csv"
        if OUTPUT_DIR:
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
        else:
            output_filepath = output_filename

        print(f"Processing batch {batch_num}/{num_batches}... Writing to '{output_filepath}'")

        # Export the current chunk to CSV
        # Use encoding='utf-8' for compatibility (like with Astra DB)
        # Use index=False as the database 'id' column is likely the true identifier
        chunk_df.to_csv(output_filepath, index=False, encoding='utf-8')

        batch_num += 1

    print(f"\nSuccessfully exported {total_records} records into {batch_num - 1} CSV files.")

except pd.io.sql.DatabaseError as e:
     print(f"Error reading data from table: {e}")
     print("Ensure the 'games' table exists and the query is correct.")
except Exception as e:
    print(f"An unexpected error occurred during batch processing: {e}")
finally:
    # Always close the connection
    if conn:
        conn.close()
        print("Database connection closed.")

