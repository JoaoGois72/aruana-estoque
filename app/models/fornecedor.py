from app.extensions import db

class Fornecedor(db.Model):
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    documento = db.Column(db.String(20), unique=True, nullable=False)  # CNPJ/CPF
    nome = db.Column(db.String(200), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Fornecedor {self.documento} {self.nome}>"
