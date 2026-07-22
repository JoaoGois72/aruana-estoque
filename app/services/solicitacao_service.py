print("########## SOLICITACAO_SERVICE V2 ##########")

from datetime import datetime
...
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.material import Material
from app.models.solicitacao import Solicitacao
from app.models.solicitacao_item import SolicitacaoItem
print(
    "SOLICITACAO ITEM ARQUIVO:",
    SolicitacaoItem.__module__
)

print(
    "SOLICITACAO ITEM CAMPOS:",
    list(SolicitacaoItem.__table__.columns.keys())
)

STATUS_SOLICITACAO_PENDENTE = "PENDENTE"
STATUS_SOLICITACAO_ANALISE_PARCIAL = "ANALISE_PARCIAL"
STATUS_SOLICITACAO_APROVADA = "APROVADA"
STATUS_SOLICITACAO_APROVADA_PARCIAL = "APROVADA_PARCIAL"
STATUS_SOLICITACAO_REJEITADA = "REJEITADA"
STATUS_SOLICITACAO_ENTREGUE = "ENTREGUE"
STATUS_SOLICITACAO_ENTREGUE_PARCIAL = "ENTREGUE_PARCIAL"

STATUS_ITEM_PENDENTE = "PENDENTE"
STATUS_ITEM_APROVADO = "APROVADO"
STATUS_ITEM_REJEITADO = "REJEITADO"
STATUS_ITEM_ENTREGUE = "ENTREGUE"


def converter_decimal(valor, nome_campo="quantidade"):
    try:
        numero = Decimal(
            str(valor or "0").replace(",", ".")
        )
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(
            f"Valor inválido para {nome_campo}."
        )

    return numero


def obter_solicitacao(solicitacao_id):
    return (
        Solicitacao.query
        .options(
            joinedload(Solicitacao.itens)
            .joinedload(SolicitacaoItem.material)
        )
        .filter(Solicitacao.id == solicitacao_id)
        .first_or_404()
    )


def recalcular_status(solicitacao):
    itens = list(solicitacao.itens)

    if not itens:
        solicitacao.status = STATUS_SOLICITACAO_PENDENTE
        return solicitacao.status

    total = len(itens)

    pendentes = sum(
        1
        for item in itens
        if item.status == STATUS_ITEM_PENDENTE
    )

    aprovados = sum(
        1
        for item in itens
        if item.status == STATUS_ITEM_APROVADO
    )

    rejeitados = sum(
        1
        for item in itens
        if item.status == STATUS_ITEM_REJEITADO
    )

    entregues = sum(
        1
        for item in itens
        if item.status == STATUS_ITEM_ENTREGUE
    )

    if pendentes == total:
        status = STATUS_SOLICITACAO_PENDENTE

    elif rejeitados == total:
        status = STATUS_SOLICITACAO_REJEITADA

    elif entregues == total:
        status = STATUS_SOLICITACAO_ENTREGUE

    elif aprovados == total:
        status = STATUS_SOLICITACAO_APROVADA

    elif entregues > 0:
        status = STATUS_SOLICITACAO_ENTREGUE_PARCIAL

    elif aprovados > 0 and rejeitados > 0 and pendentes == 0:
        status = STATUS_SOLICITACAO_APROVADA_PARCIAL

    elif pendentes > 0 and (
        aprovados > 0 or rejeitados > 0
    ):
        status = STATUS_SOLICITACAO_ANALISE_PARCIAL

    else:
        status = STATUS_SOLICITACAO_PENDENTE

    solicitacao.status = status
    return status


def criar_solicitacao(
    usuario_id,
    observacao,
    local_torre,
    local_pav,
    local_apto,
    materiais_ids,
    quantidades,
):
    if not materiais_ids:
        raise ValueError(
            "Inclua pelo menos um material."
        )

    if len(materiais_ids) != len(quantidades):
        raise ValueError(
            "A lista de materiais e quantidades está inconsistente."
        )

    solicitacao = Solicitacao(
        usuario_id=usuario_id,
        observacao=observacao,
        local_torre=local_torre,
        local_pav=local_pav,
        local_apto=local_apto,
        status=STATUS_SOLICITACAO_PENDENTE,
    )

    db.session.add(solicitacao)

    materiais_adicionados = 0

    try:
        for material_id_texto, quantidade_texto in zip(
            materiais_ids,
            quantidades,
        ):
            if not material_id_texto:
                continue

            try:
                material_id = int(material_id_texto)
            except (TypeError, ValueError):
                raise ValueError(
                    "Foi informado um material inválido."
                )

            quantidade = converter_decimal(
                quantidade_texto,
                "quantidade solicitada",
            )

            if quantidade <= 0:
                raise ValueError(
                    "A quantidade solicitada deve ser maior que zero."
                )

            material = db.session.get(
                Material,
                material_id,
            )

            if material is None:
                raise ValueError(
                    f"Material de código interno "
                    f"{material_id} não encontrado."
                )

            if not material.ativo:
                raise ValueError(
                    f"O material {material.nome} está inativo."
                )

            saldo = Decimal(
                material.saldo_atual or 0
            )

            if quantidade > saldo:
                raise ValueError(
                    f"A quantidade solicitada de "
                    f"{material.nome} é maior que o saldo disponível."
                )

            item = SolicitacaoItem(
                material_id=material.id,
                qtd=quantidade,
            )
            
            if hasattr(item, "status"):
                item.status = STATUS_ITEM_PENDENTE
            
            solicitacao.itens.append(item)
            materiais_adicionados += 1

        if materiais_adicionados == 0:
            raise ValueError(
                "Nenhum item válido foi incluído."
            )

        db.session.commit()
        return solicitacao

    except Exception:
        db.session.rollback()
        raise


