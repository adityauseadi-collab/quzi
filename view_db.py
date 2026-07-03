import sqlite3
from tabulate import tabulate

conn = sqlite3.connect("instance/quizmaster.db")
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in Database:")
for table in tables:
    print("-", table[0])

# Display the users table
table_name = "questions"  # Change this to the desired table name

cursor.execute(f"SELECT * FROM {table_name}")

rows = cursor.fetchall()

# Get column names
columns = [description[0] for description in cursor.description]

print(f"\nData from '{table_name}' table:\n")
print(tabulate(rows, headers=columns, tablefmt="grid"))

conn.close()