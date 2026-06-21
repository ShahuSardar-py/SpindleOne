import os
import sys
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add project root to path so we can import app modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

def migrate():
    sqlite_uri = "sqlite:///instance/spindleone.db"
    postgres_uri = os.environ.get("DATABASE_URL")
    
    if not postgres_uri or "[YOUR-PASSWORD]" in postgres_uri:
        print("Error: Please configure a valid DATABASE_URL in your .env file.")
        print("It should look like: postgresql://postgres:[password]@db.vgsrleyjcvsulfhndivo.supabase.co:6543/postgres?sslmode=require")
        return

    print("Connecting to source (SQLite) and target (Supabase PostgreSQL)...")
    try:
        sqlite_engine = create_engine(sqlite_uri)
        postgres_engine = create_engine(postgres_uri)
    except Exception as e:
        print(f"Error creating database engines: {e}")
        return

    sqlite_metadata = MetaData()
    sqlite_metadata.reflect(bind=sqlite_engine)
    
    # Define migration order to prevent foreign key violations
    migration_order = [
        # Level 0 (no foreign keys)
        "user",
        "clients",
        "raw_material",
        "production",
        "finished_stock",
        "recipe",
        "machines",
        "employees",
        # Level 1 (depends on Level 0)
        "module_acess",
        "Invoice",
        "raw_material_lot",
        "recipe_material",
        "maintenance_records",
        "attendance",
        # Level 2 (depends on Level 1)
        "AccountCashflow",
        "production_material",
        # Level 3 (depends on Level 2)
        "production_lot_consumption"
    ]

    # Verify that all tables in migration_order exist in SQLite
    missing_tables = [t for t in migration_order if t not in sqlite_metadata.tables]
    if missing_tables:
        print(f"Warning: The following tables were not found in SQLite: {missing_tables}")

    print("\nStarting migration...")
    
    with postgres_engine.connect() as pg_conn:
        # Disable foreign key check triggers for Postgres session to make migration easier
        # and avoid potential ordering issues during insertion.
        try:
            pg_conn.execute(text("SET session_replication_role = 'replica';"))
            print("Successfully set session_replication_role to 'replica' (temporarily disabled FK triggers).")
        except Exception as e:
            print(f"Could not disable constraint triggers (may need superuser): {e}")
            print("Continuing without disabling constraints. Insertion order will matter.")

        for table_name in migration_order:
            if table_name not in sqlite_metadata.tables:
                continue
                
            print(f"\nMigrating table: '{table_name}'...")
            
            # Read from SQLite
            sqlite_table = Table(table_name, sqlite_metadata, autoload_with=sqlite_engine)
            with sqlite_engine.connect() as lite_conn:
                rows = lite_conn.execute(select(sqlite_table)).fetchall()
            
            if not rows:
                print(f"-> Table '{table_name}' is empty in SQLite. Skipping data copy.")
                continue
            
            print(f"-> Found {len(rows)} records in SQLite.")
            
            # Delete existing records in Postgres (clean slate)
            try:
                pg_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
                print(f"-> Truncated target table '{table_name}'.")
            except Exception as e:
                # If truncate cascade fails or table doesn't exist, try DELETE
                try:
                    pg_conn.execute(text(f'DELETE FROM "{table_name}";'))
                    print(f"-> Cleared target table '{table_name}' using DELETE.")
                except Exception as ex:
                    print(f"-> Error clearing target table '{table_name}': {ex}")
            
            # Insert into Postgres
            postgres_metadata = MetaData()
            try:
                postgres_table = Table(table_name, postgres_metadata, autoload_with=postgres_engine)
            except Exception as e:
                print(f"-> Error: Table '{table_name}' does not exist on Supabase. Have you run the Flask app to initialize the database schema? Error: {e}")
                continue
            
            # Convert row objects to dicts matching columns
            insert_data = []
            for r in rows:
                # SQLAlchemy Row objects can be converted to dicts
                row_dict = dict(r._mapping)
                insert_data.append(row_dict)
                
            try:
                # Chunked insert for safety
                chunk_size = 500
                for i in range(0, len(insert_data), chunk_size):
                    chunk = insert_data[i:i+chunk_size]
                    pg_conn.execute(postgres_table.insert(), chunk)
                print(f"-> Successfully inserted {len(insert_data)} rows into '{table_name}'.")
            except Exception as e:
                print(f"-> Error inserting rows into '{table_name}': {e}")
                pg_conn.rollback()
                continue
                
            # Reset postgres primary key sequence to prevent PK collision on next inserts
            # Define custom PK column mappings
            pk_col = "id"
            if table_name == "user":
                pk_col = "user_id"
            elif table_name == "Invoice":
                pk_col = "inv_id"
                
            try:
                # Dynamic query to get sequence name and set it to max(id)
                seq_query = f"""
                SELECT pg_get_serial_sequence('"{table_name}"', '{pk_col}');
                """
                seq_result = pg_conn.execute(text(seq_query)).scalar()
                
                if seq_result:
                    reset_query = f"""
                    SELECT setval('{seq_result}', COALESCE((SELECT MAX("{pk_col}") FROM "{table_name}"), 1));
                    """
                    pg_conn.execute(text(reset_query))
                    print(f"-> Reset sequence '{seq_result}' to max ID.")
                else:
                    # Try manual fallback sequence name
                    fallback_seq = f"{table_name}_{pk_col}_seq"
                    reset_query = f"""
                    SELECT setval('"{fallback_seq}"', COALESCE((SELECT MAX("{pk_col}") FROM "{table_name}"), 1));
                    """
                    pg_conn.execute(text(reset_query))
                    print(f"-> Reset fallback sequence '{fallback_seq}' to max ID.")
            except Exception as e:
                print(f"-> Note: Sequence reset skipped/failed for '{table_name}': {e}")

        # Restore replication role to default
        try:
            pg_conn.execute(text("SET session_replication_role = 'origin';"))
            print("\nRestored session_replication_role to 'origin'.")
        except Exception as e:
            pass
            
        # Commit all pg changes
        pg_conn.commit()

    print("\nDatabase migration completed successfully!")

if __name__ == "__main__":
    migrate()
