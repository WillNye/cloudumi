from typing import Optional

from common.lib.pydantic import BaseModel


class NewTenantRegistration(BaseModel):
    first_name: str
    last_name: str
    email: str
    country: Optional[str]
    marketing_consent: Optional[bool] = True
    registration_code: Optional[str]
    # company_name: str
    # company_website: str
    # company_address: str
    # company_city: str
    # company_state: str
    # company_zip: str
    # company_country: str
    # company_phone: str
