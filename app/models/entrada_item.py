from app.extensions import db

class EntradaItem(db.Model):
    __tablename__ = "entrada_item"

    id = db.Column(db.Integer, primary_key=True)

    entrada_id = db.Column(
        db.Integer,
        db.ForeignKey("entrada.id"),
        nullable=False
    )

    material_id = db.Column(
        db.Integer,
        db.ForeignKey("material.id"),
        nullable=False
    )

    qtd = db.Column(db.Numeric(10, 2), nullable=False)

    # ✅ CORRETO
    entrada = db.relationship("Entrada", back_populates="itens")

    # pode manter esse
    material = db.relationship("Material", backref="entradas")