import os

from common.scripts.alembic import run_alembic_migrations
from common.scripts.data_migrations import run_data_migrations
from functional_tests import run_tests as functional_tests

if __name__ == "__main__":
    if os.getenv("RUNTIME_PROFILE") == "PREFLIGHT":
        run_alembic_migrations()
        run_data_migrations()

    if os.getenv("RUNTIME_PROFILE") == "PREFLIGHT" and os.getenv("STAGE") != "prod":
        # We do not want to run functional_tests in prod because
        # it is taking 45 minutes to re-run all the tests that
        # passed in staging
        # We cannot simply move it out because pre-flights
        # tasks are run in parallel
        functional_tests.run()
