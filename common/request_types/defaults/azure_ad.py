from copy import deepcopy

from iambic.plugins.v0_1_0.azure_ad.group.models import AZURE_AD_GROUP_TEMPLATE_TYPE

from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)
from common.request_types.utils import list_provider_typeahead_field_helpers

azure_ad_provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP["azure_ad"]


def _get_default_azure_ad_request_access_request_types(
    field_helper_map: dict[str:TypeAheadFieldHelper],
) -> list[RequestType]:

    access_to_group_request = RequestType(
        name="Request access to Azure AD Group",
        description="Request access to an Azure AD Group for 1 or more users or groups",
        provider=azure_ad_provider_resolver.provider,
        template_types=[
            AZURE_AD_GROUP_TEMPLATE_TYPE,
        ],
        created_by="Noq",
    )

    access_to_group_request.change_types = [
        ChangeType(
            name="Azure AD User Access Request to Group",
            description="Request to add an Azure AD user to an Azure AD Group.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="name",
                    field_type="TextBox",
                    field_text="User E-Mail",
                    description="The email of the Azure AD user that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "name":"{{form.name}}",
            "data_type":"user"
        }"""
            ),
            template_attribute="properties.members",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            created_by="Noq",
        ),
        ChangeType(
            name="Azure AD Subgroup Access Request",
            description="Request to add an Azure AD subgroup to an Azure AD Group.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="group_name",
                    field_type="TextBox",
                    field_text="Group Name",
                    description="The name of the Azure AD group that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "name":"{{form.group_name}}",
            "data_type":"group"
        }"""
            ),
            template_attribute="properties.members",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            created_by="Noq",
        ),
    ]

    return [access_to_group_request]


async def get_default_azure_ad_request_types() -> list[RequestType]:
    azure_ad_typeahead_field_helpers = await list_provider_typeahead_field_helpers(
        provider=azure_ad_provider_resolver.provider
    )
    field_helper_map = {
        field_helper.name: field_helper
        for field_helper in azure_ad_typeahead_field_helpers
    }
    default_request_types = _get_default_azure_ad_request_access_request_types(
        field_helper_map
    )

    return [deepcopy(request_type) for request_type in default_request_types]
