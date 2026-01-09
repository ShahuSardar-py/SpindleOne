from flask import Flask
from app.config import Config
from app.extensions import *

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    init_extensions(app)
    
    from app.core import routes
    app.register_blueprint(routes.bp)
    
    return app
