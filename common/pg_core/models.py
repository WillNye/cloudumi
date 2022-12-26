from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SoftDeleteMixin:
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Boolean, default=False)


try:
    import sqlalchemy.types as types

    class AsaList(types.TypeDecorator):
        # SQL-like DBs don't have a List type - so do that here by converting to a comma
        # separate string.
        impl = types.UnicodeText

        def process_bind_param(self, value, dialect):
            # produce a string from an iterable
            try:
                return ",".join(value)
            except TypeError:
                return value

        def process_result_value(self, value, dialect):
            if value:
                return value.split(",")
            return []

except ImportError:  # pragma: no cover

    class AsaList:  # type: ignore
        pass
