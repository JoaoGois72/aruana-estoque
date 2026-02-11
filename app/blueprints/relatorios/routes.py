from datetime import datetime
from decimal import Decimal
from io import BytesIO

from flask import render_template, request, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from openpyxl import Workbook

from app.extensions import db
from app.models.material import Material
from app.models.solicitacao import Solicitacao
from app.models.solicitacao_item import SolicitacaoItem
from app.models.entrada import Entrada

# Se você tiver Fornecedor no projeto, descomente:
# from app.models.fornecedor import Fornecedor

from . import relatorios_bp


# =========================
# Helpers
# =========================
def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


def _d(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _wb_to_bytes(wb: Workbook) -> BytesIO:
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _pdf_table(title: str, headers: list[str], rows: list[list[str]], filename: str):
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    w, h = A4

    x = 15 * mm
    y = h - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, title)
    y -= 10 * mm

    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 8 * mm

    # Cabeçalho
    c.setFont("Helvetica-Bold", 9)
    colw = (w - 30 * mm) / max(1, len(headers))
    for i, head in enumerate(headers):
        c.drawString(x + i * colw, y, head[:28])
    y -= 6 * mm

    c.setFont("Helvetica", 9)
    for row in rows:
        if y < 20 * mm:
            c.showPage()
            y = h - 20 * mm
            c.setFont("Helvetica-Bold", 9)
            for i, head in enumerate(headers):
                c.drawString(x + i * colw, y, head[:28])
            y -= 6 * mm
            c.setFont("Helvetica", 9)

        for i, cell in enumerate(row):
            c.drawString(x + i * colw, y, str(cell)[:28])
        y -= 5 * mm

    c.showPage()
    c.save()
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# =========================
# Index
# =========================
@relatorios_bp.get("/")
@login_required
def relatorios_index():
    return render_template("relatorios/index.html")


# =========================
# 1) ESTOQUE ATUAL
# =========================
@relatorios_bp.get("/estoque")
@login_required
def relatorio_estoque():
    q = request.args.get("q", "").strip()

    query = Material.query.filter_by(ativo=True)
    if q:
        query = query.filter(Material.descricao.ilike(f"%{q}%"))

    materiais = query.order_by(Material.descricao.asc()).all()
    return render_template("relatorios/estoque.html", materiais=materiais, q=q)


