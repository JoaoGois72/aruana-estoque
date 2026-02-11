from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user

from app.models import User
from . import auth_bp

@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("estoque.dashboard"))
    return render_template("auth/login.html")

@auth_bp.post("/login")
def login_post():
    login = (request.form.get("login") or "").strip()
    senha = (request.form.get("senha") or "").strip()

    u = User.query.filter_by(login=login, ativo=True).first()
    if not u or not u.check_password(senha):
        flash("Login inválido.", "danger")
        return redirect(url_for("auth.login"))

    login_user(u)
    nxt = request.args.get("next") or url_for("estoque.dashboard")
    return redirect(nxt)

@auth_bp.get("/logout")
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))
