from datetime import datetime
from app.models.user import User
from decimal import Decimal, InvalidOperation
import re
import xml.etree.ElementTree as ET

from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from flask import jsonify

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.extensions import db

from app.models import Material, Solicitacao, SolicitacaoItem, Categoria, Entrada, EntradaItem, Fornecedor

from app.blueprints.estoque import estoque_bp
from app.blueprints.relatorios import relatorios_bp

def role_required(*roles):
    from functools import wraps
    from flask_login import current_user
    from flask import abort, redirect

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                return redirect("/auth/login")
            
            if current_user.role == "ADMIN":
                return fn(*args, **kwargs)

            if roles and current_user.role not in roles:
                abort(403)

            return fn(*args, **kwargs)

        return wrapper
    return decorator

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

def gerar_codigo_material():
    ultimo = db.session.query(func.max(Material.id)).scalar()
    proximo = (ultimo or 0) + 1
    return str(proximo)

# ------------------------- dashboard -------------------------
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from app.models.material import Material
from app.models.categoria import Categoria

from app.models import Material, EntradaItem, Categoria
from app.extensions import db


from sqlalchemy import func
from app.models import Material, EntradaItem, Categoria

@estoque_bp.route("/dashboard")
@login_required
def dashboard():

    # 📦 TOTAL DE MATERIAIS
    total_materiais = Material.query.filter_by(ativo=True).count()

    # 🔴 MATERIAIS CRÍTICOS
    materiais_criticos = Material.query.filter(
        Material.saldo_atual <= Material.estoque_minimo,
        Material.ativo == True
    ).all()

    total_criticos = len(materiais_criticos)

    # 📊 CONSUMO POR CATEGORIA
    consumo_categoria = (
        db.session.query(
            Categoria.nome,
            func.coalesce(func.sum(EntradaItem.qtd), 0)
        )
        .join(Material, Material.categoria_id == Categoria.id)
        .outerjoin(EntradaItem, EntradaItem.material_id == Material.id)
        .group_by(Categoria.nome)
        .all()
    )

    categorias = [c[0] for c in consumo_categoria]
    valores_categoria = [float(c[1]) for c in consumo_categoria]

    # 🏆 TOP MATERIAIS
    top_materiais = (
        db.session.query(
            Material.nome,
            func.coalesce(func.sum(EntradaItem.qtd), 0).label("total")
        )
        .outerjoin(EntradaItem, EntradaItem.material_id == Material.id)
        .group_by(Material.nome)
        .order_by(func.sum(EntradaItem.qtd).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "estoque/dashboard.html",
        total_materiais=total_materiais,
        total_criticos=total_criticos,
        categorias=categorias,
        valores_categoria=valores_categoria,
        top_materiais=top_materiais,
        materiais_criticos=materiais_criticos
    )

# ------------------------- solicitações -------------------------
@estoque_bp.route("/solicitacoes")
@login_required
def solicitacoes_lista():
    status = (request.args.get("status") or "").strip()

    q = Solicitacao.query.options(
        joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material)
    )

    if status:
        q = q.filter(Solicitacao.status == status)

    # encarregado vê só as próprias, admin/engenheiro/almoxarife veem tudo
    if current_user.role not in ["ADMIN", "ENGENHEIRO", "ALMOXARIFE", "AUX_ALMOX"]:
        q = q.filter(Solicitacao.usuario_id == current_user.id)

    solicitacoes = q.order_by(Solicitacao.id.desc()).all()

    return render_template(
        "estoque/solicitacoes.html",
        solicitacoes=solicitacoes,
        status=status
    )


