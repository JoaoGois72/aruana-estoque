from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import xml.etree.ElementTree as ET

from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required

from sqlalchemy import or_

from app.extensions import db
from app.permissions import perm_required
from app.models import Material, Solicitacao, SolicitacaoItem, Entrada, EntradaItem, Fornecedor
from app.permissions import perm_required, roles_required

from . import estoque_bp


# ------------------------- helpers -------------------------
def _to_decimal(v, default="0"):
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

def _clean_doc(doc: str) -> str:
    return re.sub(r"\D+", "", doc or "")

def _local_format(torre, pav, ap, txt):
    if (txt or "").strip():
        return txt.strip()
    parts = []
    if torre: parts.append(f"Torre {torre}")
    if pav: parts.append(f"{pav}")
    if ap: parts.append(f"Apt {ap}")
    return " · ".join(parts) if parts else "-"

def _torres():
    # Aruana Garden: 6 torres
    return [f"{i:02d}" for i in range(1, 7)]

def _pavs():
    return ["Térreo"] + [f"Pav {i}" for i in range(1, 8)] + ["Cobertura"]

def _aptos_por_pav():
    d = {}
    d["Térreo"] = [f"{i:02d}" for i in range(1, 9)]
    for p in range(1, 8):
        d[f"Pav {p}"] = [f"{p}{i:02d}" for i in range(1, 9)]
    d["Cobertura"] = []
    return d


# ------------------------- dashboard -------------------------
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

@estoque_bp.get("/dashboard")
@login_required
def dashboard():

    # ======================================
    # INDICADORES GERAIS
    # ======================================

    # Total de materiais em estoque
    total_estoque = (
        db.session.query(func.sum(Material.saldo_atual))
        .filter(Material.ativo == True)
        .scalar()
    ) or 0

    # Solicitações pendentes
    solicitacoes_pendentes = (
        Solicitacao.query
        .filter_by(status="PENDENTE", ativo=True)
        .count()
    )

    # Materiais críticos
    materiais_criticos = (
        Material.query
        .filter(
            Material.ativo == True,
            Material.saldo_atual <= Material.estoque_minimo
        )
        .count()
    )

    # ======================================
    # CONSUMO DO MÊS
    # ======================================
    hoje = datetime.now()
    inicio_mes = datetime(hoje.year, hoje.month, 1)

    consumo_mes = Decimal("0")

    solicitacoes_mes = (
        Solicitacao.query
        .filter(
            Solicitacao.status == "ENTREGUE",
            Solicitacao.data_entrega >= inicio_mes
        )
        .all()
    )

    for s in solicitacoes_mes:
        for item in s.itens:
            consumo_mes += Decimal(str(item.qtd or 0))

    # ======================================
    # RANKING DE TORRES
    # ======================================
    consumo_torres = defaultdict(Decimal)

    entregues = Solicitacao.query.filter_by(status="ENTREGUE").all()

    for s in entregues:
        torre = s.local_torre or "N/A"
        for item in s.itens:
            consumo_torres[torre] += Decimal(str(item.qtd or 0))

    ranking_torres = sorted(
        consumo_torres.items(),
        key=lambda x: x[1],
        reverse=True
    )

    ranking_torres = [
        {"torre": t, "qtd": float(q)}
        for t, q in ranking_torres
    ]

    # ======================================
    # GRÁFICO: materiais com menor saldo
    # ======================================
    materiais = (
        Material.query
        .filter_by(ativo=True)
        .order_by(Material.saldo_atual.asc())
        .limit(5)
        .all()
    )

    graf_materiais = [
        {
            "descricao": m.descricao,
            "saldo": float(m.saldo_atual or 0)
        }
        for m in materiais
    ]

    return render_template(
        "estoque/dashboard.html",

        # indicadores
        total_estoque=float(total_estoque),
        solicitacoes_pendentes=solicitacoes_pendentes,
        materiais_criticos=materiais_criticos,
        consumo_mes=float(consumo_mes),

        # ranking
        ranking_torres=ranking_torres,

        # gráfico
        graf_materiais=graf_materiais
    )


    # ===============================
    # 4. Entradas por mês
    # ===============================
    entradas_mes = (
        db.session.query(
            func.strftime("%Y-%m", Entrada.data_entrada),
            func.count(Entrada.id)
        )
        .group_by(func.strftime("%Y-%m", Entrada.data_entrada))
        .all()
    )

    graf_entradas = [
        {"mes": m, "qtd": q}
        for m, q in entradas_mes
    ]

    return render_template(
        "estoque/dashboard.html",
        graf_materiais=graf_materiais,
        graf_status=graf_status,
        graf_torres=graf_torres,
        graf_entradas=graf_entradas
    )



