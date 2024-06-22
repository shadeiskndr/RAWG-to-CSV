import sqlite3
import pandas as pd
import openpyxl

# Connect to the SQLite database
conn = sqlite3.connect('game_data.db')

query = 'SELECT * FROM games'
# query = "SELECT * FROM games WHERE platforms LIKE '%playstation%'"
df = pd.read_sql_query(query, conn)
conn.close()

df.index = range(1, len(df) + 1)

excel_file = 'excelGameData.xlsx'

# Export the data to an Excel file
df.to_excel(excel_file, index=True)

print(f'Data exported to {excel_file}')
