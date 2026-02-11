from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, default="Usuário")
    login = db.Column(db.String(80), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="ENCARREGADO")
    departamento_id = db.Column(db.Integer, db.ForeignKey("departamentos.id"))
    ativo = db.Column(db.Boolean, default=True)

    departamento = db.relationship("Departamento")

    def set_password(self, senha: str):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<User {self.login} ({self.role})>"
