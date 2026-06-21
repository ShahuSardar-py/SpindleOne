import os
import sys

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app

def verify():
    app = create_app()
    with app.test_client() as client:
        print("Logging in as admin...")
        # Authenticate first
        login_response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'SuperAdmin'
        })
        assert login_response.status_code == 302, f"Expected 302 redirect on login, got {login_response.status_code}"
        
        print("Testing template download endpoint...")
        response = client.get('/finance/template/download')
        
        # Verify status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify mimetype
        assert "text/csv" in response.mimetype, f"Expected text/csv mimetype, got {response.mimetype}"
        
        # Verify headers
        disp = response.headers.get("Content-Disposition", "")
        assert "spindle_finance_template.csv" in disp, f"Expected spindle_finance_template.csv in Content-Disposition, got {disp}"
        
        # Verify content headers
        data = response.data.decode('utf-8')
        lines = data.strip().split('\n')
        headers = lines[0].strip().split(',')
        print(f"Parsed headers: {headers}")
        
        expected_headers = [
            'txn_date', 'amount', 'txn_type', 'txn_name', 'account_name', 
            'invoice_id', 'reference_id', 'description', 'sale_type'
        ]
        assert headers == expected_headers, f"Expected headers {expected_headers}, got {headers}"
        
        # Verify row content
        print(f"Sample row 1: {lines[1]}")
        assert "Corporate sales" in lines[1], "Row 1 should contain Corporate sales sample data"
        print(f"Sample row 3: {lines[3]}")
        assert "General Sale" in lines[3], "Row 3 should contain General Sale sample data"
        
        print("\nCSV TEMPLATE DOWNLOAD ENDPOINT VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()