# ------------------------- materiais -------------------------
@estoque_bp.get("/materiais")
@perm_required("ver_estoque")
def materiais():
    q = (request.args.get("q") or "").strip()
    base_q = Material.query.filter_by(ativo=True)
    if q:
        like = f"%{q}%"
        base_q = base_q.filter(or_(Material.descricao.ilike(like), Material.codigo.ilike(like)))
    materiais = base_q.order_by(Material.descricao.asc()).all()
    return render_template("estoque/materiais.html", materiais=materiais, q=q)

@estoque_bp.get("/materiais/novo")
@perm_required("gerenciar_materiais")
def material_novo():
    return render_template("estoque/material_form.html", mat=None)

@estoque_bp.post("/materiais/novo")
@perm_required("gerenciar_materiais")
def material_novo_post():
    codigo = (request.form.get("codigo") or "").strip() or None
    descricao = (request.form.get("descricao") or "").strip()
    unidade = (request.form.get("unidade") or "").strip()
    estoque_minimo = _to_decimal(request.form.get("estoque_minimo") or "0", "0")
    saldo_atual = _to_decimal(request.form.get("saldo_atual") or "0", "0")

    if not descricao or not unidade:
        flash("Descrição e Unidade são obrigatórios.", "warning")
        return redirect(url_for("estoque.material_novo"))

    existente = None
    if codigo:
        existente = Material.query.filter_by(codigo=codigo).first()
    if not existente:
        existente = Material.query.filter_by(descricao=descricao, unidade=unidade).first()

    if existente:
        existente.ativo = True
        existente.descricao = descricao
        existente.unidade = unidade
        existente.estoque_minimo = estoque_minimo
        existente.saldo_atual = saldo_atual
        if codigo:
            existente.codigo = codigo
        db.session.commit()
        flash("Material já existia. Reativado/atualizado.", "info")
        return redirect(url_for("estoque.materiais"))

    m = Material(
        codigo=codigo,
        descricao=descricao,
        unidade=unidade,
        estoque_minimo=estoque_minimo,
        saldo_atual=saldo_atual,
        reservado_atual=Decimal("0"),
        ativo=True,
    )
    db.session.add(m)
    db.session.commit()
    flash("Material cadastrado.", "success")
    return redirect(url_for("estoque.materiais"))

@estoque_bp.route("/materiais/<int:material_id>/editar", methods=["GET", "POST"])
@perm_required("gerenciar_materiais")
def material_editar(material_id):
    mat = Material.query.get_or_404(material_id)
    if request.method == "GET":
        return render_template("estoque/material_form.html", mat=mat)

    codigo = (request.form.get("codigo") or "").strip() or None
    descricao = (request.form.get("descricao") or "").strip()
    unidade = (request.form.get("unidade") or "").strip()
    estoque_minimo = _to_decimal(request.form.get("estoque_minimo") or "0", "0")
    saldo_atual = _to_decimal(request.form.get("saldo_atual") or str(mat.saldo_atual or 0), "0")

    if not descricao or not unidade:
        flash("Descrição e Unidade são obrigatórios.", "warning")
        return redirect(url_for("estoque.material_editar", material_id=material_id))

    if codigo and Material.query.filter(Material.codigo == codigo, Material.id != mat.id).first():
        flash("Já existe outro material com esse código.", "danger")
        return redirect(url_for("estoque.material_editar", material_id=material_id))

    mat.codigo = codigo
    mat.descricao = descricao
    mat.unidade = unidade
    mat.estoque_minimo = estoque_minimo
    mat.saldo_atual = saldo_atual
    db.session.commit()

    flash("Material atualizado.", "success")
    return redirect(url_for("estoque.materiais"))

