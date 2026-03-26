from functools import wraps
from flask import redirect, abort
from flask_login import current_user

# ============================
# PERMISSÕES POR PERFIL
# ============================
ROLE_PERMS = {

    "ADMIN": [
        "ver_estoque",
        "criar_solicitacao",
        "aprovar_solicitacao",
        "entregar_solicitacao",
        "gerenciar_materiais",
        "ver_relatorios",
        "gerenciar_usuarios",
    ],

    "ENGENHEIRO": [
        "ver_estoque",
        "criar_solicitacao",
        "aprovar_solicitacao",
        "entregar_solicitacao",
        "ver_relatorios",
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
    ],

    "AUX_ALMOX": [
        "ver_estoque",
        "entregar_solicitacao",
    ],
}

# ============================
# 🔐 PERMISSÃO POR ROLE
# ============================
def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect("/auth/login")

            if current_user.role not in roles:
                abort(403)

            return fn(*args, **kwargs)
        return wrapper
    return decorator


