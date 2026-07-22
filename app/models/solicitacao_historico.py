from datetime import datetime

from app.extensions import db


class SolicitacaoHistorico(db.Model):
    __tablename__ = "solicitacao_historico"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    solicitacao_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitacao.id"),
        nullable=False,
        index=True,
    )

    item_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitacao_item.id"),
        nullable=True,
        index=True,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True,
        index=True,
    )

    acao = db.Column(
        db.String(40),
        nullable=False,
        index=True,
    )

    descricao = db.Column(
        db.Text,
        nullable=False,
    )

    data_evento = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    solicitacao = db.relationship(
        "Solicitacao",
        back_populates="historico",
    )

    item = db.relationship(
        "SolicitacaoItem",
        foreign_keys=[item_id],
    )

    usuario = db.relationship(
        "User",
        foreign_keys=[usuario_id],
    )

    def __repr__(self):
        return (
            f"<SolicitacaoHistorico id={self.id} "
            f"solicitacao_id={self.solicitacao_id} "
            f"acao={self.acao}>"
        )