def analisar_itens(
    solicitacao,
    decisoes,
    usuario_id,
):
    if solicitacao.status in {
        STATUS_SOLICITACAO_ENTREGUE,
    }:
        raise ValueError(
            "Uma solicitação entregue não pode ser alterada."
        )

    houve_alteracao = False

    try:
        for item in solicitacao.itens:
            dados = decisoes.get(item.id)

            if not dados:
                continue

            decisao = (
                dados.get("decisao")
                or "MANTER"
            ).upper()

            if decisao == "MANTER":
                continue

            if item.status == STATUS_ITEM_ENTREGUE:
                raise ValueError(
                    f"O item {item.material.nome} "
                    "já foi entregue."
                )

            if decisao == "APROVAR":
                quantidade = converter_decimal(
                    dados.get("qtd_aprovada"),
                    "quantidade aprovada",
                )

                quantidade_solicitada = Decimal(
                    item.qtd or 0
                )

                if quantidade <= 0:
                    raise ValueError(
                        f"A quantidade aprovada de "
                        f"{item.material.nome} deve ser maior que zero."
                    )

                if quantidade > quantidade_solicitada:
                    raise ValueError(
                        f"A quantidade aprovada de "
                        f"{item.material.nome} não pode ultrapassar "
                        "a quantidade solicitada."
                    )

                item.status = STATUS_ITEM_APROVADO
                item.qtd_aprovada = quantidade
                item.motivo_rejeicao = None

            elif decisao == "REJEITAR":
                motivo = (
                    dados.get("motivo")
                    or ""
                ).strip()

                if not motivo:
                    raise ValueError(
                        f"Informe o motivo da rejeição de "
                        f"{item.material.nome}."
                    )

                item.status = STATUS_ITEM_REJEITADO
                item.qtd_aprovada = Decimal("0")
                item.motivo_rejeicao = motivo

            else:
                raise ValueError(
                    f"Decisão inválida para "
                    f"{item.material.nome}."
                )

            item.analisado_por_id = usuario_id
            item.data_analise = datetime.utcnow()
            houve_alteracao = True

        if not houve_alteracao:
            raise ValueError(
                "Nenhum item foi selecionado para análise."
            )

        status = recalcular_status(solicitacao)

        if status in {
            STATUS_SOLICITACAO_APROVADA,
            STATUS_SOLICITACAO_APROVADA_PARCIAL,
        }:
            solicitacao.aprovado_por_id = usuario_id
            solicitacao.data_aprovacao = datetime.utcnow()

        db.session.commit()
        return solicitacao

    except Exception:
        db.session.rollback()
        raise


def aprovar_todos_pendentes(
    solicitacao,
    usuario_id,
):
    decisoes = {}

    for item in solicitacao.itens:
        if item.status == STATUS_ITEM_PENDENTE:
            decisoes[item.id] = {
                "decisao": "APROVAR",
                "qtd_aprovada": item.qtd,
            }

    if not decisoes:
        raise ValueError(
            "Não existem itens pendentes para aprovação."
        )

    return analisar_itens(
        solicitacao,
        decisoes,
        usuario_id,
    )


def rejeitar_todos_pendentes(
    solicitacao,
    usuario_id,
    motivo,
):
    motivo = (motivo or "").strip()

    if not motivo:
        raise ValueError(
            "Informe o motivo da rejeição."
        )

    decisoes = {}

    for item in solicitacao.itens:
        if item.status == STATUS_ITEM_PENDENTE:
            decisoes[item.id] = {
                "decisao": "REJEITAR",
                "motivo": motivo,
            }

    if not decisoes:
        raise ValueError(
            "Não existem itens pendentes para rejeição."
        )

    return analisar_itens(
        solicitacao,
        decisoes,
        usuario_id,
    )


def entregar_itens_aprovados(
    solicitacao,
    usuario_id,
):
    itens_aprovados = [
        item
        for item in solicitacao.itens
        if item.status == STATUS_ITEM_APROVADO
    ]

    if not itens_aprovados:
        raise ValueError(
            "Não existem itens aprovados para entrega."
        )

    try:
        for item in itens_aprovados:
            quantidade = Decimal(
                item.qtd_aprovada
                if item.qtd_aprovada is not None
                else item.qtd
            )

            saldo = Decimal(
                item.material.saldo_atual or 0
            )

            if saldo < quantidade:
                raise ValueError(
                    f"Estoque insuficiente para "
                    f"{item.material.nome}."
                )

        for item in itens_aprovados:
            quantidade = Decimal(
                item.qtd_aprovada
                if item.qtd_aprovada is not None
                else item.qtd
            )

            item.material.saldo_atual = (
                Decimal(item.material.saldo_atual or 0)
                - quantidade
            )

            item.status = STATUS_ITEM_ENTREGUE

        solicitacao.entregue_por_id = usuario_id
        solicitacao.data_entrega = datetime.utcnow()

        recalcular_status(solicitacao)

        db.session.commit()
        return solicitacao

    except Exception:
        db.session.rollback()
        raise
