from flask import Flask
from app.config import Config
from app.extensions import init_extensions

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_extensions(app)

    # Core home
    from app.core import routes as core_routes
    app.register_blueprint(core_routes.bp)

    # HR
    from SpindlePeople import routes as spindlepeople_routes
    app.register_blueprint(spindlepeople_routes.bp)

    # Finance
    from SpindleFinance import bp as spindlefinance_bp
    app.register_blueprint(spindlefinance_bp)

    return app
