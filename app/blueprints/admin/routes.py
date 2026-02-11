from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.user import User
from app.permissions import roles_required
from . import admin_bp


# LISTA DE USUÁRIOS
@admin_bp.get("/usuarios")
@login_required
@roles_required("ADMIN")
def usuarios_lista():
    usuarios = User.query.order_by(User.nome.asc()).all()
    return render_template("admin/usuarios_lista.html", usuarios=usuarios)


# NOVO USUÁRIO
@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def usuario_novo():
    if request.method == "POST":
        nome = request.form.get("nome")
        login = request.form.get("login")
        senha = request.form.get("senha")
        role = request.form.get("role")

        if not nome or not login or not senha:
            flash("Preencha todos os campos.", "warning")
            return redirect(url_for("admin.usuario_novo"))

        if User.query.filter_by(login=login).first():
            flash("Login já existe.", "danger")
            return redirect(url_for("admin.usuario_novo"))

        u = User(nome=nome, login=login, role=role, ativo=True)
        u.set_password(senha)

        db.session.add(u)
        db.session.commit()

        flash("Usuário criado.", "success")
        return redirect(url_for("admin.usuarios_lista"))

    return render_template("admin/usuario_form.html", usuario=None)


# EDITAR USUÁRIO
@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def usuario_editar(user_id):
    u = User.query.get_or_404(user_id)

    if request.method == "POST":
        u.nome = request.form.get("nome")
        u.login = request.form.get("login")
        u.role = request.form.get("role")

        db.session.commit()
        flash("Usuário atualizado.", "success")
        return redirect(url_for("admin.usuarios_lista"))

    return render_template("admin/usuario_form.html", usuario=u)


# RESETAR SENHA
@admin_bp.post("/usuarios/<int:user_id>/reset_senha")
@login_required
@roles_required("ADMIN")
def usuario_reset_senha(user_id):
    u = User.query.get_or_404(user_id)
    u.set_password("123")
    db.session.commit()

    flash(f"Senha de {u.login} redefinida para 123.", "warning")
    return redirect(url_for("admin.usuarios_lista"))


# ATIVAR
@admin_bp.post("/usuarios/<int:user_id>/ativar")
@login_required
@roles_required("ADMIN")
def usuario_ativar(user_id):
    u = User.query.get_or_404(user_id)
    u.ativo = True
    db.session.commit()
    return redirect(url_for("admin.usuarios_lista"))


# INATIVAR
@admin_bp.post("/usuarios/<int:user_id>/inativar")
@login_required
@roles_required("ADMIN")
def usuario_inativar(user_id):
    u = User.query.get_or_404(user_id)
    u.ativo = False
    db.session.commit()
    return redirect(url_for("admin.usuarios_lista"))

