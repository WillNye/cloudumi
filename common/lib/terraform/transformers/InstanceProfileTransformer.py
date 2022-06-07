from common.lib.terraform.transformers.base import BaseEntityTransformer


class InstanceProfileTransformer(BaseEntityTransformer):
    def __init__(self, entity_json: dict, role_identifier: str):
        self.raw_name = entity_json["Arn"].split("/")[-1]
        self._role_identifier = role_identifier
        super().__init__(
            "aws_iam_instance_profile",
            BaseEntityTransformer.safe_name_converter(self.raw_name),
            entity_json,
        )

    def generate_hcl2_code(self, entity_json) -> str:

        return f"""resource "{self._entity_type}" "{self._safe_name}" {{
  name = "{self.raw_name}"
  path = "{entity_json['Path']}"
  role = {self._role_identifier}.name
}}

"""
