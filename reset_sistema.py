"""Reset do sistema (SQLite) + cria usuário admin.

Uso:
  python reset_sistema.py

Ele apaga o arquivo aruna.db (se existir), recria tabelas e cria:
  login=admin  senha=admin123
"""

import os
from app import create_app
from app.extensions import db
from app.models import User, Departamento

DB_FILE = "aruana.db"

def resetar_banco():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    app = create_app()
    with app.app_context():
        db.create_all()

        dep = Departamento(nome="ENGENHARIA", ativo=True)
        db.session.add(dep)
        db.session.flush()

        admin = User(nome="Administrador", login="admin", role="ADMIN", ativo=True, departamento_id=dep.id)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

        print("OK! Banco recriado.")
        print("Login: admin  |  Senha: admin123")

if __name__ == "__main__":
    resetar_banco()
