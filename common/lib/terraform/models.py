from typing import List

from common.lib.pydantic import BaseModel


class TerraformResourceModel(BaseModel):
    name: str
    resource_type: str
    display_text: str
    resource_url: str
    repository_name: str
    repository_url: str
    web_path: str
    file_path: str
    template_language: str


class TerraformResourceModelArray(BaseModel):
    terraform_resources: List[TerraformResourceModel]
