from app import create_app
from seed import ensure_seed_data

app = create_app()


def bootstrap_database():
    ensure_seed_data(app)


if __name__ == "__main__":
    bootstrap_database()
    app.run(use_reloader=False)
