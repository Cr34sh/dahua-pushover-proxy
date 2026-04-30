import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from .models import db, User, Setting, EventTemplate

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'web.login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_change_me_in_prod')
    
    # Configure SQLite database inside the 'data' directory (which will be a Docker volume)
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(data_dir, 'campush.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        # Create default admin user if no users exist
        if not User.query.first():
            hashed_pw = bcrypt.generate_password_hash('admin').decode('utf-8')
            admin_user = User(username='admin', password_hash=hashed_pw)
            db.session.add(admin_user)
            db.session.commit()
            print("Usuario admin por defecto creado (admin/admin).")
            
        # Seed default events if they don't exist
        if not EventTemplate.query.first():
            default_events = [
                EventTemplate(event_id='movimiento', title='Movimiento', message='Detectado movimiento en la cámara {camera_name}'),
                EventTemplate(event_id='cruce', title='Cruce', message='Detectado cruce de linea en la cámara {camera_name}'),
                EventTemplate(event_id='cara', title='Reconocimiento Facial', message='Se ha detectado una cara en {camera_name}'),
                EventTemplate(event_id='matricula', title='Reconocimiento Matricula', message='Se ha detectado una matricula en {camera_name}'),
                EventTemplate(event_id='errorsd', title='Error en SD', message='La tarjeta SD en la {camera_name} tiene problemas'),
                EventTemplate(event_id='tampering', title='Manipulacion', message='Posible manipulacion en {camera_name}'),
                EventTemplate(event_id='espaciosd', title='Espacio en SD', message='Queda poco espacio en la tarjeta SD de {camera_name}'),
                EventTemplate(event_id='sinsd', title='Sin SD', message='No se detecta tarjeta SD en {camera_name}'),
                EventTemplate(event_id='alarma', title='Alarma', message='Se ha activado la alarma en {camera_name}'),
                EventTemplate(event_id='audio', title='Audio Detectado', message='Se ha detectado audio en {camera_name}')
            ]
            db.session.bulk_save_objects(default_events)
            db.session.commit()
            print("Eventos por defecto inicializados.")

    # Import and register blueprints
    from .routes_web import web_bp
    from .routes_api import api_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    return app
