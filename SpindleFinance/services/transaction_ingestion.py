import pandas as pd
from ..models import AccountCashflow
from app.extensions import db


def get_balance():
    latest = AccountCashflow.query.order_by(
        AccountCashflow.txn_date.desc(),
        AccountCashflow.id.desc()
    ).first()

    return latest.current_balance if latest else 0.00


def ingest_data(file_path):
    df = pd.read_csv(file_path)

    # Column renaming
    rename_map = {
        "date": "txn_date",
        "transaction name": "txn_name",
        "bank account name": "account_name",
        "transaction amount": "amount",
        "inflow or outflow": "txn_type",
        "refrence ID": "reference_id",
        # optional if exists in CSV
        "description": "description",
    }

    df = df.rename(columns=rename_map)

    # Required columns validation
    required = [
        "txn_date", "txn_name", "account_name",
        "amount", "txn_type"
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    # Data cleaning
    df["txn_date"] = pd.to_datetime(df["txn_date"], errors="coerce").dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Normalize txn_type properly
    df["txn_type"] = df["txn_type"].str.strip().str.upper()
    df = df[df["txn_type"].isin(["INFLOW", "OUTFLOW"])]

    # Optional fields handling
    if "description" not in df.columns:
        df["description"] = None

    df["invoice_id"] = None  # since not coming from CSV
    df["source"] = "File_Upload"

    # Drop bad rows
    df = df.dropna(subset=["txn_date", "amount", "txn_type"])

    # Running balance calculation - start from 0 for first import (avoid recursion)
    running_bal = 0.0
    balances = []

    for _, row in df.iterrows():
        if row["txn_type"] == "INFLOW":
            running_bal += row["amount"]
        else:
            running_bal -= row["amount"]
        balances.append(running_bal)

    df["current_balance"] = balances

    # Convert to ORM objects
    objects = [
        AccountCashflow(**row)
        for row in df.to_dict(orient="records")
    ]

    db.session.bulk_save_objects(objects)
    db.session.commit()

    return len(objects)