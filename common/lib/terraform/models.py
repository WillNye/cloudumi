from typing import List

from common.lib.pydantic import BaseModel


class TerraformResourceModel(BaseModel):
    resource: str
    resource_type: str
    display_text: str
    resource_url: str
    repository_name: str
    repository_url: str
    repository_path: str


class TerraformResourceModelArray(BaseModel):
    terraform_resources: List[TerraformResourceModel]
