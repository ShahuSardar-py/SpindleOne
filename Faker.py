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
        ["inflow", "outflow"],
        weights=[0.25, 0.75]
    )[0]

    # slightly realistic amount ranges
    if txn_type == "inflow":
        amount = round(random.uniform(25000, 350000), 2)
    else:
        amount = round(random.uniform(2000, 180000), 2)

    records.append({
        "txn_date": fake.date_between(start_date="-10M", end_date="today"),
        "txn_name": random.choice(txn_names),
        "account_name": random.choice(account_names),
        "amount": amount,
        "txn_type": txn_type,
        "description": random.choice(descriptions),
        "reference_id": "TXN-" + uuid.uuid4().hex[:18].upper()
    })

df = pd.DataFrame(records)

print(df.head())

df.to_csv("DevTestingData.csv", index=False)
