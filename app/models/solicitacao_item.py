from app.extensions import db


class SolicitacaoItem(db.Model):
    __tablename__ = "solicitacao_item"

    id = db.Column(db.Integer, primary_key=True)

    solicitacao_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitacao.id"),
        nullable=False
    )

    material_id = db.Column(
        db.Integer,
        db.ForeignKey("material.id"),
        nullable=False
    )

    qtd = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    solicitacao = db.relationship("Solicitacao", back_populates="itens")
    material = db.relationship("Material")