@estoque_bp.route("/solicitacoes/nova", methods=["GET", "POST"])
@login_required
def solicitacao_nova():

    if request.method == "POST":

        # 🔹 cria a solicitação
        s = Solicitacao(
            usuario_id=current_user.id,
            observacao=request.form.get("observacao"),
            local_torre=request.form.get("local_torre"),
            local_pav=request.form.get("local_pav"),
            local_apto=request.form.get("local_apto"),
        )

        db.session.add(s)

        # 🔥 PEGAR LISTAS DO FORM
        materiais_ids = request.form.getlist("material_id[]")
        qtds = request.form.getlist("qtd[]")

        from decimal import Decimal

        # 🔥 AQUI ENTRA SUA VALIDAÇÃO
        for i in range(len(materiais_ids)):

            material_id = int(materiais_ids[i])
            qtd = Decimal(qtds[i] or "0")

            material = Material.query.get(material_id)

            # 🚨 VALIDAÇÃO DE ESTOQUE
            if qtd > material.saldo_atual:
                flash(f"Quantidade maior que o saldo para o material: {material.nome}", "danger")
                return redirect(url_for("estoque.solicitacao_nova"))

            if qtd <= 0:
                flash("Quantidade inválida.", "warning")
                return redirect(url_for("estoque.solicitacao_nova"))

            # 🔹 adiciona item
            item = SolicitacaoItem(
                material_id=material_id,
                qtd=qtd
            )

            s.itens.append(item)

        db.session.commit()

        flash("Solicitação criada com sucesso!", "success")
        return redirect(url_for("estoque.solicitacoes_lista"))

    # GET
    materiais = Material.query.filter_by(ativo=True).order_by(Material.nome).all()

    return render_template("estoque/solicitacao_form.html", materiais=materiais)


@estoque_bp.route("/solicitacoes/<int:id>")
@login_required
def solicitacao_detalhe(id):
    s = Solicitacao.query.options(
        joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material)
    ).get_or_404(id)

    if current_user.role not in ["ADMIN", "ENGENHEIRO", "ALMOXARIFE", "AUX_ALMOX"] and s.usuario_id != current_user.id:
        flash("Você não tem acesso a esta solicitação.", "danger")
        return redirect(url_for("estoque.solicitacoes_lista"))
    usuario = User.query.get(s.usuario_id) if s.usuario_id else None
    
    return render_template("estoque/solicitacao_detalhe.html", solicitacao=s, usuario_solicitante=usuario)


@estoque_bp.route("/solicitacoes/<int:id>/aprovar", methods=["POST"])
@login_required
@role_required("ADMIN", "ENGENHEIRO", "MESTRE", "AUX_ALMOX")
def solicitacao_aprovar(id):
    s = Solicitacao.query.options(
        joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material)
    ).get_or_404(id)

    if s.status != "PENDENTE":
        flash("Só é possível aprovar solicitação pendente.", "warning")
        return redirect(url_for("estoque.solicitacao_detalhe", id=id))

    # opcional: validar estoque antes da aprovação
    s.status = "APROVADA"
    s.data_aprovacao = datetime.utcnow()
    s.aprovado_por_id = current_user.id

    db.session.commit()
    flash("Solicitação aprovada com sucesso.", "success")
    return redirect(url_for("estoque.solicitacao_detalhe", id=id))


@estoque_bp.route("/solicitacoes/<int:id>/rejeitar", methods=["POST"])
@login_required
@role_required("ADMIN", "ENGENHEIRO")
def solicitacao_rejeitar(id):
    s = Solicitacao.query.get_or_404(id)

    if s.status != "PENDENTE":
        flash("Só é possível rejeitar solicitação pendente.", "warning")
        return redirect(url_for("estoque.solicitacao_detalhe", id=id))

    s.status = "REJEITADA"
    db.session.commit()

    flash("Solicitação rejeitada.", "info")
    return redirect(url_for("estoque.solicitacao_detalhe", id=id))


