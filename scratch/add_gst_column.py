import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    bind = db.engine
    print(f"Connected to dialect: {bind.dialect.name}")
    with bind.begin() as conn:
        if bind.dialect.name == 'postgresql':
            print("Adding column gst_rate to PostgreSQL table Invoice...")
            conn.execute(text('ALTER TABLE "Invoice" ADD COLUMN IF NOT EXISTS gst_rate FLOAT DEFAULT 0.0;'))
            print("PostgreSQL migration complete.")
        else:
            print("Adding column gst_rate to SQLite table Invoice...")
            try:
                conn.execute(text('ALTER TABLE "Invoice" ADD COLUMN gst_rate FLOAT DEFAULT 0.0;'))
                print("SQLite migration complete.")
            except Exception as e:
                print(f"SQLite migration ignored (column might already exist): {e}")
