import os

from common.scripts.alembic import run_alembic_migrations
from functional_tests import run_tests as functional_tests

if __name__ == "__main__":
    if os.getenv("RUNTIME_PROFILE") == "PREFLIGHT":
        run_alembic_migrations()
        functional_tests.run()
