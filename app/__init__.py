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

    # Zarvec Admin
    from app.zarvec import bp as zarvec_bp
    app.register_blueprint(zarvec_bp)

    app.config["SECRET_KEY"] = "spindle-secret"

    @app.before_request
    def check_auth_and_permissions():
        from flask import request, session, g, redirect, url_for, abort, render_template
        from app.auth.models import User
        from app.zarvec.lock_manager import get_lock_state

        # Skip static assets
        if request.path.startswith('/static') or request.endpoint == 'static':
            return

        # Skip zarvec endpoints
        if request.blueprint == 'zarvec' or request.path.startswith('/zarvec'):
            return

        # Check system lockout status
        lock_state = get_lock_state()
        if lock_state.get('is_locked', False):
            # Allow access to static files and zarvec endpoints
            is_zarvec = request.path.startswith('/zarvec') or request.blueprint == 'zarvec'
            if not is_zarvec:
                return render_template('zarvec/suspended.html', reason=lock_state.get('lock_reason', '')), 503

        # Skip auth routes
        if request.blueprint == 'auth':
            return

        user_id = session.get('user_id')
        g.user = None
        if user_id:
            g.user = User.query.get(user_id)

        # If not logged in, redirect to login
        if g.user is None:
            return redirect(url_for('auth.login'))

        # Role-based access control per blueprint
        role_permissions = {
            'spindlepeople': ['SuperAdmin', 'HR'],
            'spindlefinance': ['SuperAdmin', 'accounts'],
            'spindlestock': ['SuperAdmin', 'store keeper'],
            'spindlemech': ['SuperAdmin', 'store keeper', 'accounts'],
        }

        current_bp = request.blueprint
        if current_bp in role_permissions:
            allowed = role_permissions[current_bp]
            if g.user.role not in allowed:
                abort(403)

    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403

    # create all tables if they do not yet exist; safe to call on every startup
    with app.app_context():
        db.create_all()
        # Seed default users
        from app.auth.routes import seed_demo_users
        seed_demo_users()

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

 