@estoque_bp.get("/materiais/<int:material_id>/inativar")
@perm_required("gerenciar_materiais")
def material_inativar(material_id):
    mat = Material.query.get_or_404(material_id)
    mat.ativo = False
    db.session.commit()
    flash("Material inativado.", "info")
    return redirect(url_for("estoque.materiais"))


# ------------------------- solicitações -------------------------
@estoque_bp.get("/solicitacoes")
@perm_required("ver_estoque")
def solicitacoes_lista():
    status = (request.args.get("status") or "").strip().upper()
    q = Solicitacao.query.filter_by(ativo=True)

    if status:
        q = q.filter_by(status=status)
    solicitacoes = q.order_by(Solicitacao.id.desc()).all()
    return render_template("estoque/solicitacoes_lista.html", solicitacoes=solicitacoes, status=status)

@estoque_bp.route("/solicitacoes/nova", methods=["GET", "POST"])
@perm_required("criar_solicitacao")
def solicitacao_nova():
    materiais = Material.query.filter_by(ativo=True).order_by(Material.descricao.asc()).all()

    if request.method == "POST":
        obs = (request.form.get("obs") or "").strip()
        torre = request.form.get("local_torre")
        pav = request.form.get("local_pav")
        apto = request.form.get("local_apto")
        txt = request.form.get("local_txt")

        sol = Solicitacao(
            solicitante_id=current_user.id,
            departamento_id=current_user.departamento_id,
            status="PENDENTE",
            obs=obs,
            local_torre=torre,
            local_pav=pav,
            local_apto=apto,
            local_txt=txt,
        )
        db.session.add(sol)
        db.session.flush()

        materiais_ids = request.form.getlist("material_id[]")
        quantidades = request.form.getlist("qtd[]")

        itens = []
        for mat_id, qtd in zip(materiais_ids, quantidades):
            if not mat_id or not qtd:
                continue
            qtd_dec = _to_decimal(qtd, "0")
            if qtd_dec <= 0:
                continue
            itens.append((int(mat_id), qtd_dec))

        if not itens:
            db.session.rollback()
            flash("Inclua pelo menos 1 material com quantidade válida.", "warning")
            return redirect(url_for("estoque.solicitacao_nova"))

        for mat_id, qtd_dec in itens:
            mat = Material.query.get(mat_id)
            if not mat or not mat.ativo:
                db.session.rollback()
                flash("Material inválido.", "danger")
                return redirect(url_for("estoque.solicitacao_nova"))
            if (mat.saldo_atual or 0) < qtd_dec:
                db.session.rollback()
                flash(f"Saldo insuficiente para: {mat.descricao}.", "danger")
                return redirect(url_for("estoque.solicitacao_nova"))

        for mat_id, qtd_dec in itens:
            db.session.add(SolicitacaoItem(solicitacao_id=sol.id, material_id=mat_id, qtd=qtd_dec))

        db.session.commit()
        flash("Solicitação criada com sucesso.", "success")
        return redirect(url_for("estoque.solicitacoes_lista"))

    return render_template(
        "estoque/solicitacao_form.html",
        materiais=materiais,
        torres=_torres(),
        pavs=_pavs(),
        aptos_por_pav=_aptos_por_pav(),
    )

@estoque_bp.get("/solicitacoes/<int:solicitacao_id>")
@perm_required("ver_estoque")
def solicitacao_detalhe(solicitacao_id):
    s = Solicitacao.query.get_or_404(solicitacao_id)
    return render_template(
        "estoque/solicitacao_detalhe.html",
        s=s,
        local=_local_format(s.local_torre, s.local_pav, s.local_apto, s.local_txt),
    )

