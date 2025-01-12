import sqlite3
import pandas as pd
# import openpyxl # Keep if you still want Excel output

# --- Database Filename Consistency ---
# Make sure this matches the filename used in the updated main_model.py
DB_FILENAME = 'game_data_cleaned.db'

# --- Output Filenames ---
EXCEL_FILE = 'game_data_cleaned.xlsx'
CSV_FILE = 'game_data_cleaned.csv' # Define a CSV output filename

# Connect to the SQLite database
print(f"Connecting to database '{DB_FILENAME}'...")
try:
    conn = sqlite3.connect(DB_FILENAME)
except sqlite3.OperationalError as e:
    print(f"Error connecting to database: {e}")
    print(f"Make sure the database file '{DB_FILENAME}' exists and the path is correct.")
    exit(1)

# Query to select all data
query = 'SELECT * FROM games'
# query = "SELECT * FROM games WHERE platforms LIKE '%playstation%'" # Example filter

print("Reading data from the 'games' table...")
try:
    df = pd.read_sql_query(query, conn)
except pd.io.sql.DatabaseError as e:
     print(f"Error reading data from table: {e}")
     print("Ensure the 'games' table exists in the database.")
     conn.close()
     exit(1)
finally:
    # Always close the connection
    if conn:
        conn.close()
        print("Database connection closed.")

# Set the DataFrame index to start from 1 (optional, but matches previous script)
df.index = range(1, len(df) + 1)
print(f"Read {len(df)} records.")

# --- Exporting Data ---

# Option 1: Export to Excel (Pandas usually handles UTF-8 well for xlsx via openpyxl)
# print(f"Exporting data to Excel file: '{EXCEL_FILE}'...")
# try:
#     df.to_excel(EXCEL_FILE, index=True, engine='openpyxl')
#     print(f"Data successfully exported to {EXCEL_FILE}")
# except Exception as e:
#     print(f"Error exporting to Excel: {e}")

# Option 2: Export directly to CSV with explicit UTF-8 encoding (Recommended for Astra DB)
print(f"Exporting data to CSV file: '{CSV_FILE}' with UTF-8 encoding...")
try:
    # Use encoding='utf-8' and index=False if Astra doesn't need the row number as a column
    # Use index=True if you want the 1-based index included in the CSV
    df.to_csv(CSV_FILE, index=True, encoding='utf-8')
    print(f"Data successfully exported to {CSV_FILE}")
except Exception as e:
    print(f"Error exporting to CSV: {e}")

