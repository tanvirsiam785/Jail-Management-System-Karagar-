# app/__init__.py

import os
from flask import Flask
from flask_mysqldb import MySQL
from flask_cors import CORS
from .config import Config
from .routes.alerts import start_scheduler
from flask_moment import Moment  # <-- 1. IMPORT THIS

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    Moment(app)  # <-- 2. INITIALIZE IT HERE
    
    # Initialize CORS after the app is created
    CORS(app, supports_credentials=True)

    mysql.init_app(app)

    # ... rest of your file remains the same ...

 

    # Register blueprints AFTER initializing MySQL to prevent import issues
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.inmates import inmates_bp
    from .routes.visitors import visitors_bp
    from .routes.punishments import punishments_bp
    from .routes.transfers import transfers_bp
    from .routes.notifications import notifications_bp
    from .routes.cells import cells_bp
    from .routes.search import search_bp
    from .routes.visit_request import visit_request_bp
    from .routes.alerts import alerts_bp
    from .routes.work_assignments import work_assignments_bp
    from .routes.behavior import behavior_bp
    from .routes.ranking import ranking_bp
    app.register_blueprint(ranking_bp)
    app.register_blueprint(behavior_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmates_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(punishments_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(cells_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(visit_request_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(work_assignments_bp)

    # ✅ Only start scheduler once
    # Using a context to prevent it from running multiple times in debug mode
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler()

    return app