@estoque_bp.post("/solicitacoes/<int:solicitacao_id>/aprovar")
@perm_required("aprovar_solicitacao")
def solicitacao_aprovar(solicitacao_id):
    s = Solicitacao.query.get_or_404(solicitacao_id)
    if s.status != "PENDENTE":
        flash("Solicitação não está pendente.", "warning")
        return redirect(url_for("estoque.solicitacoes_lista"))

    for it in s.itens:
        mat = it.material
        if (mat.saldo_atual or 0) < it.qtd:
            flash(f"Saldo insuficiente para aprovar: {mat.descricao}.", "danger")
            return redirect(url_for("estoque.solicitacao_detalhe", solicitacao_id=s.id))

    for it in s.itens:
        mat = it.material
        mat.saldo_atual = (mat.saldo_atual or 0) - it.qtd

    s.status = "APROVADA"
    s.aprovado_por = current_user.id
    s.data_aprovacao = datetime.utcnow()
    db.session.commit()
    flash("Solicitação aprovada e estoque baixado.", "success")
    return redirect(url_for("estoque.solicitacao_detalhe", solicitacao_id=s.id))

@estoque_bp.post("/solicitacoes/<int:solicitacao_id>/entregar")
@perm_required("entregar_solicitacao")
def solicitacao_entregar(solicitacao_id):
    s = Solicitacao.query.get_or_404(solicitacao_id)
    if s.status != "APROVADA":
        flash("Somente solicitações aprovadas podem ser entregues.", "warning")
        return redirect(url_for("estoque.solicitacao_detalhe", solicitacao_id=s.id))
    s.status = "ENTREGUE"
    s.entregue_por = current_user.id
    s.data_entrega = datetime.utcnow()
    db.session.commit()
    flash("Solicitação entregue.", "success")
    return redirect(url_for("estoque.solicitacao_detalhe", solicitacao_id=s.id))

@estoque_bp.post("/solicitacoes/<int:solicitacao_id>/inativar")
@roles_required("ADMIN")
def solicitacao_inativar(solicitacao_id):
    sol = Solicitacao.query.get_or_404(solicitacao_id)
    sol.ativo = False
    db.session.commit()
    flash("Solicitação inativada.", "warning")
    return redirect(url_for("estoque.solicitacoes_lista"))

# ------------------------- entradas -------------------------
@estoque_bp.get("/entradas")
@perm_required("registrar_entrada_nf")
def entradas_lista():
    entradas = Entrada.query.order_by(Entrada.id.desc()).all()
    return render_template("estoque/entradas_lista.html", entradas=entradas)

@estoque_bp.get("/entradas/nova")
@perm_required("registrar_entrada_nf")
def entrada_nova():
    ent = Entrada(status="RASCUNHO", registrado_por_id=current_user.id)
    db.session.add(ent)
    db.session.commit()
    return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

@estoque_bp.route("/entradas/<int:entrada_id>", methods=["GET", "POST"])
@perm_required("registrar_entrada_nf")
def entrada_editar(entrada_id):
    ent = Entrada.query.get_or_404(entrada_id)
    materiais = Material.query.filter_by(ativo=True).order_by(Material.descricao.asc()).all()

    if request.method == "GET":
        return render_template("estoque/entrada_form.html", ent=ent, materiais=materiais)

    acao = request.form.get("acao") or "salvar"

    if acao == "cancelar":
        flash("Entrada cancelada (sem salvar alterações).", "info")
        return redirect(url_for("estoque.entradas_lista"))

    ent.numero_nf = (request.form.get("numero_nf") or "").strip()
    ent.documento_fornecedor = _clean_doc(request.form.get("documento_fornecedor") or "")
    ent.nome_fornecedor = (request.form.get("nome_fornecedor") or "").strip()

    if ent.documento_fornecedor and not ent.nome_fornecedor:
        f = Fornecedor.query.filter_by(documento=ent.documento_fornecedor, ativo=True).first()
        if f:
            ent.nome_fornecedor = f.nome

    materiais_ids = request.form.getlist("material_id[]")
    quantidades = request.form.getlist("qtd[]")

    itens = []
    for mat_id, qtd in zip(materiais_ids, quantidades):
        if not mat_id or not qtd:
            continue
        qtd_dec = _to_decimal(qtd, "0")
        if qtd_dec <= 0:
            continue
        itens.append((int(mat_id), qtd_dec))

    if not ent.numero_nf or not ent.documento_fornecedor:
        flash("Informe Número da NF e CNPJ/CPF.", "warning")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    if not itens:
        flash("Inclua pelo menos 1 material com quantidade válida.", "warning")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    ent.itens.clear()
    db.session.flush()

    for mat_id, qtd_dec in itens:
        db.session.add(EntradaItem(entrada_id=ent.id, material_id=mat_id, qtd=qtd_dec))

    db.session.commit()
    flash("Entrada salva (RASCUNHO).", "success")
    return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

