from datetime import datetime

from app.extensions import db


class Solicitacao(db.Model):
    __tablename__ = "solicitacao"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Usuário que criou a solicitação
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    usuario = db.relationship(
        "User",
        foreign_keys=[usuario_id]
    )

    # Usuário que realizou a aprovação/análise geral
    aprovado_por_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True,
        index=True
    )

    aprovado_por = db.relationship(
        "User",
        foreign_keys=[aprovado_por_id]
    )

    # Usuário que realizou a entrega
    entregue_por_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True,
        index=True
    )

    entregue_por = db.relationship(
        "User",
        foreign_keys=[entregue_por_id]
    )

    data_solicitacao = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    data_aprovacao = db.Column(
        db.DateTime,
        nullable=True
    )

    data_entrega = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDENTE",
        server_default="PENDENTE",
        index=True
    )

    observacao = db.Column(
        db.Text,
        nullable=True
    )

    local_torre = db.Column(
        db.String(20),
        nullable=True
    )

    local_pav = db.Column(
        db.String(20),
        nullable=True
    )

    local_apto = db.Column(
        db.String(20),
        nullable=True
    )

    itens = db.relationship(
        "SolicitacaoItem",
        back_populates="solicitacao",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    historico = db.relationship(
        "SolicitacaoHistorico",
        back_populates="solicitacao",
        cascade="all, delete-orphan",
        order_by="SolicitacaoHistorico.data_evento.asc()",
        lazy="selectin",
    )
    @property
    def pode_ser_analisada(self):
        return self.status in {
            "PENDENTE",
            "ANALISE_PARCIAL",
            "APROVADA_PARCIAL"
        }

    @property
    def pode_ser_entregue(self):
        return self.status in {
            "APROVADA",
            "APROVADA_PARCIAL",
            "ENTREGUE_PARCIAL"
        }

    @property
    def finalizada(self):
        return self.status in {
            "ENTREGUE",
            "REJEITADA",
            "CANCELADA"
        }

    def __repr__(self):
        return (
            f"<Solicitacao id={self.id} "
            f"status={self.status} "
            f"usuario_id={self.usuario_id}>"
        )
 
