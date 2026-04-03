import random
import uuid
from faker import Faker
import pandas as pd
from datetime import datetime, timedelta

fake = Faker()

N = 1000

# Specific invoices to include
specific_invoices = [
    {
        "number": 1,
        "vendor": "Horizon Retail Group",
        "description": "DIWALI GIFT BOX",
        "amount": 50000.00,
        "due_date": "2026-04-30",
        "paid": True
    },
    {
        "number": 2,
        "vendor": "Clearpath Logistics",
        "description": "Banana chips",
        "amount": 25000.00,
        "due_date": "2026-04-15",
        "paid": True
    },
    {
        "number": 3,
        "vendor": "Atlas Components",
        "description": "Company Party",
        "amount": 40000.00,
        "due_date": "2026-04-30",
        "paid": True
    },
    {
        "number": 4,
        "vendor": "Blueforge Solutions Pvt. Ltd.",
        "description": "Fryums",
        "amount": 100000.00,
        "due_date": "2026-05-31",
        "paid": False
    },
    {
        "number": 5,
        "vendor": "Evermint Industries",
        "description": "DIWALI GIFT BOX",
        "amount": 65002.00,
        "due_date": "2026-03-31",
        "paid": True
    },
    {
        "number": 6,
        "vendor": "Northline Trading Co.",
        "description": "Banana chips",
        "amount": 45038.00,
        "due_date": "2026-04-21",
        "paid": False
    },
    {
        "number": 7,
        "vendor": "Horizon Retail Group",
        "description": "Banana chips",
        "amount": 98291.00,
        "due_date": "2026-04-30",
        "paid": True
    }
]

txn_names = [
    "Wheat Flour Purchase",
    "Sugar Procurement",
    "Milk Powder Supply",
    "Edible Oil Purchase",
    "Spices Raw Material",
    "Packaging Film Purchase",
    "Cold Storage Electricity",
    "Refrigeration Maintenance",
    "Factory Sanitation Charges",
    "Quality Inspection Fees",
    "Factory Worker Payroll",
    "Packaging Staff Payroll",
    "Distributor Payment",
    "Retail Chain Settlement",
    "Bulk Order Receipt",
    "Hotel Supply Payment"
]

account_names = [
    "HDFC – Operations Account",
    "ICICI – Procurement Account",
    "SBI – Payroll Account",
    "Axis – Sales Collection Account",
    "Kotak – Vendor Payments Account"
]

descriptions = [
    "Monthly supplier settlement",
    "Urgent procurement for production run",
    "Routine operational expense",
    "Bulk order payment received",
    "Invoice settlement",
    "Contractual service charges",
    "Cold chain logistics charges",
    "Packaging material replenishment",
    "Temporary labour payment",
    "Scheduled maintenance activity"
]

records = []

# Add specific invoice records and payments first
for inv in specific_invoices:
    due_date = datetime.strptime(inv["due_date"], "%Y-%m-%d").date()
    
    # Invoice record (INFLOW)
    inv_record = {
        "txn_date": due_date,
        "txn_name": f"Invoice #{inv['number']} - {inv['vendor']}",
        "account_name": random.choice(account_names),
        "amount": inv["amount"],
        "txn_type": "INFLOW",
        "description": f"Invoice from {inv['vendor']} for {inv['description']}",
        "reference_id": f"INV-{inv['number']:03d}-{uuid.uuid4().hex[:10].upper()}",
        "invoice_id": f"INV-{inv['number']:03d}",
        "source": "Specific_Invoices"
    }
    records.append(inv_record)
    
    # Payment transaction if paid (OUTFLOW, random date before due date)
    if inv["paid"]:
        days_before = random.randint(1, 30)
        payment_date = due_date - timedelta(days=days_before)
        payment_record = {
            "txn_date": payment_date,
            "txn_name": f"Payment for Invoice #{inv['number']}",
            "account_name": random.choice(account_names),
            "amount": inv["amount"],
            "txn_type": "OUTFLOW",
            "description": f"Payment to {inv['vendor']} - Invoice #{inv['number']}",
            "reference_id": f"PAY-{inv['number']:03d}-{uuid.uuid4().hex[:10].upper()}",
            "invoice_id": f"INV-{inv['number']:03d}",
            "source": "Specific_Invoices"
        }
        records.append(payment_record)

for _ in range(N):

    txn_type = random.choices(
["INFLOW", "OUTFLOW"],
        weights=[0.65, 0.35]  # Increased inflow probability for net positive cash flow
    )[0]

    # realistic amount ranges
    if txn_type == "INFLOW":
        amount = round(random.uniform(30000, 400000), 2)  # Slightly higher inflow range
    else:
        amount = round(random.uniform(1500, 150000), 2)  # Slightly lower outflow range

    records.append({
        "txn_date": fake.date_between(start_date="-10M", end_date="today"),
        "txn_name": random.choice(txn_names),
        "account_name": random.choice(account_names),
        "amount": amount,
        "txn_type": txn_type,
        "description": random.choice(descriptions),
        "reference_id": "TXN-" + uuid.uuid4().hex[:18].upper(),
        
        # NEW FIELDS (aligned with model)
        "invoice_id": None,
        "source": "Faker_Test_Data"
    })

df = pd.DataFrame(records)

# IMPORTANT: sort for realistic balance calculation later
df = df.sort_values(by=["txn_date"])

print(df.head())

df.to_csv("DevTestingData.csv", index=False)