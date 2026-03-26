from datetime import datetime
from app.extensions import db

class Entrada(db.Model):
    __tablename__ = "entrada"

    id = db.Column(db.Integer, primary_key=True)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="RASCUNHO")  # RASCUNHO | CONCLUIDA

    numero_nf = db.Column(db.String(30))
    documento_fornecedor = db.Column(db.String(20))
    nome_fornecedor = db.Column(db.String(200))

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    registrado_por = db.relationship("User")

    itens = db.relationship("EntradaItem", back_populates="entrada", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Entrada {self.id} {self.status}>"

