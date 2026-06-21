import os
import sqlite3
import sys

# Add parent directory to path to import app config if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def migrate():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance", "spindleone.db"))
    print(f"Connecting to database at: {db_path}")

    if not os.path.exists(db_path):
        print("Database file does not exist yet. Run the application to create it.")
        return

    # Connect to sqlite database directly
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check table columns of AccountCashflow
        cursor.execute("PRAGMA table_info(AccountCashflow)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns in AccountCashflow: {columns}")

        if "sale_type" not in columns:
            print("Adding 'sale_type' column to 'AccountCashflow' table...")
            cursor.execute("ALTER TABLE AccountCashflow ADD COLUMN sale_type VARCHAR(25)")
            conn.commit()
            print("✓ Column 'sale_type' added successfully.")
        else:
            print("✓ Column 'sale_type' already exists.")

    except Exception as e:
        print(f"Error during sqlite ALTER: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
