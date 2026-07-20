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

            # Ajusta os itens antigos conforme o status da solicitação.
            db.session.execute(
                text(
                    """
                    UPDATE solicitacao_item AS item
                    SET
                        status = CASE
                            WHEN solicitacao.status = 'APROVADA'
                                THEN 'APROVADO'
                            WHEN solicitacao.status = 'ENTREGUE'
                                THEN 'ENTREGUE'
                            WHEN solicitacao.status = 'REJEITADA'
                                THEN 'REJEITADO'
                            ELSE 'PENDENTE'
                        END,

                        qtd_aprovada = CASE
                            WHEN solicitacao.status IN (
                                'APROVADA',
                                'ENTREGUE'
                            )
                                THEN item.qtd
                            WHEN solicitacao.status = 'REJEITADA'
                                THEN 0
                            ELSE NULL
                        END

                    FROM solicitacao

                    WHERE solicitacao.id = item.solicitacao_id
                    """
                )
            )

            db.session.commit()

            print("========================================")
            print("BANCO ATUALIZADO COM SUCESSO")
            print("Colunas da solicitacao_item criadas.")
            print("Itens antigos ajustados.")
            print("========================================")

        except Exception as erro:
            db.session.rollback()

            print("========================================")
            print("ERRO AO ATUALIZAR O BANCO")
            print(str(erro))
            print("========================================")

            raise


if __name__ == "__main__":
    executar()
