from app.extensions import db


class SolicitacaoItem(db.Model):
    __tablename__ = "solicitacao_item"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    solicitacao_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitacao.id"),
        nullable=False,
        index=True
    )

    material_id = db.Column(
        db.Integer,
        db.ForeignKey("material.id"),
        nullable=False,
        index=True
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
        server_default="PENDENTE",
        index=True
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
        nullable=True,
        index=True
    )

    data_analise = db.Column(
        db.DateTime,
        nullable=True
    )

    solicitacao = db.relationship(
        "Solicitacao",
        back_populates="itens"
    )

    material = db.relationship(
        "Material"
    )

    analisado_por = db.relationship(
        "User",
        foreign_keys=[analisado_por_id]
    )

    @property
    def quantidade_para_entrega(self):
        if self.qtd_aprovada is not None:
            return self.qtd_aprovada

        return self.qtd

    @property
    def pendente(self):
        return self.status == "PENDENTE"

    @property
    def aprovado(self):
        return self.status == "APROVADO"

    @property
    def rejeitado(self):
        return self.status == "REJEITADO"

    @property
    def entregue(self):
        return self.status == "ENTREGUE"

    def __repr__(self):
        return (
            f"<SolicitacaoItem id={self.id} "
            f"solicitacao_id={self.solicitacao_id} "
            f"material_id={self.material_id} "
            f"status={self.status}>"
        )
