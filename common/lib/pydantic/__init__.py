from typing import Optional

from pydantic import BaseModel as PydanticBaseModel


def to_camel(string):
    """Convert a snake_case string to CamelCase"""
    return "".join(word.capitalize() for word in string.split("_"))


class BaseModel(PydanticBaseModel):
    """BaseModel adds CamelCase aliases to a Pydantic model"""

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

    @classmethod
    def required_fields(cls) -> list[str]:
        return [
            field_name
            for field_name, field in cls.__dict__.get("__fields__", {}).items()
            if field != Optional
        ]
