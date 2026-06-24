"""
SolarGuard AI — Flask Application Entry Point
Run: python app.py   (from inside SolarGuard_AI/)
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_login import LoginManager
from config import Config

login_manager = LoginManager()

def _get_alert_count():
    try:
        from db import query_db
        row = query_db("SELECT COUNT(*) AS cnt FROM alerts WHERE status='active'", one=True)
        return row['cnt'] if row else 0
    except Exception:
        return 0


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(Config)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    login_manager.init_app(app)
    login_manager.login_view             = 'auth.login'
    login_manager.login_message          = 'Please sign in to continue.'
    login_manager.login_message_category = 'warning'

    from routers.auth import auth_bp
    from routers.analyze import analyze_bp
    from routers.alerts import alerts_bp
    from routers.live_monitor import live_monitor_bp
    from routers.generate import generate_bp
    from routers.admin import admin_bp
    from routers.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(live_monitor_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']  = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from config import Config
        alert_count = 0
        if current_user.is_authenticated:
            alert_count = _get_alert_count()
        return dict(
            alert_count=alert_count,
            station_id=Config.get_station_config()['STATION_ID'],
            station_name=Config.get_station_config()['STATION_NAME'],
        )

    with app.app_context():
        try:
            from models import _load_cache
            _load_cache()
        except Exception as e:
            print(f'[app] user cache preload error: {e}')

    return app


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.get_by_id(int(user_id))


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
