from functools import wraps
from flask import redirect, abort
from flask_login import current_user

# ============================
# PERMISSÕES POR PERFIL
# ============================
ROLE_PERMS = {

    "ADMIN": ["*"],

    "ENGENHEIRO": [
        "ver_estoque",
        "criar_solicitacao",
        "aprovar_solicitacao",
        "entregar_solicitacao",
        "ver_relatorios",
        "ver_fornecedores",
        "cadastrar_fornecedor",
    ],

    "MESTRE": [
        "ver_estoque",
        "criar_solicitacao",
    ],

    "ENCARREGADO": [
        "ver_estoque",
        "criar_solicitacao",
    ],

    "ALMOXARIFE": [
        "ver_estoque",
        "gerenciar_materiais",
        "entregar_solicitacao",
        "ver_fornecedores",
        "cadastrar_fornecedor",
    ],

    "AUX_ALMOX": [
        "ver_estoque",
        "entregar_solicitacao",
    ],
}

def tem_permissao(permissao):

    role = current_user.role

    if role not in ROLE_PERMS:
        return False

    if "*" in ROLE_PERMS[role]:
        return True

    return permissao in ROLE_PERMS[role]

def perm_required(permissao):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                return redirect("/auth/login")

            if not tem_permissao(permissao):
                abort(403)

            return fn(*args, **kwargs)
        return wrapper
    return decorator