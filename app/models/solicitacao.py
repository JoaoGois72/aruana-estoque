from datetime import datetime
from app.extensions import db

class Solicitacao(db.Model):
    __tablename__ = "solicitacoes"

    id = db.Column(db.Integer, primary_key=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="PENDENTE")  # PENDENTE | APROVADA | ENTREGUE | REJEITADA
    
    solicitante_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey("departamentos.id"), nullable=True)

    obs = db.Column(db.Text)
    
    ativo = db.Column(db.Boolean, default=True)

    local_torre = db.Column(db.String(10))
    local_pav = db.Column(db.String(20))
    local_apto = db.Column(db.String(10))
    local_txt = db.Column(db.String(120))

    aprovado_por = db.Column(db.Integer)
    data_aprovacao = db.Column(db.DateTime)

    entregue_por = db.Column(db.Integer)
    data_entrega = db.Column(db.DateTime)

    solicitante = db.relationship("User")
    departamento = db.relationship("Departamento")

    itens = db.relationship("SolicitacaoItem", back_populates="solicitacao", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Solicitacao {self.id} {self.status}>"
