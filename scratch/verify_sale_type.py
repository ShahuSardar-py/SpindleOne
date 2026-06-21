import os
import sys
from datetime import date

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from SpindleFinance.models import AccountCashflow
from SpindleFinance.services.dashboardCalc import get_dashboard_context
from SpindleFinance.CF01.metric_Store import get_metric_store, refresh_store

def verify():
    app = create_app()
    with app.app_context():
        print("Starting verification of Sale Type changes...")
        
        # 1. Clean up any existing test records if they exist to start fresh
        # Note: We won't touch other real records, but we will count them.
        orig_context = get_dashboard_context()
        orig_corporate = orig_context.get('corporate_sales', 0.0)
        orig_general = orig_context.get('general_sale', 0.0)
        print(f"Original totals - Corporate: ₹{orig_corporate}, General: ₹{orig_general}")

        # 2. Add test inflow transactions
        print("Inserting test inflow transactions...")
        corp_txn = AccountCashflow(
            txn_date=date(2026, 6, 21),
            amount=100000.0,
            txn_name="Test Corporate Deal",
            account_name="Business Checking",
            txn_type="INFLOW",
            description="Verification corp sale",
            current_balance=150000.0, # dummy
            source="MANUAL",
            sale_type="Corporate sales"
        )
        gen_txn = AccountCashflow(
            txn_date=date(2026, 6, 21),
            amount=50000.0,
            txn_name="Test General Deal",
            account_name="Business Checking",
            txn_type="INFLOW",
            description="Verification general sale",
            current_balance=200000.0, # dummy
            source="MANUAL",
            sale_type="General Sale"
        )

        db.session.add(corp_txn)
        db.session.add(gen_txn)
        db.session.commit()
        print("✓ Test transactions saved.")

        try:
            # 3. Verify dashboard calculations
            print("Calculating dashboard metrics...")
            context = get_dashboard_context()
            new_corporate = context.get('corporate_sales', 0.0)
            new_general = context.get('general_sale', 0.0)
            
            expected_corp = orig_corporate + 100000.0
            expected_gen = orig_general + 50000.0
            
            assert abs(new_corporate - expected_corp) < 0.01, f"Expected Corporate sales sum to be {expected_corp}, got {new_corporate}"
            assert abs(new_general - expected_gen) < 0.01, f"Expected General Sale sum to be {expected_gen}, got {new_general}"
            print(f"✓ Dashboard calculations verified. Corporate: ₹{new_corporate}, General: ₹{new_general}")

            # 4. Verify metric store for LLM chatbot
            print("Verifying chatbot metric store refresh...")
            store_json = refresh_store()
            import json
            store = json.loads(store_json)
            
            assert "sale_types" in store, "sale_types section not found in chatbot metric store"
            sale_types = store["sale_types"]
            assert abs(sale_types["corporate_sales"] - expected_corp) < 0.01
            assert abs(sale_types["general_sale"] - expected_gen) < 0.01
            print("✓ Chatbot metric store successfully updated and verified.")

        finally:
            # 5. Clean up test records
            print("Cleaning up test transactions...")
            db.session.delete(corp_txn)
            db.session.delete(gen_txn)
            db.session.commit()
            print("✓ Cleanup complete.")

        print("\nALL BACKEND VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()
