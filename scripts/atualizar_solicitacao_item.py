from sqlalchemy import text

from app import create_app
from app.extensions import db


app = create_app()


def executar():
    comandos = [
        """
        ALTER TABLE solicitacao_item
        ADD COLUMN IF NOT EXISTS status VARCHAR(20)
        NOT NULL DEFAULT 'PENDENTE'
        """,

        """
        ALTER TABLE solicitacao_item
        ADD COLUMN IF NOT EXISTS qtd_aprovada NUMERIC(12, 2)
        """,

        """
        ALTER TABLE solicitacao_item
        ADD COLUMN IF NOT EXISTS motivo_rejeicao TEXT
        """,

        """
        ALTER TABLE solicitacao_item
        ADD COLUMN IF NOT EXISTS analisado_por_id INTEGER
        """,

        """
        ALTER TABLE solicitacao_item
        ADD COLUMN IF NOT EXISTS data_analise TIMESTAMP
        """,
    ]

    with app.app_context():
        try:
            for comando in comandos:
                db.session.execute(text(comando))

            db.session.commit()

            print("Colunas criadas ou já existentes.")
            print("Atualização concluída com sucesso.")

        except Exception as erro:
            db.session.rollback()
            print(f"Erro ao atualizar o banco: {erro}")
            raise


if __name__ == "__main__":
    executar()
