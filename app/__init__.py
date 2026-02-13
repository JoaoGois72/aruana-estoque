from flask import Flask, redirect, url_for
from .extensions import db, login_manager
from .models.user import User
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db_url = os.getenv("DATABASE_URL")

    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///aruana.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.estoque import estoque_bp
    from app.blueprints.admin import admin_bp   # ← IMPORTAR AQUI
    from app.blueprints.relatorios import relatorios_bp # ← IMPORTAR AQUI
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(admin_bp)            # ← REGISTRAR AQUI
    app.register_blueprint(relatorios_bp)
    
    with app.app_context():
        db.create_all()
    
    @app.get("/")
    def index():
        return redirect(url_for("estoque.dashboard"))

    # cria tabelas + admin padrão
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    from app.models.user import User
    from app.extensions import db

    admin = User.query.filter_by(login="admin").first()
    if not admin:
        u = User(nome="Administrador", login="admin", role="ADMIN", ativo=True)
        u.set_password("123")
        db.session.add(u)
        db.session.commit()

