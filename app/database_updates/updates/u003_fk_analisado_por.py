from sqlalchemy import text


CODIGO = "003_fk_analisado_por"

DESCRICAO = (
    "Adicionar chave estrangeira do usuário "
    "que analisou o item da solicitação."
)


def executar(session, inspector):
    if not inspector.has_table("solicitacao_item"):
        raise RuntimeError(
            "A tabela solicitacao_item não existe."
        )

    if not inspector.has_table("user"):
        raise RuntimeError(
            "A tabela user não existe."
        )

    constraints = inspector.get_foreign_keys(
        "solicitacao_item"
    )

    nomes = {
        constraint.get("name")
        for constraint in constraints
        if constraint.get("name")
    }

    nome_constraint = (
        "fk_solicitacao_item_analisado_por"
    )

    if nome_constraint not in nomes:
        session.execute(
            text(
                f"""
                ALTER TABLE solicitacao_item
                ADD CONSTRAINT {nome_constraint}
                FOREIGN KEY (analisado_por_id)
                REFERENCES "user" (id)
                ON DELETE SET NULL
                """
            )
        )
