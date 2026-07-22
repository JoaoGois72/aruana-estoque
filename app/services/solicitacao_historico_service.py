from app.extensions import db
from app.models.solicitacao_historico import SolicitacaoHistorico


def registrar_evento(
    solicitacao,
    acao,
    descricao,
    usuario_id=None,
    item=None,
):
    if solicitacao is None:
        raise ValueError(
            "Solicitação não informada para o histórico."
        )

    if not acao:
        raise ValueError(
            "Ação não informada para o histórico."
        )

    if not descricao:
        raise ValueError(
            "Descrição não informada para o histórico."
        )

    if solicitacao.id is None:
        db.session.flush()

    historico = SolicitacaoHistorico(
        solicitacao_id=solicitacao.id,
        item_id=item.id if item else None,
        usuario_id=usuario_id,
        acao=acao,
        descricao=descricao,
    )

    db.session.add(historico)

    return historico