@estoque_bp.post("/entradas/<int:entrada_id>/concluir")
@perm_required("concluir_entrada")
def entrada_concluir(entrada_id):
    ent = Entrada.query.get_or_404(entrada_id)
    if ent.status == "CONCLUIDA":
        flash("Entrada já está concluída.", "info")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    if not ent.itens:
        flash("Sem itens para concluir.", "warning")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    for it in ent.itens:
        mat = it.material
        mat.saldo_atual = (mat.saldo_atual or 0) + it.qtd

    ent.status = "CONCLUIDA"
    db.session.commit()
    flash("Entrada concluída e estoque atualizado.", "success")
    return redirect(url_for("estoque.entradas_lista"))

@estoque_bp.post("/entradas/<int:entrada_id>/excluir")
@roles_required("ADMIN", "ALMOXARIFE")
def entrada_excluir(entrada_id):
    entrada = Entrada.query.get_or_404(entrada_id)

    # se a entrada estiver concluída, devolve o saldo
    if entrada.status == "CONCLUIDA":
        for item in entrada.itens:
            mat = Material.query.get(item.material_id)
            if mat:
                qtd = Decimal(str(item.qtd))
                mat.saldo_atual = (mat.saldo_atual or Decimal("0")) - qtd

    db.session.delete(entrada)
    db.session.commit()

    flash("Entrada excluída com sucesso.", "success")
    return redirect(url_for("estoque.entradas_lista"))


# ------------------------- fornecedores -------------------------
@estoque_bp.get("/fornecedores")
@perm_required("registrar_entrada_nf")
def fornecedores_lista():
    q = (request.args.get("q") or "").strip()
    base_q = Fornecedor.query.filter_by(ativo=True)
    if q:
        like = f"%{_clean_doc(q)}%"
        base_q = base_q.filter(Fornecedor.documento.like(like))
    fornecedores = base_q.order_by(Fornecedor.id.desc()).all()
    return render_template("estoque/fornecedores.html", fornecedores=fornecedores, q=q)

@estoque_bp.post("/fornecedores/novo")
@perm_required("registrar_entrada_nf")
def fornecedor_novo():
    documento = _clean_doc(request.form.get("documento") or "")
    nome = (request.form.get("nome") or "").strip()
    if not documento or not nome:
        flash("Informe CNPJ/CPF e Nome.", "warning")
        return redirect(url_for("estoque.fornecedores_lista"))

    f = Fornecedor.query.filter_by(documento=documento).first()
    if f:
        f.nome = nome
        f.ativo = True
        db.session.commit()
        flash("Fornecedor atualizado.", "info")
        return redirect(url_for("estoque.fornecedores_lista"))

    f = Fornecedor(documento=documento, nome=nome, ativo=True)
    db.session.add(f)
    db.session.commit()
    flash("Fornecedor cadastrado.", "success")
    return redirect(url_for("estoque.fornecedores_lista"))

from flask_login import login_required
from app.models.fornecedor import Fornecedor
from flask import jsonify

@estoque_bp.get("/fornecedores/buscar")
@login_required
def fornecedor_buscar():
    doc = request.args.get("doc", "").strip()

    if not doc:
        return jsonify({})

    forn = Fornecedor.query.filter_by(documento=doc).first()

    if not forn:
        return jsonify({})

    return jsonify({
        "id": forn.id,
        "nome": forn.nome,
        "documento": forn.documento
    })

