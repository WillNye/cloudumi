from typing import List, Optional

from common import Tenant
from common.lib.pydantic import BaseModel


class RequestContext(BaseModel):
    tenant: str
    db_tenant: Tenant
    user: Optional[str]
    groups: Optional[List[str]]
    request_uuid: str
    uri: str
    mfa_setup_required: Optional[bool]
    password_reset_required: Optional[bool]
    needs_to_sign_eula: Optional[bool]
    mfa_verification_required: Optional[bool]
    is_admin: Optional[bool]
