import pandas as pd 
from ..models import AccountCashflow
from app.extensions import db
from ..routes import starting_balance 
def ingest_data(file_path):
    #loader 
    df= pd.read_csv(file_path)

    #columns renamig
    rename_map = {
    "date": "txn_date",
    "transaction name": "txn_name",
    "bank account name": "account_name",
    "transaction amount": "amount",
    "inflow or outflow": "txn_type",
    "refrence ID": "reference_id",
    }
    df= df.rename(columns= rename_map)

    #df = df.drop(columns=["categroy"])



    #column validation
    required = list(rename_map.values())
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")
    
    #data type validation and transoform
    df['txn_date'] = pd.to_datetime(df['txn_date'],errors='coerce').dt.date
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df["current_balance"] = starting_balance
    df["source"] = "File_Upload"

    df= df[df['txn_type'].isin(["inflow", "outflow"])]

    objects = [
        AccountCashflow(**row)
        for row in df.to_dict(orient="records")

    ]
    db.session.bulk_save_objects(objects)
    db.session.commit()

    return len(objects)