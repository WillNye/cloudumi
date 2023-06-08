from typing import Any, List, Optional

from common.lib.pydantic import BaseModel


class RequestContext(BaseModel):
    tenant: str
    db_tenant: Any
    user: Optional[str]
    db_user: Any
    groups: Optional[List[str]]
    request_uuid: str
    uri: str
    mfa_setup_required: Optional[bool]
    password_reset_required: Optional[bool]
    needs_to_sign_eula: Optional[bool]
    mfa_verification_required: Optional[bool]
    is_admin: Optional[bool]
