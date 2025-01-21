import sqlite3
import pandas as pd
import math
import os
import json
import argparse

# --- Configuration ---
DB_FILENAME = 'game_data_cleaned.db'
CSV_BASE_NAME = 'game_data_batch'
JSON_BASE_NAME = 'game_data_batch'
CSV_OUTPUT_DIR = 'batched_csv_output'
JSON_OUTPUT_DIR = 'batched_json_output'
BATCH_SIZE = 500
MAX_DESCRIPTION_BYTES = 7900  # Setting slightly below 8000 for safety

def ensure_dir(directory):
    if directory and not os.path.exists(directory):
        print(f"Creating output directory: '{directory}'")
        os.makedirs(directory)

def truncate_to_max_bytes(text, max_bytes):
    if not text:
        return text
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes-3].decode('utf-8', errors='ignore')
    return truncated + "..."

def process_chunk(chunk_df):
    truncated_count = 0
    if 'description' in chunk_df.columns:
        for idx, row in chunk_df.iterrows():
            if pd.notna(row['description']):
                original_desc = row['description']
                truncated_desc = truncate_to_max_bytes(original_desc, MAX_DESCRIPTION_BYTES)
                if original_desc != truncated_desc:
                    truncated_count += 1
                    chunk_df.at[idx, 'description'] = truncated_desc
                chunk_df.at[idx, 'vecdesc'] = truncated_desc
    return truncated_count

def export_csv(chunks, num_batches, total_records):
    ensure_dir(CSV_OUTPUT_DIR)
    batch_num = 1
    for chunk_df in chunks:
        truncated_count = process_chunk(chunk_df)
        output_filename = f"{CSV_BASE_NAME}_{batch_num}.csv"
        output_filepath = os.path.join(CSV_OUTPUT_DIR, output_filename)
        print(f"Processing batch {batch_num}/{num_batches}... Writing to '{output_filepath}'")
        if truncated_count > 0:
            print(f"  Note: Truncated {truncated_count} descriptions that exceeded {MAX_DESCRIPTION_BYTES} bytes")
        chunk_df.to_csv(output_filepath, index=False, encoding='utf-8')
        batch_num += 1
    print(f"\nSuccessfully exported {total_records} records into {batch_num - 1} CSV files.")

def export_json(chunks, num_batches, total_records):
    ensure_dir(JSON_OUTPUT_DIR)
    batch_num = 1
    for chunk_df in chunks:
        output_filename = f"{JSON_BASE_NAME}_{batch_num}.json"
        output_filepath = os.path.join(JSON_OUTPUT_DIR, output_filename)
        print(f"Processing batch {batch_num}/{num_batches}... Writing to '{output_filepath}'")
        json_data = json.loads(chunk_df.to_json(orient='records', force_ascii=False))
        truncated_count = 0
        for item in json_data:
            if 'description' in item and item['description']:
                original_desc = item['description']
                truncated_desc = truncate_to_max_bytes(original_desc, MAX_DESCRIPTION_BYTES)
                if original_desc != truncated_desc:
                    truncated_count += 1
                item['description'] = truncated_desc
                item['vecdesc'] = truncated_desc
        if truncated_count > 0:
            print(f"  Note: Truncated {truncated_count} descriptions that exceeded {MAX_DESCRIPTION_BYTES} bytes")
        with open(output_filepath, 'w', encoding='utf-8') as json_file:
            formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False)
            json_file.write(formatted_json)
        batch_num += 1
    print(f"\nSuccessfully exported {total_records} records into {batch_num - 1} JSON files.")

def main():
    parser = argparse.ArgumentParser(description="Export games table to CSV and/or JSON in batches.")
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='both',
                        help="Output format: csv, json, or both (default: both)")
    args = parser.parse_args()

    print(f"Connecting to database '{DB_FILENAME}'...")
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
    except sqlite3.OperationalError as e:
        print(f"Error connecting to database: {e}")
        print(f"Make sure the database file '{DB_FILENAME}' exists and the path is correct.")
        exit(1)

    try:
        cursor.execute('SELECT COUNT(*) FROM games')
        total_records = cursor.fetchone()[0]
        print(f"Found {total_records} total records in the 'games' table.")
        if total_records == 0:
            print("Database table is empty. No files will be generated.")
            conn.close()
            exit(0)
        num_batches = math.ceil(total_records / BATCH_SIZE)
        print(f"Will create approximately {num_batches} batch file(s).")
    except sqlite3.OperationalError as e:
        print(f"Error counting records: {e}")
        print("Ensure the 'games' table exists in the database.")
        conn.close()
        exit(1)

    query = 'SELECT * FROM games'
    print(f"\nReading data from '{DB_FILENAME}' and exporting in batches of {BATCH_SIZE}...")

    try:
        chunks = pd.read_sql_query(query, conn, chunksize=BATCH_SIZE)
        # We need to be able to iterate multiple times if both formats are selected
        if args.format == 'csv':
            export_csv(chunks, num_batches, total_records)
        elif args.format == 'json':
            export_json(chunks, num_batches, total_records)
        elif args.format == 'both':
            # Read all chunks into memory (could be optimized for huge datasets)
            all_chunks = list(chunks)
            export_csv((chunk.copy() for chunk in all_chunks), num_batches, total_records)
            export_json((chunk.copy() for chunk in all_chunks), num_batches, total_records)
    except pd.io.sql.DatabaseError as e:
        print(f"Error reading data from table: {e}")
        print("Ensure the 'games' table exists and the query is correct.")
    except Exception as e:
        print(f"An unexpected error occurred during batch processing: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
