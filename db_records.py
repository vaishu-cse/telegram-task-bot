import sqlite3

conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM tasks")
tasks = cursor.fetchall()
conn.close()

for task in tasks:
    print(f"ID: {task[0]}, User ID: {task[1]}, Task: {task[2]}, Time: {task[3]}")
    print(f"tasks:::: {task}")