@estoque_bp.post("/fornecedores/<int:fornecedor_id>/inativar")
@roles_required("ADMIN")
def fornecedor_inativar(fornecedor_id):
    f = Fornecedor.query.get_or_404(fornecedor_id)
    f.ativo = False
    db.session.commit()
    flash("Fornecedor inativado.", "warning")
    return redirect(url_for("estoque.fornecedores_lista"))

# ------------------------- importação XML NF-e (básico) -------------------------
from difflib import SequenceMatcher

def buscar_material_inteligente(codigo, descricao, unidade):
    # 1) Busca pelo código exato
    if codigo:
        mat = Material.query.filter_by(codigo=codigo).first()
        if mat:
            return mat

    # 2) Busca por descrição parecida
    mats = Material.query.all()
    melhor = None
    melhor_score = 0.0

    for m in mats:
        score = SequenceMatcher(
            None,
            m.descricao.lower(),
            descricao.lower()
        ).ratio()

        if score > melhor_score:
            melhor_score = score
            melhor = m

    # Se similaridade alta, usa o material existente
    if melhor and melhor_score > 0.80:
        return melhor

    # 3) Se não achou, cria material novo
    novo = Material(
        codigo=codigo,
        descricao=descricao,
        unidade=unidade or "UN",
        saldo_atual=0,
        ativo=True
    )
    db.session.add(novo)
    db.session.flush()

    return novo

@estoque_bp.route("/entradas/<int:entrada_id>/importar_xml", methods=["POST"])
@perm_required("registrar_entrada_nf")
def entrada_importar_xml(entrada_id):
    ent = Entrada.query.get_or_404(entrada_id)
    arq = request.files.get("xml")
    if not arq:
        flash("Selecione um arquivo XML.", "warning")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    xml_bytes = arq.read()
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        flash("XML inválido.", "danger")
        return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

    nNF = root.findtext(".//{*}ide/{*}nNF") or root.findtext(".//ide/nNF") or ""
    ent.numero_nf = (nNF or "").strip()

    cnpj = root.findtext(".//{*}emit/{*}CNPJ") or root.findtext(".//emit/CNPJ") or ""
    cpf = root.findtext(".//{*}emit/{*}CPF") or root.findtext(".//emit/CPF") or ""
    ent.documento_fornecedor = _clean_doc(cnpj or cpf)
    ent.nome_fornecedor = (root.findtext(".//{*}emit/{*}xNome") or root.findtext(".//emit/xNome") or "").strip()

    dets = root.findall(".//{*}det") or root.findall(".//det")
    materiais_por_codigo = {m.codigo: m for m in Material.query.filter_by(ativo=True).all() if m.codigo}

    ent.itens.clear()
    db.session.flush()

    for det in dets:
        cProd = det.findtext(".//{*}prod/{*}cProd") or det.findtext(".//prod/cProd") or ""
        xProd = det.findtext(".//{*}prod/{*}xProd") or det.findtext(".//prod/xProd") or ""
        uCom = det.findtext(".//{*}prod/{*}uCom") or det.findtext(".//prod/uCom") or ""
        qCom = det.findtext(".//{*}prod/{*}qCom") or det.findtext(".//prod/qCom") or "0"

        qtd = _to_decimal(qCom, "0")
        if qtd <= 0:
            continue

        mat = None
        if cProd and cProd in materiais_por_codigo:
            mat = materiais_por_codigo[cProd]
        else:
            mat = Material.query.filter_by(descricao=xProd).first()

        if not mat:
            mat = Material(codigo=(cProd or None), descricao=(xProd or "SEM DESCRIÇÃO"), unidade=(uCom or "un"), ativo=True)
            db.session.add(mat)
            db.session.flush()

        db.session.add(EntradaItem(entrada_id=ent.id, material_id=mat.id, qtd=qtd))

    db.session.commit()
    flash("XML importado. Confira os itens e salve.", "success")
    return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

from sqlalchemy import func
from app.models.material import Material


