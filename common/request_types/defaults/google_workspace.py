from iambic.plugins.v0_1_0.google_workspace.group.models import (
    GOOGLE_GROUP_TEMPLATE_TYPE,
)

from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)
from common.request_types.utils import list_provider_typeahead_field_helpers

google_workspace_provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP["google_workspace"]


def _get_default_google_workspace_request_access_request_types(
    field_helper_map: dict[str:TypeAheadFieldHelper],
) -> list[RequestType]:

    access_to_group_request = RequestType(
        name="Request access to Google Workspace Group",
        description="Request access to a Google Workspace Group for 1 or more users or groups",
        provider=google_workspace_provider_resolver.provider,
        template_types=[
            GOOGLE_GROUP_TEMPLATE_TYPE,
        ],
        created_by="Noq",
    )

    access_to_group_request.change_types = [
        ChangeType(
            name="Google Workspace access request",
            description="Request access to a Google Workspace Group.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="email",
                    field_type="TextBox",
                    field_text="E-Mail",
                    description="The email of the user or group that requires access",
                    allow_none=False,
                    allow_multiple=True,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "email":"{{form.email}}"
        }"""
            ),
            template_attribute="properties.members",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            created_by="Noq",
        )
    ]

    return [access_to_group_request]


async def get_default_google_workspace_request_types() -> list[RequestType]:
    google_workspace_typeahead_field_helpers = (
        await list_provider_typeahead_field_helpers(
            provider=google_workspace_provider_resolver.provider
        )
    )
    field_helper_map = {
        field_helper.name: field_helper
        for field_helper in google_workspace_typeahead_field_helpers
    }
    default_request_types = _get_default_google_workspace_request_access_request_types(
        field_helper_map
    )

    return default_request_types
