import sqlite3
import os

db_path = 'instance/tryon.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    # Try to find where the db is
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                print(f"Found db at {os.path.join(root, file)}")
                db_path = os.path.join(root, file)

print(f"Inspecting database at {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- Users ---")
    cursor.execute("SELECT id, email, credits FROM users;")
    users = cursor.fetchall()
    for user in users:
        print(user)
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
