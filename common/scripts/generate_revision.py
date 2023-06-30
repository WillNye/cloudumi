import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from common.pg_core.models import Base  # noqa: F401,E402


def generate_revision():
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, "migration", autogenerate=True)


if __name__ == "__main__":
    # To apply migrations
    # python -m common.scripts.generate_revision
    generate_revision()
