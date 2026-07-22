from sqlalchemy import text


CODIGO = "004_historico_solicitacoes"

DESCRICAO = (
    "Criar tabela de histórico e auditoria "
    "das solicitações de materiais."
)


def executar(session, inspector):
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS solicitacao_historico (
                id SERIAL PRIMARY KEY,

                solicitacao_id INTEGER NOT NULL,

                item_id INTEGER NULL,

                usuario_id INTEGER NULL,

                acao VARCHAR(40) NOT NULL,

                descricao TEXT NOT NULL,

                data_evento TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_historico_solicitacao
                    FOREIGN KEY (solicitacao_id)
                    REFERENCES solicitacao (id)
                    ON DELETE CASCADE,

                CONSTRAINT fk_historico_item
                    FOREIGN KEY (item_id)
                    REFERENCES solicitacao_item (id)
                    ON DELETE SET NULL,

                CONSTRAINT fk_historico_usuario
                    FOREIGN KEY (usuario_id)
                    REFERENCES "user" (id)
                    ON DELETE SET NULL
            )
            """
        )
    )

    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS
                ix_historico_solicitacao_id
            ON solicitacao_historico (solicitacao_id)
            """
        )
    )

    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS
                ix_historico_data_evento
            ON solicitacao_historico (data_evento)
            """
        )
    )

    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS
                ix_historico_usuario_id
            ON solicitacao_historico (usuario_id)
            """
        )
    )
