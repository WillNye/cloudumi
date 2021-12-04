from typing import List

from common.lib.pydantic import BaseModel


class RequestContext(BaseModel):
    host: str
    user: str
    groups: List[str]
    request_uuid: str
    uri: str
