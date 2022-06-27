from types import GenericAlias
from typing import Dict, List, Optional, Set, Union, get_args, get_origin

from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import ModelField


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

    @staticmethod
    def get_field_type(field: any) -> any:
        """
        Resolves the base field type for a model
        """
        field_type = field.type_ if isinstance(field, ModelField) else field
        if field_type == Optional:
            field_type = field_type[0]

        if (
            type(field_type) in [dict, Dict, GenericAlias, list, List, Set, set]
            or get_origin(field_type) == Union
        ) and (field_types := get_args(field_type)):
            return BaseModel.get_field_type(field_types[0])

        return field_type

    def dict(self, exclude_secrets=True, **kwargs):
        return_val = dict()

        # Iterate model fields
        for field_name, field in self.__class__.__dict__.get("__fields__", {}).items():
            dict_key = field_name
            field_val = getattr(self, field_name)

            if isinstance(field, ModelField):
                if exclude_secrets and field.field_info.extra.get("is_secret", False):
                    continue

            # Get base field type accounting for things like union, list, set, field types
            field_type = self.get_field_type(field)
            try:
                if issubclass(field_type, BaseModel) and field_val:
                    if isinstance(field_val, list) or isinstance(field_val, set):
                        return_val[dict_key] = [
                            field_elem.dict(exclude_secrets, **kwargs)
                            for field_elem in field_val
                        ]
                    else:
                        return_val[dict_key] = field_val.dict(exclude_secrets, **kwargs)
                else:
                    return_val[dict_key] = field_val

            except TypeError:
                # Catch all for things like SpecialForm, GenericAlias, etc.
                return_val[dict_key] = field_val

        return return_val
