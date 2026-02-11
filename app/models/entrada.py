from datetime import datetime
from app.extensions import db

class Entrada(db.Model):
    __tablename__ = "entradas"

    id = db.Column(db.Integer, primary_key=True)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="RASCUNHO")  # RASCUNHO | CONCLUIDA

    numero_nf = db.Column(db.String(30))
    documento_fornecedor = db.Column(db.String(20))
    nome_fornecedor = db.Column(db.String(200))

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    registrado_por = db.relationship("User")

    itens = db.relationship("EntradaItem", back_populates="entrada", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Entrada {self.id} {self.status}>"

class EntradaItem(db.Model):
    __tablename__ = "entrada_itens"

    id = db.Column(db.Integer, primary_key=True)
    entrada_id = db.Column(db.Integer, db.ForeignKey("entradas.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    qtd = db.Column(db.Numeric(12, 2), nullable=False)

    entrada = db.relationship("Entrada", back_populates="itens")
    material = db.relationship("Material", back_populates="entrada_itens")

    def __repr__(self):
        return f"<EntradaItem {self.id}>"
