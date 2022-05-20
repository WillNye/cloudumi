from decimal import Decimal
from typing import Union

from boto3.dynamodb.types import Binary  # noqa
from pynamodax.attributes import MapAttribute
from pynamodax.models import Model
from pynamodb_encoder import decoder, encoder

DYNAMO_EMPTY_STRING = "---DYNAMO-EMPTY-STRING---"
DYNAMODB_EMPTY_DECIMAL = Decimal(0)
ENCODER = encoder.Encoder()
DECODER = decoder.Decoder()


def sanitize_dynamo_obj(
    obj: Union[
        list[dict[str, Union[Decimal, str]]],
        dict[str, Union[Decimal, str]],
        str,
        Decimal,
    ],
) -> Union[int, dict[str, Union[int, str]], str, list[dict[str, Union[int, str]]]]:
    """Traverse a potentially nested object and replace all Dynamo placeholders with actual empty strings
    Args:
        obj (object)
    Returns:
        object: Object with original empty strings
    """
    if isinstance(obj, dict):
        for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
            if k in obj.keys():
                del obj[k]
        return {k: sanitize_dynamo_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_dynamo_obj(elem) for elem in obj]
    else:
        if isinstance(obj, Binary):
            obj = obj.value
        elif str(obj) == DYNAMO_EMPTY_STRING:
            obj = ""
        elif isinstance(obj, Decimal):
            obj = int(obj)
        return obj


class NoqModel(Model):
    def dict(self) -> dict:
        return sanitize_dynamo_obj(ENCODER.encode(self))

    @classmethod
    def from_dict(cls, model_as_dict: dict):
        return DECODER.decode(cls, model_as_dict)


class NoqMapAttribute(MapAttribute):
    @classmethod
    def is_raw(cls):
        return cls == NoqMapAttribute

    def as_dict(self):
        return sanitize_dynamo_obj(super(NoqMapAttribute, self).as_dict())

    def dict(self):  # Helper to standardize the method for converting object to dict
        return self.as_dict()