@estoque_bp.route("/solicitacoes/<int:id>/entregar", methods=["POST"])
@login_required
@role_required("ADMIN", "ALMOXARIFE", "AUX_ALMOX")
def solicitacao_entregar(id):
    s = Solicitacao.query.options(
        joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material)
    ).get_or_404(id)

    if s.status != "APROVADA":
        flash("Só é possível entregar solicitação aprovada.", "warning")
        return redirect(url_for("estoque.solicitacao_detalhe", id=id))

    # valida estoque
    for item in s.itens:
        mat = item.material
        qtd = Decimal(item.qtd or 0)
        saldo = Decimal(mat.saldo_atual or 0)

        if saldo < qtd:
            flash(f"Estoque insuficiente para {mat.nome}.", "danger")
            return redirect(url_for("estoque.solicitacao_detalhe", id=id))

    # baixa estoque
    for item in s.itens:
        mat = item.material
        qtd = Decimal(item.qtd or 0)
        mat.saldo_atual = Decimal(mat.saldo_atual or 0) - qtd

    s.status = "ENTREGUE"
    s.data_entrega = datetime.utcnow()
    s.entregue_por_id = current_user.id

    db.session.commit()
    flash("Solicitação entregue e estoque baixado com sucesso.", "success")
    return redirect(url_for("estoque.solicitacao_detalhe", id=id))


from sqlalchemy import func

@estoque_bp.get("/solicitacoes/pendentes/qtd")
@login_required
def solicitacoes_pendentes_qtd():
    if current_user.role not in ["ADMIN", "ALMOXARIFE", "AUX_ALMOX"]:
        return jsonify({"total": 0})

    total = Solicitacao.query.filter_by(status="PENDENTE").count()

    return jsonify({
        "total": total
    })
# ------------------------- entradas -------------------------
@estoque_bp.get("/entradas")
@role_required("ALMOXARIFE", "ENGENHEIRO", "ADMIN", "registrar_entrada_nf")
def entradas_lista():
    entradas = Entrada.query.order_by(Entrada.id.desc()).all()
    return render_template("estoque/entradas_lista.html", entradas=entradas)

@estoque_bp.get("/entradas/nova")
@role_required("ALMOXARIFE", "ENGENHEIRO", "ADMIN", "registrar_entrada_nf")
def entrada_nova():
    ent = Entrada(status="RASCUNHO", registrado_por_id=current_user.id)
    db.session.add(ent)
    db.session.commit()
    return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

@estoque_bp.route("/entradas/<int:entrada_id>", methods=["GET", "POST"])
@role_required("ALMOXARIFE", "ENGENHEIRO", "ADMIN", "registrar_entrada_nf")
def entrada_editar(entrada_id):
    ent = Entrada.query.get_or_404(entrada_id)
    materiais = Material.query.filter_by(ativo=True).order_by(Material.nome.asc()).all()

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
@role_required("ADMIN, ENGENHEIR, ALMOXARIFE, concluir_entrada")
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
@role_required("ADMIN", "ALMOXARIFE", "ENGENHEIRO")
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
@role_required("ver_fornecedores")
def fornecedores_lista():
    q = (request.args.get("q") or "").strip()
    base_q = Fornecedor.query.filter_by(ativo=True)
    if q:
        like = f"%{_clean_doc(q)}%"
        base_q = base_q.filter(Fornecedor.documento.like(like))
    fornecedores = base_q.order_by(Fornecedor.id.desc()).all()
    return render_template("estoque/fornecedores.html", fornecedores=fornecedores, q=q)

@estoque_bp.post("/fornecedores/novo")
@role_required("cadastrar_fornecedor")
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
@role_required("ADMIN", "ALMOXARIFE")
def fornecedor_inativar(fornecedor_id):
    f = Fornecedor.query.get_or_404(fornecedor_id)
    f.ativo = False
    db.session.commit()
    flash("Fornecedor inativado.", "warning")
    return redirect(url_for("estoque.fornecedores_lista"))

# ------------------------- importação XML NF-e (básico) -------------------------
from difflib import SequenceMatcher

def buscar_material_inteligente(codigo, nome, unidade):
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
            m.nome.lower(),
            nome.lower()
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
        nome=nome,
        unidade=unidade or "UN",
        saldo_atual=0,
        ativo=True
    )
    db.session.add(novo)
    db.session.flush()

    return novo

