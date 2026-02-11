from app.extensions import db

class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)
    descricao = db.Column(db.String(200), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)

    estoque_minimo = db.Column(db.Numeric(12, 2), default=0)
    saldo_atual = db.Column(db.Numeric(12, 2), default=0)
    reservado_atual = db.Column(db.Numeric(12, 2), default=0)

    ativo = db.Column(db.Boolean, default=True)

    solicitacao_itens = db.relationship("SolicitacaoItem", back_populates="material", cascade="all, delete-orphan")
    entrada_itens = db.relationship("EntradaItem", back_populates="material", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Material {self.descricao}>"
