import os

from app import create_app
from app.seeds.seed_runner import SeedRunner

# Enable seeding automatically when the server starts; can be turned off by overriding
# RUN_SEEDS_ON_STARTUP in the environment before launch.
os.environ.setdefault("RUN_SEEDS_ON_STARTUP", "true")

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        SeedRunner(app).run_if_enabled()
    app.run(use_reloader=False)