@estoque_bp.route("/entradas/<int:entrada_id>/importar_xml", methods=["POST"])
@role_required("registrar_entrada_nf")
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
            mat = Material.query.filter_by(nome=xProd).first()

        if not mat:
            mat = Material(codigo=(cProd or None), nome=(xProd or "SEM DESCRIÇÃO"), unidade=(uCom or "un"), ativo=True)
            db.session.add(mat)
            db.session.flush()

        db.session.add(EntradaItem(entrada_id=ent.id, material_id=mat.id, qtd=qtd))

    db.session.commit()
    flash("XML importado. Confira os itens e salve.", "success")
    return redirect(url_for("estoque.entrada_editar", entrada_id=ent.id))

# =========================
# CATEGORIAS
# =========================
@estoque_bp.route("/categorias")
@login_required
@role_required("ADMIN", "ALMOXARIFE")
def categorias_lista():
    q = (request.args.get("q") or "").strip()

    query = Categoria.query
    if q:
        query = query.filter(Categoria.nome.ilike(f"%{q}%"))

    categorias = query.order_by(Categoria.nome.asc()).all()

    return render_template(
        "estoque/categorias.html",
        categorias=categorias,
        q=q
    )


@estoque_bp.route("/categorias/nova", methods=["GET", "POST"])
@login_required
def categoria_nova():

    if request.method == "POST":

        nome = request.form.get("nome")

        if not nome or nome.strip() == "":
            flash("Informe o nome da categoria", "danger")
            return redirect(url_for("estoque.categoria_nova"))

        # 🚨 evitar duplicado
        if Categoria.query.filter_by(nome=nome).first():
            flash("Categoria já existe!", "warning")
            return redirect(url_for("estoque.categoria_nova"))

        cat = Categoria(nome=nome)

        db.session.add(cat)
        db.session.commit()

        flash("Categoria cadastrada com sucesso!", "success")
        return redirect(url_for("estoque.categorias_lista"))

    return render_template("estoque/categoria_form.html")


@estoque_bp.route("/categorias/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required("ADMIN", "ALMOXARIFE")
def categoria_editar(id):
    categoria = Categoria.query.get_or_404(id)

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()

        if not nome:
            flash("Informe o nome da categoria.", "warning")
            return redirect(url_for("estoque.categoria_editar", id=id))

        existe = Categoria.query.filter(
            db.func.lower(Categoria.nome) == nome.lower(),
            Categoria.id != categoria.id
        ).first()

        if existe:
            flash("Já existe outra categoria com esse nome.", "warning")
            return redirect(url_for("estoque.categoria_editar", id=id))

        categoria.nome = nome
        db.session.commit()

        flash("Categoria atualizada com sucesso.", "success")
        return redirect(url_for("estoque.categorias_lista"))

    return render_template("estoque/categoria_form.html", categoria=categoria)


@estoque_bp.route("/categorias/<int:id>/inativar", methods=["POST"])
@login_required
@role_required("ADMIN")
def categoria_inativar(id):
    categoria = Categoria.query.get_or_404(id)

    categoria.ativo = False
    db.session.commit()

    flash("Categoria inativada.", "warning")
    return redirect(url_for("estoque.categorias_lista"))

@estoque_bp.route("/relatorios")
@login_required
def relatorios():
    return render_template("relatorios/index.html")

from flask import jsonify, request
from flask_login import login_required
from sqlalchemy import or_

@estoque_bp.get("/materiais/buscar")
@login_required
def materiais_buscar():
    termo = (request.args.get("q") or "").strip()

    if not termo:
        return jsonify({"results": []})

    materiais = (
        Material.query
        .filter(
            Material.ativo == True,
            or_(
                Material.nome.ilike(f"%{termo}%"),
                Material.codigo.ilike(f"%{termo}%")
            )
        )
        .order_by(Material.nome.asc())
        .limit(30)
        .all()
    )

    return jsonify({
        "results": [
            {
                "id": m.id,
                "text": f"{m.codigo or '-'} - {m.nome}",
                "saldo": float(m.saldo_atual or 0),
                "unidade": m.unidade or ""
            }
            for m in materiais
        ]
    })
