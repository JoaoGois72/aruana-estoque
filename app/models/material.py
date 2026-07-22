from decimal import Decimal

from app.extensions import db


class Material(db.Model):
    __tablename__ = "material"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    codigo = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True
    )

    nome = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    unidade = db.Column(
        db.String(10),
        nullable=False
    )

    estoque_minimo = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0"
    )

    saldo_atual = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0"
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("categoria.id"),
        nullable=True,
        index=True
    )

    categoria = db.relationship(
        "Categoria",
        back_populates="materiais"
    )

    @property
    def saldo_decimal(self):
        return Decimal(self.saldo_atual or 0)

    @property
    def estoque_minimo_decimal(self):
        return Decimal(self.estoque_minimo or 0)

    @property
    def estoque_critico(self):
        return (
            self.saldo_decimal
            <= self.estoque_minimo_decimal
        )

    def possui_saldo(self, quantidade):
        quantidade = Decimal(quantidade or 0)

        return self.saldo_decimal >= quantidade

    def baixar_estoque(self, quantidade):
        quantidade = Decimal(quantidade or 0)

        if quantidade <= 0:
            raise ValueError(
                "A quantidade para baixa deve ser maior que zero."
            )

        if not self.possui_saldo(quantidade):
            raise ValueError(
                f"Estoque insuficiente para {self.nome}."
            )

        self.saldo_atual = (
            self.saldo_decimal - quantidade
        )

    def adicionar_estoque(self, quantidade):
        quantidade = Decimal(quantidade or 0)

        if quantidade <= 0:
            raise ValueError(
                "A quantidade de entrada deve ser maior que zero."
            )

        self.saldo_atual = (
            self.saldo_decimal + quantidade
        )

    def __repr__(self):
        return (
            f"<Material id={self.id} "
            f"codigo={self.codigo} "
            f"nome={self.nome}>"
        )
