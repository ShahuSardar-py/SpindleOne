import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.auth.routes import seed_demo_users

app = create_app()
with app.app_context():
    bind = db.engine
    print(f"Connected to dialect: {bind.dialect.name} for reset.")
    print("Dropping all existing database tables...")
    db.drop_all()
    print("Recreating all database tables...")
    db.create_all()
    print("Seeding default demo users...")
    seed_demo_users()
    print("Database reset successfully complete!")
