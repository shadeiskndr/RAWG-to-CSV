import sqlite3
import pandas as pd
import math
import os
import json

# --- Configuration ---
# Database filename (should match the output of main_model.py)
DB_FILENAME = 'game_data_cleaned.db'
# Base name for output JSON files
OUTPUT_JSON_BASE_NAME = 'game_data_batch'
# Directory to save the JSON files (optional, creates if not exists)
OUTPUT_DIR = 'batched_json_output'
# Number of records per JSON file
BATCH_SIZE = 500
# Maximum length for description field (in bytes)
MAX_DESCRIPTION_BYTES = 7900  # Setting slightly below 8000 for safety

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
        print("Database table is empty. No JSON files will be generated.")
        conn.close()
        exit(0)
    num_batches = math.ceil(total_records / BATCH_SIZE)
    print(f"Will create approximately {num_batches} batch file(s).")
except sqlite3.OperationalError as e:
    print(f"Error counting records: {e}")
    print("Ensure the 'games' table exists in the database.")
    conn.close()
    exit(1)

# --- Helper function to truncate text to max bytes ---
def truncate_to_max_bytes(text, max_bytes):
    if not text:
        return text
    
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    
    # Truncate and add ellipsis
    truncated = encoded[:max_bytes-3].decode('utf-8', errors='ignore')
    return truncated + "..."

# --- Process in Batches ---
query = 'SELECT * FROM games'
# query = "SELECT * FROM games WHERE platforms LIKE '%playstation%'"
batch_num = 1
print(f"\nReading data from '{DB_FILENAME}' and exporting in batches of {BATCH_SIZE}...")

try:
    # Use pandas read_sql_query with chunksize for memory efficiency
    for chunk_df in pd.read_sql_query(query, conn, chunksize=BATCH_SIZE):
        # Define the output filename for this batch
        output_filename = f"{OUTPUT_JSON_BASE_NAME}_{batch_num}.json"
        if OUTPUT_DIR:
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
        else:
            output_filepath = output_filename

        print(f"Processing batch {batch_num}/{num_batches}... Writing to '{output_filepath}'")

        # Convert DataFrame to JSON and parse it back to a Python object
        json_data = json.loads(chunk_df.to_json(orient='records', force_ascii=False))
        
        # Add vecdesc field and truncate description if needed
        truncated_count = 0
        for item in json_data:
            if 'description' in item and item['description']:
                # Truncate description if it's too long
                original_desc = item['description']
                truncated_desc = truncate_to_max_bytes(original_desc, MAX_DESCRIPTION_BYTES)
                
                if original_desc != truncated_desc:
                    truncated_count += 1
                
                item['description'] = truncated_desc
                # Use the same truncated value for vecdesc
                item['vecdesc'] = truncated_desc
        
        if truncated_count > 0:
            print(f"  Note: Truncated {truncated_count} descriptions that exceeded {MAX_DESCRIPTION_BYTES} bytes")
        
        # Write the JSON data to file with pretty formatting
        with open(output_filepath, 'w', encoding='utf-8') as json_file:
            formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False)
            json_file.write(formatted_json)

        batch_num += 1

    print(f"\nSuccessfully exported {total_records} records into {batch_num - 1} JSON files.")

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
