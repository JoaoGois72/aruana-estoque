from app.extensions import db

class Departamento(db.Model):
    __tablename__ = "departamentos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Departamento {self.nome}>"
