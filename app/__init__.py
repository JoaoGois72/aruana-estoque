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
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///aruana.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret",
    )

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Carrega os modelos para registrar o metadata do SQLAlchemy.
    with app.app_context():
        from app.models import (
            User,
            Material,
            Categoria,
            Solicitacao,
            SolicitacaoItem,
            Entrada,
            EntradaItem,
            Departamento,
            Fornecedor,
        )

        # Pode permanecer temporariamente.
        # Não substitui o atualizador permanente do banco.
        db.create_all()

        _seed_admin()

    from app.blueprints.auth import auth_bp
    from app.blueprints.estoque import estoque_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.relatorios import relatorios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(relatorios_bp)

    @app.get("/")
    def index():
        return redirect(url_for("estoque.dashboard"))

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    return app


def _seed_admin():
    from app.models.user import User

    admin = User.query.filter_by(login="admin").first()

    if not admin:
        usuario = User(
            nome="Administrador",
            login="admin",
            role="ADMIN",
            ativo=True,
        )
        usuario.set_password("123")

        db.session.add(usuario)
        db.session.commit()

