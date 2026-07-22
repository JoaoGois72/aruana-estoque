from sqlalchemy import text


CODIGO = "002_ampliar_status_solicitacao"

DESCRICAO = (
    "Ampliar o campo status da solicitação "
    "para suportar estados parciais."
)


def executar(session, inspector):
    if not inspector.has_table("solicitacao"):
        raise RuntimeError(
            "A tabela solicitacao não existe."
        )

    session.execute(
        text(
            """
            ALTER TABLE solicitacao
            ALTER COLUMN status TYPE VARCHAR(30)
            """
        )
    )

    session.execute(
        text(
            """
            ALTER TABLE solicitacao
            ALTER COLUMN status
            SET DEFAULT 'PENDENTE'
            """
        )
    )

    session.execute(
        text(
            """
            UPDATE solicitacao
            SET status = 'PENDENTE'
            WHERE status IS NULL
               OR TRIM(status) = ''
            """
        )
    )
