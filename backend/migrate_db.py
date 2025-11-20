import sqlite3
import os

# Target the root instance database
db_path = os.path.join(os.getcwd(), 'instance', 'tryon.db')
print(f"Connecting to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(clothing_items)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Add is_generated column
    if 'is_generated' in columns:
        print("Column 'is_generated' already exists.")
    else:
        print("Adding column 'is_generated'...")
        cursor.execute("ALTER TABLE clothing_items ADD COLUMN is_generated BOOLEAN DEFAULT 0")
        conn.commit()
        print("Successfully added 'is_generated' column.")
    
    # Add price column
    if 'price' in columns:
        print("Column 'price' already exists.")
    else:
        print("Adding column 'price'...")
        cursor.execute("ALTER TABLE clothing_items ADD COLUMN price FLOAT DEFAULT 0.0")
        conn.commit()
        print("Successfully added 'price' column.")
    
    # Add wear_count column
    if 'wear_count' in columns:
        print("Column 'wear_count' already exists.")
    else:
        print("Adding column 'wear_count'...")
        cursor.execute("ALTER TABLE clothing_items ADD COLUMN wear_count INTEGER DEFAULT 0")
        conn.commit()
        print("Successfully added 'wear_count' column.")

    # Check users table columns
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [info[1] for info in cursor.fetchall()]

    # Add credits column
    if 'credits' in user_columns:
        print("Column 'credits' already exists in users table.")
    else:
        print("Adding column 'credits'...")
        cursor.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 5")
        conn.commit()
        print("Successfully added 'credits' column.")

    # Add last_daily_login column
    if 'last_daily_login' in user_columns:
        print("Column 'last_daily_login' already exists in users table.")
    else:
        print("Adding column 'last_daily_login'...")
        # Use a fixed string for default to avoid "non-constant default" error in some SQLite versions
        cursor.execute("ALTER TABLE users ADD COLUMN last_daily_login DATETIME DEFAULT '2024-01-01 00:00:00'")
        conn.commit()
        print("Successfully added 'last_daily_login' column.")
        
    conn.close()
    print("\n✅ Database migration completed successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
