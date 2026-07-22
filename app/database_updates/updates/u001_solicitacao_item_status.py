from sqlalchemy import text


CODIGO = "001_solicitacao_item_status"

DESCRICAO = (
    "Adicionar controle de aprovação, rejeição e entrega "
    "individual aos itens da solicitação."
)


def executar(session, inspector):
    tabela = "solicitacao_item"

    if not inspector.has_table(tabela):
        raise RuntimeError(
            f"A tabela {tabela} não existe no banco."
        )

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns(tabela)
    }

    if "status" not in colunas:
        session.execute(
            text(
                """
                ALTER TABLE solicitacao_item
                ADD COLUMN status VARCHAR(20)
                NOT NULL DEFAULT 'PENDENTE'
                """
            )
        )

    if "qtd_aprovada" not in colunas:
        session.execute(
            text(
                """
                ALTER TABLE solicitacao_item
                ADD COLUMN qtd_aprovada NUMERIC(12, 2)
                """
            )
        )

    if "motivo_rejeicao" not in colunas:
        session.execute(
            text(
                """
                ALTER TABLE solicitacao_item
                ADD COLUMN motivo_rejeicao TEXT
                """
            )
        )

    if "analisado_por_id" not in colunas:
        session.execute(
            text(
                """
                ALTER TABLE solicitacao_item
                ADD COLUMN analisado_por_id INTEGER
                """
            )
        )

    if "data_analise" not in colunas:
        session.execute(
            text(
                """
                ALTER TABLE solicitacao_item
                ADD COLUMN data_analise TIMESTAMP
                """
            )
        )

    session.execute(
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

                    ELSE COALESCE(
                        NULLIF(item.status, ''),
                        'PENDENTE'
                    )
                END,

                qtd_aprovada = CASE
                    WHEN solicitacao.status IN (
                        'APROVADA',
                        'ENTREGUE'
                    )
                        THEN COALESCE(
                            item.qtd_aprovada,
                            item.qtd
                        )

                    WHEN solicitacao.status = 'REJEITADA'
                        THEN 0

                    ELSE item.qtd_aprovada
                END

            FROM solicitacao

            WHERE solicitacao.id = item.solicitacao_id
            """
        )
    )