@relatorios_bp.get("/estoque.xlsx")
@login_required
def relatorio_estoque_xlsx():
    q = request.args.get("q", "").strip()

    query = Material.query.filter_by(ativo=True)
    if q:
        query = query.filter(Material.descricao.ilike(f"%{q}%"))
    materiais = query.order_by(Material.descricao.asc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Estoque Atual"
    ws.append(["Código", "Descrição", "Unidade", "Saldo", "Reservado", "Disponível", "Mínimo"])

    for m in materiais:
        saldo = _d(getattr(m, "saldo_atual", 0))
        reservado = _d(getattr(m, "reservado_atual", 0))
        minimo = _d(getattr(m, "estoque_minimo", 0))
        disponivel = saldo - reservado
        ws.append([
            m.codigo or "",
            m.descricao,
            m.unidade,
            float(saldo),
            float(reservado),
            float(disponivel),
            float(minimo),
        ])

    bio = _wb_to_bytes(wb)
    return send_file(
        bio,
        as_attachment=True,
        download_name="relatorio_estoque.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@relatorios_bp.get("/estoque.pdf")
@login_required
def relatorio_estoque_pdf():
    q = request.args.get("q", "").strip()
    query = Material.query.filter_by(ativo=True)
    if q:
        query = query.filter(Material.descricao.ilike(f"%{q}%"))
    materiais = query.order_by(Material.descricao.asc()).all()

    headers = ["Código", "Descrição", "Un", "Saldo", "Res", "Disp", "Min"]
    rows = []
    for m in materiais:
        saldo = _d(getattr(m, "saldo_atual", 0))
        reservado = _d(getattr(m, "reservado_atual", 0))
        minimo = _d(getattr(m, "estoque_minimo", 0))
        disponivel = saldo - reservado
        rows.append([
            m.codigo or "-",
            m.descricao,
            m.unidade,
            str(saldo),
            str(reservado),
            str(disponivel),
            str(minimo),
        ])

    return _pdf_table("Relatório de Estoque Atual", headers, rows, "relatorio_estoque.pdf")


# =========================
# 2) CONSUMO (ENTREGUE) POR TORRE/APTO
# =========================
@relatorios_bp.get("/consumo")
@login_required
def relatorio_consumo():
    data_de = _parse_date(request.args.get("de"))
    data_ate = _parse_date(request.args.get("ate"))
    torre = (request.args.get("torre") or "").strip()
    pav = (request.args.get("pav") or "").strip()
    apto = (request.args.get("apto") or "").strip()

    filtros = [Solicitacao.status == "ENTREGUE"]
    if data_de:
        filtros.append(Solicitacao.data_entrega >= data_de)
    if data_ate:
        filtros.append(Solicitacao.data_entrega <= data_ate)
    if torre:
        filtros.append(Solicitacao.local_torre == torre)
    if pav:
        filtros.append(Solicitacao.local_pav == pav)
    if apto:
        filtros.append(Solicitacao.local_apto == apto)

    itens = (
        SolicitacaoItem.query
        .join(Solicitacao, Solicitacao.id == SolicitacaoItem.solicitacao_id)
        .options(joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .all()
    )

    return render_template(
        "relatorios/consumo.html",
        itens=itens,
        de=request.args.get("de", ""),
        ate=request.args.get("ate", ""),
        torre=torre,
        pav=pav,
        apto=apto,
    )


@relatorios_bp.get("/consumo.xlsx")
@login_required
def relatorio_consumo_xlsx():
    data_de = _parse_date(request.args.get("de"))
    data_ate = _parse_date(request.args.get("ate"))
    torre = (request.args.get("torre") or "").strip()
    pav = (request.args.get("pav") or "").strip()
    apto = (request.args.get("apto") or "").strip()

    filtros = [Solicitacao.status == "ENTREGUE"]
    if data_de:
        filtros.append(Solicitacao.data_entrega >= data_de)
    if data_ate:
        filtros.append(Solicitacao.data_entrega <= data_ate)
    if torre:
        filtros.append(Solicitacao.local_torre == torre)
    if pav:
        filtros.append(Solicitacao.local_pav == pav)
    if apto:
        filtros.append(Solicitacao.local_apto == apto)

    itens = (
        SolicitacaoItem.query
        .join(Solicitacao, Solicitacao.id == SolicitacaoItem.solicitacao_id)
        .options(joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Consumo"
    ws.append(["Solic#", "Entrega", "Torre", "Pav", "Apto", "Material", "Qtd", "Un"])

    for it in itens:
        s = it.solicitacao  # relationship (se você não tiver, me diga)
        m = it.material
        ws.append([
            s.id,
            s.data_entrega.strftime("%d/%m/%Y") if s.data_entrega else "",
            s.local_torre or "",
            s.local_pav or "",
            s.local_apto or "",
            m.descricao if m else "",
            float(_d(it.qtd)),
            m.unidade if m else "",
        ])

    bio = _wb_to_bytes(wb)
    return send_file(
        bio,
        as_attachment=True,
        download_name="relatorio_consumo.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@relatorios_bp.get("/consumo.pdf")
@login_required
def relatorio_consumo_pdf():
    data_de = _parse_date(request.args.get("de"))
    data_ate = _parse_date(request.args.get("ate"))
    torre = (request.args.get("torre") or "").strip()
    pav = (request.args.get("pav") or "").strip()
    apto = (request.args.get("apto") or "").strip()

    filtros = [Solicitacao.status == "ENTREGUE"]
    if data_de:
        filtros.append(Solicitacao.data_entrega >= data_de)
    if data_ate:
        filtros.append(Solicitacao.data_entrega <= data_ate)
    if torre:
        filtros.append(Solicitacao.local_torre == torre)
    if pav:
        filtros.append(Solicitacao.local_pav == pav)
    if apto:
        filtros.append(Solicitacao.local_apto == apto)

    itens = (
        SolicitacaoItem.query
        .join(Solicitacao, Solicitacao.id == SolicitacaoItem.solicitacao_id)
        .options(joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .all()
    )

    headers = ["Solic#", "Entrega", "Local", "Material", "Qtd", "Un"]
    rows = []
    for it in itens:
        s = it.solicitacao
        m = it.material
        local = f"{s.local_torre or ''}-{s.local_pav or ''}-{s.local_apto or ''}"
        rows.append([
            str(s.id),
            s.data_entrega.strftime("%d/%m/%Y") if s.data_entrega else "",
            local,
            m.descricao if m else "",
            str(_d(it.qtd)),
            m.unidade if m else "",
        ])

    return _pdf_table("Relatório de Consumo (ENTREGUE)", headers, rows, "relatorio_consumo.pdf")


# =========================
# 3) ENTRADAS POR FORNECEDOR
# =========================
@relatorios_bp.get("/entradas")
@login_required
def relatorio_entradas_fornecedor():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))
    doc = (request.args.get("doc") or "").strip()

    q = Entrada.query
    if de:
        q = q.filter(Entrada.data_entrada >= de)
    if ate:
        q = q.filter(Entrada.data_entrada <= ate)
    if doc:
        # Se você armazena documento do fornecedor na entrada:
        # q = q.filter(Entrada.documento_fornecedor == doc)
        # Se não tiver, filtramos pelo texto (nome_fornecedor):
        q = q.filter(Entrada.nome_fornecedor.ilike(f"%{doc}%"))

    entradas = q.order_by(Entrada.id.desc()).limit(500).all()

    return render_template(
        "relatorios/entradas.html",
        entradas=entradas,
        de=request.args.get("de", ""),
        ate=request.args.get("ate", ""),
        doc=doc,
    )


@relatorios_bp.get("/entradas.xlsx")
@login_required
def relatorio_entradas_fornecedor_xlsx():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))
    doc = (request.args.get("doc") or "").strip()

    q = Entrada.query
    if de:
        q = q.filter(Entrada.data_entrada >= de)
    if ate:
        q = q.filter(Entrada.data_entrada <= ate)
    if doc:
        q = q.filter(Entrada.nome_fornecedor.ilike(f"%{doc}%"))

    entradas = q.order_by(Entrada.id.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Entradas"
    ws.append(["Entrada#", "Data", "NF", "Fornecedor", "Status"])

    for e in entradas:
        ws.append([
            e.id,
            e.data_entrada.strftime("%d/%m/%Y") if e.data_entrada else "",
            getattr(e, "numero_nf", "") or "",
            getattr(e, "nome_fornecedor", "") or "",
            getattr(e, "status", "") or "",
        ])

    bio = _wb_to_bytes(wb)
    return send_file(
        bio,
        as_attachment=True,
        download_name="relatorio_entradas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@relatorios_bp.get("/entradas.pdf")
@login_required
def relatorio_entradas_fornecedor_pdf():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))
    doc = (request.args.get("doc") or "").strip()

    q = Entrada.query
    if de:
        q = q.filter(Entrada.data_entrada >= de)
    if ate:
        q = q.filter(Entrada.data_entrada <= ate)
    if doc:
        q = q.filter(Entrada.nome_fornecedor.ilike(f"%{doc}%"))

    entradas = q.order_by(Entrada.id.desc()).all()

    headers = ["Entrada#", "Data", "NF", "Fornecedor", "Status"]
    rows = []
    for e in entradas:
        rows.append([
            str(e.id),
            e.data_entrada.strftime("%d/%m/%Y") if e.data_entrada else "",
            getattr(e, "numero_nf", "") or "",
            getattr(e, "nome_fornecedor", "") or "",
            getattr(e, "status", "") or "",
        ])

    return _pdf_table("Relatório de Entradas por Fornecedor", headers, rows, "relatorio_entradas.pdf")


# =========================
# 4) SAÍDAS POR PERÍODO (ENTREGUE)
# =========================
@relatorios_bp.get("/saidas")
@login_required
def relatorio_saidas_periodo():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))

    filtros = [Solicitacao.status == "ENTREGUE"]
    if de:
        filtros.append(Solicitacao.data_entrega >= de)
    if ate:
        filtros.append(Solicitacao.data_entrega <= ate)

    solicitacoes = (
        Solicitacao.query
        .options(joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .limit(300)
        .all()
    )

    return render_template(
        "relatorios/saidas.html",
        solicitacoes=solicitacoes,
        de=request.args.get("de", ""),
        ate=request.args.get("ate", ""),
    )


@relatorios_bp.get("/saidas.xlsx")
@login_required
def relatorio_saidas_periodo_xlsx():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))

    filtros = [Solicitacao.status == "ENTREGUE"]
    if de:
        filtros.append(Solicitacao.data_entrega >= de)
    if ate:
        filtros.append(Solicitacao.data_entrega <= ate)

    solicitacoes = (
        Solicitacao.query
        .options(joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Saídas"
    ws.append(["Solic#", "Entrega", "Torre", "Pav", "Apto", "Material", "Qtd", "Un"])

    for s in solicitacoes:
        for it in s.itens:
            m = it.material
            ws.append([
                s.id,
                s.data_entrega.strftime("%d/%m/%Y") if s.data_entrega else "",
                s.local_torre or "",
                s.local_pav or "",
                s.local_apto or "",
                m.descricao if m else "",
                float(_d(it.qtd)),
                m.unidade if m else "",
            ])

    bio = _wb_to_bytes(wb)
    return send_file(
        bio,
        as_attachment=True,
        download_name="relatorio_saidas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@relatorios_bp.get("/saidas.pdf")
@login_required
def relatorio_saidas_periodo_pdf():
    de = _parse_date(request.args.get("de"))
    ate = _parse_date(request.args.get("ate"))

    filtros = [Solicitacao.status == "ENTREGUE"]
    if de:
        filtros.append(Solicitacao.data_entrega >= de)
    if ate:
        filtros.append(Solicitacao.data_entrega <= ate)

    solicitacoes = (
        Solicitacao.query
        .options(joinedload(Solicitacao.itens).joinedload(SolicitacaoItem.material))
        .filter(and_(*filtros))
        .order_by(Solicitacao.id.desc())
        .all()
    )

    headers = ["Solic#", "Entrega", "Local", "Material", "Qtd", "Un"]
    rows = []
    for s in solicitacoes:
        local = f"{s.local_torre or ''}-{s.local_pav or ''}-{s.local_apto or ''}"
        for it in s.itens:
            m = it.material
            rows.append([
                str(s.id),
                s.data_entrega.strftime("%d/%m/%Y") if s.data_entrega else "",
                local,
                m.descricao if m else "",
                str(_d(it.qtd)),
                m.unidade if m else "",
            ])

    return _pdf_table("Relatório de Saídas (ENTREGUE) por Período", headers, rows, "relatorio_saidas.pdf")
