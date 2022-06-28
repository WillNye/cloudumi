from typing import List, Optional

from common.lib.pydantic import BaseModel


class RequestContext(BaseModel):
    tenant: str
    user: Optional[str]
    groups: Optional[List[str]]
    request_uuid: str
    uri: str
