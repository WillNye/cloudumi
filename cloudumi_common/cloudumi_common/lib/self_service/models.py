from typing import List, Optional, Union

from cloudumi_common.lib.pydantic import BaseModel
from cloudumi_common.models import (
    AwsResourcePrincipalModel,
    HoneybeeAwsResourceTemplatePrincipalModel,
)


class SelfServiceTypeaheadModel(BaseModel):
    icon: str
    number_of_affected_resources: int
    display_text: str
    account: Optional[str] = None
    details_endpoint: str
    application_name: Optional[str] = None
    principal: Union[
        AwsResourcePrincipalModel, HoneybeeAwsResourceTemplatePrincipalModel
    ]


class SelfServiceTypeaheadModelArray(BaseModel):
    typeahead_entries: Optional[List[SelfServiceTypeaheadModel]] = None
