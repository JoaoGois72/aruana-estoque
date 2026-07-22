from app import create_app
from app.database_updates.runner import executar_atualizacoes


def main():
    app = create_app()

    with app.app_context():
        executar_atualizacoes()


if __name__ == "__main__":
    main()
