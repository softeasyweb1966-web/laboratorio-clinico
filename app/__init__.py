import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def _resolve_database_uri():
    database_url = os.environ.get('LABCLINICO_DATABASE_URL')
    if not database_url:
        raise RuntimeError(
            'Debes definir LABCLINICO_DATABASE_URL con una conexion PostgreSQL '
            'nueva y exclusiva para este proyecto.'
        )

    normalized_url = database_url.strip()
    if normalized_url.startswith('postgres://'):
        normalized_url = normalized_url.replace('postgres://', 'postgresql://', 1)

    if not normalized_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
        raise RuntimeError(
            'LABCLINICO_DATABASE_URL debe apuntar a PostgreSQL. '
            'Ejemplo: postgresql+psycopg2://usuario:clave@127.0.0.1:5432/labclinico_integrado'
        )

    return normalized_url


def create_app():
    app = Flask(__name__)

    # Configuracion
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = _resolve_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesion para acceder.'
    login_manager.login_message_category = 'warning'

    # Registrar blueprints
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.pacientes import pacientes_bp
    app.register_blueprint(pacientes_bp, url_prefix='/pacientes')

    from app.clientes import clientes_bp
    app.register_blueprint(clientes_bp, url_prefix='/clientes')

    from app.cups import cups_bp
    app.register_blueprint(cups_bp, url_prefix='/cups')

    from app.atenciones import atenciones_bp
    app.register_blueprint(atenciones_bp, url_prefix='/atenciones')

    from app.cartera import cartera_bp
    app.register_blueprint(cartera_bp, url_prefix='/cartera')

    from app.rips import rips_bp
    app.register_blueprint(rips_bp, url_prefix='/rips')

    from app.informes import informes_bp
    app.register_blueprint(informes_bp, url_prefix='/informes')

    from app.listas_precios import listas_bp
    app.register_blueprint(listas_bp, url_prefix='/listas')

    from app.resultados.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.resultados.designer import designer_bp
    app.register_blueprint(designer_bp, url_prefix='/designer')

    from app.resultados.exams import exams_bp
    app.register_blueprint(exams_bp, url_prefix='/exams')

    from app.resultados.orders import orders_bp
    app.register_blueprint(orders_bp, url_prefix='/orders')

    from app.resultados.pdf_config import pdf_config_bp
    app.register_blueprint(pdf_config_bp, url_prefix='/pdf-config')

    from app.resultados.results import results_bp
    app.register_blueprint(results_bp, url_prefix='/results')

    # Context processor global
    from datetime import datetime as _dt

    @app.context_processor
    def inject_now():
        return {'now': _dt.utcnow()}

    return app
