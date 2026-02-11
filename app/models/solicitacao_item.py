from app.extensions import db

class SolicitacaoItem(db.Model):
    __tablename__ = "solicitacao_itens"

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey("solicitacoes.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    qtd = db.Column(db.Numeric(12, 2), nullable=False)

    solicitacao = db.relationship("Solicitacao", back_populates="itens")
    material = db.relationship("Material", back_populates="solicitacao_itens")

    def __repr__(self):
        return f"<SolicitacaoItem {self.id}>"
