import os
import sys

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.auth.models import User

def test_dashboard():
    print("Initializing Flask test environment...")
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    
    with app.test_client() as client:
        with app.app_context():
            # Query an admin user to use for session authentication
            admin_user = User.query.filter_by(role="SuperAdmin").first()
            if not admin_user:
                print("Error: No admin user found in database. Seed the database first.")
                sys.exit(1)
            
            user_id = admin_user.user_id
            username = admin_user.username
            role = admin_user.role

        # Set session variables using session_transaction
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["role"] = role

        print("Sending GET request to SpindleStock dashboard /stock/ ...")
        response = client.get("/stock/")
        
        print(f"Response status code: {response.status_code}")
        if response.status_code != 200:
            print("FAILED: Stock dashboard did not load successfully.")
            sys.exit(1)
        
        html = response.data.decode("utf-8")
        
        # Check for new KPIs
        kpi_checks = [
            "Total Materials",
            "Stock Value",
            "Active Lots",
            "Low Stock Alerts",
            "Total Prod. Cost"
        ]
        
        print("\nVerifying New KPI Cards:")
        for check in kpi_checks:
            found = check in html
            print(f" - {check}: {'FOUND' if found else 'NOT FOUND'}")
            if not found:
                print(f"FAILED: KPI '{check}' not found in dashboard HTML.")
                sys.exit(1)
                
        # Check for new Tables/Headers
        table_checks = [
            "Recent Inward Purchases (Quantity & Rate)",
            "Recent Production Runs",
            "Inventory Valuation Breakdown"
        ]
        
        print("\nVerifying New Tables and Charts:")
        for check in table_checks:
            found = check in html
            print(f" - {check}: {'FOUND' if found else 'NOT FOUND'}")
            if not found:
                print(f"FAILED: Element '{check}' not found in dashboard HTML.")
                sys.exit(1)

        # Check for injected JSON data for Doughnut chart
        json_checks = [
            'id="valuation-data"',
            'id="product-data"'
        ]
        
        print("\nVerifying Chart JSON data scripts:")
        for check in json_checks:
            found = check in html
            print(f" - {check}: {'FOUND' if found else 'NOT FOUND'}")
            if not found:
                print(f"FAILED: Chart JSON data script tag '{check}' not found in dashboard HTML.")
                sys.exit(1)

        print("\n✓ SUCCESS: All tests passed! SpindleStock dashboard is fully enhanced and functional.")

if __name__ == "__main__":
    test_dashboard()
