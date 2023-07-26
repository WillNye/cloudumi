# Imports all DB models in the proper order to prevent race conditions in the models
# Must be imported before any models are imported
from common.config import config  # noqa: F401,E403
from common.pg_core.db_schema_loader import *  # noqa: F401,F403
