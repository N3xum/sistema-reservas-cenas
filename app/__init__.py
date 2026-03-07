from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

# Inicializamos las extensiones sin vincularlas a la app todavía
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Vinculamos las extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configuración de Flask-Login para la autenticación
    login_manager.login_view = 'auth.login' # Esta ruta la crearemos luego
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

    with app.app_context():
        # Importamos los modelos para que Flask-Migrate los detecte
        from . import models
        
    # --- AÑADE ESTO AQUÍ ---
    from .models import Usuario

    # Función para que Flask-Login sepa quién es el usuario actual
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # Registramos tu módulo de usuarios
    from .modulo_usuario import usuario_bp
    app.register_blueprint(usuario_bp)
    # -----------------------
    

    return app