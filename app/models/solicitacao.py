from datetime import datetime
from app.extensions import db


class Solicitacao(db.Model):
    __tablename__ = "solicitacao"

    id = db.Column(db.Integer, primary_key=True)

    # 🔥 USUÁRIO QUE SOLICITOU
    usuario_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    usuario = db.relationship("User", foreign_keys=[usuario_id])

    # 🔥 QUEM APROVOU
    aprovado_por_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    aprovado_por = db.relationship("User", foreign_keys=[aprovado_por_id])

    # 🔥 QUEM ENTREGOU
    entregue_por_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    entregue_por = db.relationship("User", foreign_keys=[entregue_por_id])

    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao = db.Column(db.DateTime)
    data_entrega = db.Column(db.DateTime)

    status = db.Column(db.String(20), default="PENDENTE", nullable=False)

    observacao = db.Column(db.Text)

    local_torre = db.Column(db.String(20))
    local_pav = db.Column(db.String(20))
    local_apto = db.Column(db.String(20))

    itens = db.relationship(
        "SolicitacaoItem",
        back_populates="solicitacao",
        cascade="all, delete-orphan"
    )