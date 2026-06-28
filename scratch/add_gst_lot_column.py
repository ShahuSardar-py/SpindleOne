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
            print("Adding columns unit_rate and gst_rate to PostgreSQL table raw_material_lot...")
            conn.execute(text('ALTER TABLE raw_material_lot ADD COLUMN IF NOT EXISTS unit_rate FLOAT DEFAULT 0.0;'))
            conn.execute(text('ALTER TABLE raw_material_lot ADD COLUMN IF NOT EXISTS gst_rate FLOAT DEFAULT 0.0;'))
            print("PostgreSQL migration complete.")
        else:
            print("Adding columns to SQLite table raw_material_lot...")
            try:
                conn.execute(text('ALTER TABLE raw_material_lot ADD COLUMN unit_rate FLOAT DEFAULT 0.0;'))
            except Exception as e:
                print(f"SQLite migration unit_rate ignored: {e}")
            try:
                conn.execute(text('ALTER TABLE raw_material_lot ADD COLUMN gst_rate FLOAT DEFAULT 0.0;'))
            except Exception as e:
                print(f"SQLite migration gst_rate ignored: {e}")
            print("SQLite migration complete.")
