import os
import sqlite3
import sys

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db

def repair():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance", "spindleone.db"))
    print(f"Connecting to database at: {db_path}")

    if not os.path.exists(db_path):
        print("Database file does not exist yet. Run the application to create it.")
        return

    # Connect to sqlite database directly
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check table columns
        cursor.execute("PRAGMA table_info(raw_material)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns in raw_material: {columns}")

        if "alert_threshold" not in columns:
            print("Adding 'alert_threshold' column to 'raw_material' table...")
            cursor.execute("ALTER TABLE raw_material ADD COLUMN alert_threshold FLOAT DEFAULT 25.0")
            conn.commit()
            print("✓ Column 'alert_threshold' added successfully.")
        else:
            print("✓ Column 'alert_threshold' already exists.")

    except Exception as e:
        print(f"Error during sqlite ALTER: {e}")
    finally:
        conn.close()

    # Trigger create_all within app context to make sure recipe and recipe_material tables exist
    print("\nEnsuring all tables are created via SQLAlchemy create_all()...")
    app = create_app()
    with app.app_context():
        db.create_all()
    print("✓ All tables verified and created successfully.")

if __name__ == "__main__":
    repair()
