import random
import uuid
from faker import Faker
import pandas as pd

fake = Faker()

N = 1000

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
        "invoice_id": None,              # since no invoice table linkage here
        "source": "Faker_Test_Data"      # helps you track origin
    })

df = pd.DataFrame(records)

# IMPORTANT: sort for realistic balance calculation later
df = df.sort_values(by=["txn_date"])

print(df.head())

df.to_csv("DevTestingData.csv", index=False)