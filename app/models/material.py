from app.extensions import db

class Material(db.Model):
    __tablename__ = "material"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(20), unique=True, nullable=False)

    nome = db.Column(db.String(120), nullable=False)  # 🔥 padrão único
    unidade = db.Column(db.String(10), nullable=False)

    estoque_minimo = db.Column(db.Numeric(10, 2), default=0)
    saldo_atual = db.Column(db.Numeric(10, 2), default=0)

    ativo = db.Column(db.Boolean, default=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria.id"))
    categoria = db.relationship("Categoria", back_populates="materiais")