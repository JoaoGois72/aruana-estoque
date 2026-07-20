from datetime import datetime

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

    qtd = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PENDENTE",
        server_default="PENDENTE"
    )

    qtd_aprovada = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    motivo_rejeicao = db.Column(
        db.Text,
        nullable=True
    )

    analisado_por_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    data_analise = db.Column(
        db.DateTime,
        nullable=True
    )

    solicitacao = db.relationship(
        "Solicitacao",
        back_populates="itens"
    )

    material = db.relationship("Material")

    analisado_por = db.relationship(
        "User",
        foreign_keys=[analisado_por_id]
    )
