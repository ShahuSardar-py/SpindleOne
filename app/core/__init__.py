from flask import Flask
from app.config import Config
from app.extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)

    # register core routes
    from app.core.routes import core_bp
    app.register_blueprint(core_bp)

    # register HR module
    from SpindlePeople import spindlepeople_bp
    app.register_blueprint(spindlepeople_bp)

    with app.app_context():
        db.create_all()

    return app
