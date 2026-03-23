from flask import Flask
from app.config import Config
from app.extensions import init_extensions, db
import os 
# import all model modules so SQLAlchemy metadata is populated
from .auth import models as auth_models
# finance, stock and people models will be imported later inside create_app when
# the modules are accessed (or you can import them here if you prefer).


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_extensions(app)

    # register blueprints after initializing extensions
    # Core home
    from app.core import routes as core_routes
    app.register_blueprint(core_routes.bp)
    from .auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp)
    # HR
    from SpindlePeople import routes as spindlepeople_routes
    # ensure people models are imported so they are registered
    from SpindlePeople import models as spindlepeople_models
    app.register_blueprint(spindlepeople_routes.bp)

    # Finance
    from SpindleFinance import bp as spindlefinance_bp
    from SpindleFinance import models as spindlefinance_models
    app.register_blueprint(spindlefinance_bp)

    # Stock
    from SpindleStock import routes as spindlestock_routes
    from SpindleStock import models as spindlestock_models
    app.register_blueprint(spindlestock_routes.bp)

    # Mech
    from SpindleMech import routes as spindlemech_routes
    from SpindleMech import models as spindlemech_models
    app.register_blueprint(spindlemech_routes.bp)

    app.config["SECRET_KEY"] = "spindle-secret"

    # create all tables if they do not yet exist; safe to call on every startup
    with app.app_context():
        db.create_all()

    # add a convenience flask command; this registration has to happen after
    # the app object exists
    from flask.cli import with_appcontext

    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Create database tables defined in all models."""
        db.create_all()
        print("Database tables created (or already existed).")

    return app

 