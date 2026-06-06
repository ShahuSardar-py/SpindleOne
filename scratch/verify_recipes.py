import sys
import os
from datetime import datetime, date

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from SpindleStock.models import RawMaterial, RawMaterialLot, Recipe, RecipeMaterial, Production, ProductionMaterial, ProductionLotConsumption, FinishedStock
from SpindleStock.routes import consume_fifo
from app.config import Config

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True

def run_tests():
    print("=== STARTING FIFO LOTS VERIFICATION TESTS ===")
    app = create_app(TestConfig)

    with app.app_context():
        # Create all tables in memory
        db.create_all()
        print("1. In-memory database tables created successfully.")

        # 2. Add Test Raw Materials (Catalog)
        print("\nAdding test raw materials to catalog...")
        sugar = RawMaterial(name="Sugar", unit="kg", alert_threshold=20.0)
        flour = RawMaterial(name="Flour", unit="kg", alert_threshold=50.0)
        db.session.add(sugar)
        db.session.add(flour)
        db.session.flush()
        print(f"Created Raw Material Sugar (ID: {sugar.id}, Unit: {sugar.unit})")
        print(f"Created Raw Material Flour (ID: {flour.id}, Unit: {flour.unit})")

        # 3. Add Multiple Lots for FIFO Testing
        print("\nAdding purchase lots to inventory...")
        # Sugar Lot 1: 100 kg at ₹50/kg
        sugar_lot1 = RawMaterialLot(
            raw_material_id=sugar.id,
            batch_number="LOT-SUGAR-01",
            quantity=100.0,
            remaining_quantity=100.0,
            price_per_unit=50.0,
            inward_date=date(2026, 6, 1),
            is_exhausted=False
        )
        # Sugar Lot 2: 50 kg at ₹60/kg (inwarded later)
        sugar_lot2 = RawMaterialLot(
            raw_material_id=sugar.id,
            batch_number="LOT-SUGAR-02",
            quantity=50.0,
            remaining_quantity=50.0,
            price_per_unit=60.0,
            inward_date=date(2026, 6, 3),
            is_exhausted=False
        )
        # Flour Lot 1: 200 kg at ₹30/kg
        flour_lot1 = RawMaterialLot(
            raw_material_id=flour.id,
            batch_number="LOT-FLOUR-01",
            quantity=200.0,
            remaining_quantity=200.0,
            price_per_unit=30.0,
            inward_date=date(2026, 6, 1),
            is_exhausted=False
        )
        db.session.add(sugar_lot1)
        db.session.add(sugar_lot2)
        db.session.add(flour_lot1)
        db.session.commit()
        print("✓ Successfully created sugar_lot1 (100 kg @ ₹50), sugar_lot2 (50 kg @ ₹60), flour_lot1 (200 kg @ ₹30).")

        # Verify total quantity calculation on catalog model
        assert sugar.total_quantity == 150.0, f"Expected total sugar qty 150.0, got {sugar.total_quantity}"
        assert flour.total_quantity == 200.0, f"Expected total flour qty 200.0, got {flour.total_quantity}"
        print("✓ Property RawMaterial.total_quantity correctly calculates sum across active lots.")

        # 4. Create a Recipe (linking by raw_material_id)
        print("\nCreating a test recipe...")
        cake_recipe = Recipe(
            name="Vanilla Cake",
            finished_product_name="Vanilla Sponge Cake"
        )
        db.session.add(cake_recipe)
        db.session.flush()

        sugar_req = RecipeMaterial(
            recipe_id=cake_recipe.id,
            raw_material_id=sugar.id,
            quantity_required=10.0,
            unit="kg"
        )
        flour_req = RecipeMaterial(
            recipe_id=cake_recipe.id,
            raw_material_id=flour.id,
            quantity_required=20.0,
            unit="kg"
        )
        db.session.add(sugar_req)
        db.session.add(flour_req)
        db.session.commit()
        print(f"Created Recipe '{cake_recipe.name}' (Product: '{cake_recipe.finished_product_name}') linked to RawMaterial IDs:")
        for mat in cake_recipe.materials:
            print(f" - ID {mat.raw_material_id} ({mat.raw_material.name}): {mat.quantity_required} {mat.unit}")

        # 5. Simulate Production using Recipe and FIFO Consumption
        # We need to consume:
        # Sugar: 120 kg (drains Lot 1 [100 kg] fully, and Lot 2 [20 kg] partially)
        # Flour: 50 kg (drains Lot 1 [50 kg] partially)
        print("\nSimulating production saving using FIFO consumption...")
        
        prod = Production(
            product_name=cake_recipe.finished_product_name,
            quantity_produced=5.0,
            expiry_date=None,
            total_raw_material_cost=0.0
        )
        db.session.add(prod)
        db.session.flush()

        materials_to_use = [
            {"id": sugar.id, "qty": 120.0, "name": "Sugar"},
            {"id": flour.id, "qty": 50.0, "name": "Flour"}
        ]

        total_production_cost = 0.0

        for entry in materials_to_use:
            material = RawMaterial.query.get(entry["id"])
            assert material is not None
            
            # Stock check
            stock_qty = material.total_quantity
            assert stock_qty >= entry["qty"], f"Not enough {entry['name']} in stock!"

            # FIFO Drain
            consumptions, material_cost = consume_fifo(material.id, entry["qty"])

            # Save ProductionMaterial row
            usage = ProductionMaterial(
                production_id=prod.id,
                raw_material_id=material.id,
                quantity_used=entry["qty"],
                computed_cost=material_cost
            )
            db.session.add(usage)
            db.session.flush()

            # Save ProductionLotConsumption audit rows
            for consumption in consumptions:
                consumption.production_material_id = usage.id
                db.session.add(consumption)

            total_production_cost += material_cost

        # Save finished stock
        finished = FinishedStock(
            product_name=prod.product_name,
            quantity=prod.quantity_produced,
            expiry_date=prod.expiry_date
        )
        db.session.add(finished)
        
        prod.total_raw_material_cost = total_production_cost
        db.session.commit()

        # 6. Verify Lot Deduction State after FIFO execution
        print("\nVerifying database state after production...")
        # Sugar Lot 1 should be exhausted (remaining: 0)
        # Sugar Lot 2 should have 30 kg remaining (50 - 20)
        # Flour Lot 1 should have 150 kg remaining (200 - 50)
        s_lot1 = RawMaterialLot.query.filter_by(batch_number="LOT-SUGAR-01").first()
        s_lot2 = RawMaterialLot.query.filter_by(batch_number="LOT-SUGAR-02").first()
        f_lot1 = RawMaterialLot.query.filter_by(batch_number="LOT-FLOUR-01").first()

        assert s_lot1.is_exhausted == True, "Sugar Lot 1 should be exhausted!"
        assert s_lot1.remaining_quantity == 0.0, f"Expected Sugar Lot 1 remaining quantity 0, got {s_lot1.remaining_quantity}"
        
        assert s_lot2.is_exhausted == False, "Sugar Lot 2 should be active!"
        assert s_lot2.remaining_quantity == 30.0, f"Expected Sugar Lot 2 remaining quantity 30, got {s_lot2.remaining_quantity}"
        
        assert f_lot1.is_exhausted == False, "Flour Lot 1 should be active!"
        assert f_lot1.remaining_quantity == 150.0, f"Expected Flour Lot 1 remaining quantity 150, got {f_lot1.remaining_quantity}"

        print("✓ Lots remaining quantities correctly updated.")
        print("✓ Lot exhaustion flags set correctly.")

        # 7. Verify Cost Calculation
        # Sugar: (100 * ₹50) + (20 * ₹60) = ₹6200
        # Flour: (50 * ₹30) = ₹1500
        # Total cost: ₹7700
        assert prod.total_raw_material_cost == 7700.0, f"Expected total raw material cost 7700.0, got {prod.total_raw_material_cost}"
        print(f"✓ Production total raw material cost calculated correctly: ₹{prod.total_raw_material_cost}")

        # Verify lot consumption audit trail
        sugar_consumptions = ProductionLotConsumption.query.join(ProductionMaterial).filter(ProductionMaterial.raw_material_id == sugar.id).all()
        assert len(sugar_consumptions) == 2, f"Expected 2 lot consumption records for Sugar, got {len(sugar_consumptions)}"
        print("✓ FIFO Audit Trail logged correctly:")
        for sc in sugar_consumptions:
            print(f" - Consumed {sc.quantity_taken} kg from Lot ID {sc.lot_id} (Batch: {sc.lot.batch_number}) at ₹{sc.price_per_unit}/kg. Line Cost: ₹{sc.cost}")

        # 8. Verify Validation Enforces Stock Constraints
        print("\nVerifying validation prevents consumption beyond total stock...")
        sugar = RawMaterial.query.filter_by(name="Sugar").first()
        requested_qty = 35.0  # Sugar remaining is only 30.0 kg
        
        try:
            # This should raise ValueError
            consume_fifo(sugar.id, requested_qty)
            raise Exception("FIFO validation failed to catch insufficient stock!")
        except ValueError as e:
            print(f"✓ Success: Validation caught insufficient stock. Error message: '{e}'")

        print("\n=== ALL FIFO LOTS TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
