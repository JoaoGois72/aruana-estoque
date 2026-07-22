import importlib
import pkgutil
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.extensions import db
from app.database_updates import updates


TABELA_CONTROLE = "database_update_history"


def criar_tabela_controle():
    """
    Cria a tabela que registra quais atualizações já foram executadas.
    Não apaga nem modifica tabelas existentes.
    """
    db.session.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {TABELA_CONTROLE} (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(100) NOT NULL UNIQUE,
                descricao VARCHAR(255),
                executado_em TIMESTAMP NOT NULL,
                sucesso BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
    )

    db.session.commit()


def atualizacao_ja_executada(codigo):
    resultado = db.session.execute(
        text(
            f"""
            SELECT 1
            FROM {TABELA_CONTROLE}
            WHERE codigo = :codigo
              AND sucesso = TRUE
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).scalar()

    return resultado is not None


def registrar_atualizacao(codigo, descricao):
    db.session.execute(
        text(
            f"""
            INSERT INTO {TABELA_CONTROLE}
                (codigo, descricao, executado_em, sucesso)
            VALUES
                (:codigo, :descricao, :executado_em, TRUE)
            ON CONFLICT (codigo)
            DO UPDATE SET
                descricao = EXCLUDED.descricao,
                executado_em = EXCLUDED.executado_em,
                sucesso = TRUE
            """
        ),
        {
            "codigo": codigo,
            "descricao": descricao,
            "executado_em": datetime.now(timezone.utc),
        },
    )


def carregar_atualizacoes():
    """
    Carrega automaticamente os arquivos existentes em:
    app/database_updates/updates/
    """
    modulos = []

    for modulo_info in pkgutil.iter_modules(updates.__path__):
        nome = modulo_info.name

        if nome.startswith("_"):
            continue

        modulo = importlib.import_module(
            f"app.database_updates.updates.{nome}"
        )

        if not hasattr(modulo, "CODIGO"):
            raise RuntimeError(
                f"A atualização {nome} não possui CODIGO."
            )

        if not hasattr(modulo, "DESCRICAO"):
            raise RuntimeError(
                f"A atualização {nome} não possui DESCRICAO."
            )

        if not hasattr(modulo, "executar"):
            raise RuntimeError(
                f"A atualização {nome} não possui executar()."
            )

        modulos.append(modulo)

    return sorted(
        modulos,
        key=lambda modulo: modulo.CODIGO,
    )


def executar_atualizacoes():
    criar_tabela_controle()

    atualizacoes = carregar_atualizacoes()

    if not atualizacoes:
        print("Nenhuma atualização de banco encontrada.")
        return

    for atualizacao in atualizacoes:
        codigo = atualizacao.CODIGO
        descricao = atualizacao.DESCRICAO

        if atualizacao_ja_executada(codigo):
            print(f"[IGNORADA] {codigo} - já executada.")
            continue

        print(f"[EXECUTANDO] {codigo} - {descricao}")

        try:
            atualizacao.executar(
                db.session,
                inspect(db.engine),
            )

            registrar_atualizacao(
                codigo,
                descricao,
            )

            db.session.commit()

            print(f"[CONCLUÍDA] {codigo}")

        except Exception:
            db.session.rollback()

            print(f"[FALHOU] {codigo}")
            raise
