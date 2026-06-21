from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from supabase import create_client, Client

db = SQLAlchemy()
migrate = Migrate()
supabase: Client = None

def init_extensions(app):
    global supabase
    db.init_app(app)
    migrate.init_app(app, db)
    
    url = app.config.get("SUPABASE_URL")
    key = app.config.get("SUPABASE_KEY")
    if url and key:
        supabase = create_client(url, key)

