import os
import sqlite3
import sys
from datetime import datetime, date

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from SpindleStock.models import RawMaterial, RawMaterialLot, Recipe, RecipeMaterial, FinishedStock

def migrate_and_seed():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance", "spindleone.db"))
    print(f"Connecting to database at: {db_path}")

    if not os.path.exists(db_path):
        print("Database file does not exist yet. It will be created.")

    # 1. Connect directly to SQLite to drop specific stock tables safely
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables_to_drop = [
        "raw_material",
        "raw_material_lot",
        "production",
        "production_material",
        "production_lot_consumption",
        "recipe",
        "recipe_material",
        "finished_stock"
    ]

    print("Dropping outdated stock tables...")
    cursor.execute("PRAGMA foreign_keys = OFF")
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f" - Dropped table {table} (if it existed)")
        except Exception as e:
            print(f" - Error dropping table {table}: {e}")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

    # 2. Run db.create_all() inside app context to recreate tables with new schemas
    print("\nRecreating stock tables using SQLAlchemy create_all()...")
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✓ Tables successfully recreated.")

        # 3. Seed initial materials, lots, and recipes for dev validation
        print("\nSeeding initial development data...")
        
        # Raw materials
        sugar = RawMaterial(name="Sugar", unit="kg", alert_threshold=20.0)
        flour = RawMaterial(name="Flour", unit="kg", alert_threshold=50.0)
        db.session.add(sugar)
        db.session.add(flour)
        db.session.flush() # get IDs

        # Lots
        sugar_lot_1 = RawMaterialLot(
            raw_material_id=sugar.id,
            batch_number="LOT-SUGAR-A1",
            quantity=100.0,
            remaining_quantity=100.0,
            price_per_unit=50.0, # ₹50.00 / kg
            inward_date=date(2026, 6, 1),
            expiry_date=date(2027, 6, 1),
            is_exhausted=False
        )
        sugar_lot_2 = RawMaterialLot(
            raw_material_id=sugar.id,
            batch_number="LOT-SUGAR-B2",
            quantity=50.0,
            remaining_quantity=50.0,
            price_per_unit=60.0, # ₹60.00 / kg
            inward_date=date(2026, 6, 3),
            expiry_date=date(2027, 6, 3),
            is_exhausted=False
        )
        flour_lot_1 = RawMaterialLot(
            raw_material_id=flour.id,
            batch_number="LOT-FLOUR-X9",
            quantity=200.0,
            remaining_quantity=200.0,
            price_per_unit=30.0, # ₹30.00 / kg
            inward_date=date(2026, 6, 1),
            expiry_date=date(2027, 6, 1),
            is_exhausted=False
        )
        db.session.add(sugar_lot_1)
        db.session.add(sugar_lot_2)
        db.session.add(flour_lot_1)

        # Seed Recipe
        sourdough_recipe = Recipe(
            name="Sourdough Bread",
            finished_product_name="Sourdough Loaf"
        )
        db.session.add(sourdough_recipe)
        db.session.flush()

        flour_req = RecipeMaterial(
            recipe_id=sourdough_recipe.id,
            raw_material_id=flour.id,
            quantity_required=50.0,
            unit="kg"
        )
        sugar_req = RecipeMaterial(
            recipe_id=sourdough_recipe.id,
            raw_material_id=sugar.id,
            quantity_required=5.0,
            unit="kg"
        )
        db.session.add(flour_req)
        db.session.add(sugar_req)

        db.session.commit()
        print("✓ Seeding complete! Database is fully migrated and ready to run.")

if __name__ == "__main__":
    migrate_and_seed()
