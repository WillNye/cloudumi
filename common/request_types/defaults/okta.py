from copy import deepcopy

from iambic.plugins.v0_1_0.okta.app.models import OKTA_APP_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.okta.group.models import OKTA_GROUP_TEMPLATE_TYPE

from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)
from common.request_types.utils import list_provider_typeahead_field_helpers

okta_provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP["okta"]


def _get_default_okta_request_access_request_types(
    field_helper_map: dict[str, TypeAheadFieldHelper]
) -> list[RequestType]:
    access_to_group_request = RequestType(
        name="Request access to Okta Group",
        description="Request access to an Okta Group for 1 or more users or groups",
        provider=okta_provider_resolver.provider,
        created_by="Noq",
        express_request_support=False,
    )

    access_to_app_request = deepcopy(access_to_group_request)
    access_to_app_request.name = "Request access to Okta App"
    access_to_app_request.description = (
        "Request access to an Okta App for 1 or more users or groups"
    )

    access_to_group_request.change_types = [
        ChangeType(
            name="Okta User Access Request to Group",
            description="Request to add an Okta user to an Okta Group.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="name",
                    field_type="TypeAhead",
                    field_text="User E-Mail",
                    description="The email of the Okta user that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["Okta User"].id,
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "username":"{{form.name}}"
        }"""
            ),
            template_attribute="properties.members",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            supported_template_types=[
                OKTA_GROUP_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        )
    ]

    access_to_app_request.change_types = [
        ChangeType(
            name="Okta User Access Request to App",
            description="Request to add an Okta user to an Okta App.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="name",
                    field_type="TypeAhead",
                    field_text="User E-Mail",
                    description="The email of the Okta user that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["Okta User"].id,
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "user":"{{form.name}}"
        }"""
            ),
            template_attribute="properties.assignments",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            supported_template_types=[
                OKTA_APP_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
        ChangeType(
            name="Okta Group Access Request to App",
            description="Request to add an Okta Group to an Okta App.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="name",
                    field_type="TypeAhead",
                    field_text="Group Name",
                    description="The name of the Group user that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["Okta Group"].id,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "group":"{{form.name}}"
        }"""
            ),
            template_attribute="properties.assignments",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            supported_template_types=[
                OKTA_APP_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
    ]

    return [access_to_group_request, access_to_app_request]


async def get_default_okta_request_types() -> list[RequestType]:
    okta_typeahead_field_helpers = await list_provider_typeahead_field_helpers(
        provider=okta_provider_resolver.provider
    )
    field_helper_map = {
        field_helper.name: field_helper for field_helper in okta_typeahead_field_helpers
    }
    default_request_types = _get_default_okta_request_access_request_types(
        field_helper_map
    )

    return [deepcopy(request_type) for request_type in default_request_types]
