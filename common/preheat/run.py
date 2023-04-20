import os

from common.scripts.alembic import run_alembic_migrations

if __name__ == "__main__":
    if os.getenv("RUNTIME_PROFILE") == "PREHEAT":
        run_alembic_migrations()
