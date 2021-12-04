from common.lib.pydantic import BaseModel


class NewTenantRegistration(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    country: str
    marketing_consent: bool = False
    registration_code: str
    # company_name: str
    # company_website: str
    # company_address: str
    # company_city: str
    # company_state: str
    # company_zip: str
    # company_country: str
    # company_phone: str
