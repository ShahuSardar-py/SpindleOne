from flask import Flask
from app.config import Config
from app.extensions import db, init_extensions

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    init_extensions(app)
    
    # Register blueprints
    from app.core import routes as core_routes
    app.register_blueprint(core_routes.bp)
    
    from SpindlePeople import routes as spindlepeople_routes
    app.register_blueprint(spindlepeople_routes.bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

