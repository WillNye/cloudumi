from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional, Type, get_origin
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from iambic.core.logger import log
from iambic.core.models import BaseModel as IambicBaseModel
from iambic.core.models import BaseTemplate
from iambic.core.template_generation import templatize_resource
from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.policy.models import (
    AwsIamManagedPolicyTemplate,
    PolicyStatement,
)
from iambic.plugins.v0_1_0.aws.iam.role.models import AWS_IAM_ROLE_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import (
    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
)
from jinja2 import BaseLoader
from jinja2.sandbox import ImmutableSandboxedEnvironment
from regex import regex
from sqlalchemy import func as sql_func
from sqlalchemy import select

from common import (
    ChangeField,
    ChangeType,
    IambicTemplateProviderDefinition,
    Tenant,
    TenantProviderDefinition,
)
from common.config import config
from common.config.globals import (
    ASYNC_PG_SESSION,
    GITHUB_APP_APPROVE_PRIVATE_PEM_1,
    GITHUB_APP_URL,
)
from common.config.models import ModelAdapter
from common.iambic.config.models import (
    TRUSTED_PROVIDER_RESOLVER_MAP,
    TrustedProviderResolver,
)
from common.iambic.config.utils import list_tenant_provider_definitions
from common.iambic.git.models import IambicRepo
from common.iambic.templates.utils import (
    get_template_by_id,
    get_template_str_value_for_provider_definition,
    list_tenant_templates,
)
from common.iambic.utils import get_iambic_repo
from common.iambic_request.models import GitHubPullRequest, IambicTemplateChange
from common.lib import noq_json as json
from common.lib.yaml import yaml
from common.models import (
    HubAccount,
    IambicRepoDetails,
    SelfServiceRequestChangeType,
    SelfServiceRequestData,
)
from common.request_types.utils import list_tenant_change_types

if TYPE_CHECKING:
    from common.iambic.templates.models import IambicTemplate


class EnrichedChangeType(SelfServiceRequestChangeType):
    rendered_template: dict
    identifier: str


async def generate_updated_iambic_template(
    tenant: Tenant, request_data: SelfServiceRequestData
) -> Type[BaseTemplate]:
    """Generates the updated iambic template for the given request

    Args:
        tenant (Tenant): The db tenant instance
        request_data (SelfServiceRequestData): The request data
    Returns:
        Type[BaseTemplate]: The updated iambic template
    """
    tenant_id: int = tenant.id  # type: ignore
    request_data_changes = request_data.changes or []

    if not request_data.iambic_template_id:
        # TODO: Add support for a create template request/change type
        raise NotImplementedError

    template = await get_template_by_id(tenant_id, request_data.iambic_template_id)
    provider_ref = TRUSTED_PROVIDER_RESOLVER_MAP[template.provider]
    # TODO support resolving for create types
    template_obj = build_template(template, provider_ref)

    db_change_types = await list_tenant_change_types(
        tenant_id,
        change_type_ids=[ct.change_type_id for ct in request_data_changes],
        summary_only=False,
    )
    db_change_type_map = {str(ct.id): ct for ct in db_change_types}
    iambic_template_ref_map = await get_referenced_templates_map(
        tenant_id, request_data_changes, db_change_type_map
    )
    request_data = await maybe_extend_change_type_provider_definitions(
        tenant_id, request_data, template_obj, provider_ref
    )
    provider_definition_ids = set()

    for change_type in request_data_changes:
        provider_definition_ids.update(set(change_type.provider_definition_ids))

    template_obj = await maybe_add_hub_role_assume_role_policy_document(
        tenant.name, template_obj, db_change_types
    )

    provider_definitions = await get_provider_definitions(
        tenant_id, provider_definition_ids
    )

    # Render and merge the change type templates for the request
    provider_definition_map = {str(pd.id): pd for pd in provider_definitions}
    merged_change_types = await explode_templatize_merge_change_types(
        request_data,
        db_change_type_map,
        iambic_template_ref_map,
        provider_definition_map,
    )

    template_pd_count = await _get_template_pd_count(template, provider_ref)

    # Merge the change types into the template
    # TODO: move to a function (?)
    for change_type in merged_change_types:
        if request_data.expires_at:
            change_type.rendered_template["expires_at"] = request_data.expires_at

        db_change_type = db_change_type_map[change_type.change_type_id]

        if (
            provider_ref.included_providers_attribute
            and db_change_type.provider_definition_field != "Allow None"  # type: ignore
        ):
            if template_pd_count > len(change_type.provider_definition_ids):
                change_type.rendered_template[
                    provider_ref.included_providers_attribute
                ] = [
                    provider_definition_map[pd_id].preferred_identifier
                    for pd_id in change_type.provider_definition_ids
                ]

        update_iambic_template_with_change(
            template_obj,
            db_change_type.template_attribute,  # type: ignore
            change_type.rendered_template,
            db_change_type.apply_attr_behavior,  # type: ignore
        )

    return template_obj


async def get_allowed_approvers(
    tenant_name: str, request_pr, changes: list[IambicTemplateChange]
) -> list[str]:
    """Retrieve the list of allowed approvers from the template body.

    Not using template_bodies for now but may be used to resolve approvers in the future.
    The idea being that
    """
    return config.get_tenant_specific_key(
        "groups.can_admin", tenant_name, ["noq_admins"]
    )


async def get_iambic_pr_instance(
    tenant: Tenant,
    request_id: str,
    requested_by: str,
    pull_request_id: int = None,
    file_paths_being_changed: Optional[list[str]] = None,
    use_request_branch: bool = True,
):
    iambic_repo_details: IambicRepoDetails = await get_iambic_repo(tenant.name)
    try:
        iambic_repo = await IambicRepo.setup(
            tenant,
            iambic_repo_details.repo_name,
            request_id,
            requested_by,
            file_paths_being_changed=file_paths_being_changed,
            use_request_branch=use_request_branch,
        )
    except AttributeError:
        return None

    if iambic_repo_details.git_provider == "github":
        return GitHubPullRequest(
            tenant=tenant,
            request_id=str(request_id),
            requested_by=requested_by,
            pull_request_id=pull_request_id,
            iambic_repo=iambic_repo,
            merge_on_approval=iambic_repo_details.merge_on_approval,
        )

    raise ValueError(f"Unsupported git provider: {iambic_repo.git_provider}")


def noq_github_app_identity() -> str:
    public_key = serialization.load_pem_private_key(
        GITHUB_APP_APPROVE_PRIVATE_PEM_1, None
    ).public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    url_parts = GITHUB_APP_URL.split("/")
    url_parts = [p for p in url_parts if p]  # remove empty string
    login = f"{url_parts[-1]}[bot]"
    integration_config = {
        "github": {
            "allowed_bot_approvers": [
                {
                    "login": login,
                    "es256_pub_key": public_pem.decode("utf-8"),
                },
            ]
        }
    }
    return yaml.dump(integration_config)


async def get_referenced_templates_map(
    tenant_id: int,
    change_types: list[SelfServiceRequestChangeType],
    db_change_type_map: dict[str, ChangeType],
) -> dict[str, Type[BaseTemplate]]:
    template_map = {}
    template_ids = []
    for request_change_type in change_types:
        change_type = db_change_type_map[request_change_type.change_type_id]
        field_element_map = {f.field_key: f for f in change_type.change_fields}
        for field in request_change_type.fields:
            field_element = field_element_map[field.field_key]
            if field_element.field_type == "TypeAheadTemplateRef":
                template_ids.append(field.field_value)

    if template_ids:
        templates = await list_tenant_templates(
            tenant_id, template_ids=template_ids, exclude_template_content=False
        )
        for template in templates:
            provider_ref = TRUSTED_PROVIDER_RESOLVER_MAP[template.provider]
            template_cls = provider_ref.template_map[template.template_type]
            template_obj = template_cls(
                file_path=template.file_path, **template.content.content
            )
            template_map[str(template.id)] = template_obj

    return template_map


def update_iambic_template_with_change(
    iambic_template_instance: Any,
    template_property: str,
    rendered_change_type_template: dict,
    apply_attr_behavior: str,
):
    """Converts the given rendered change type template property to an Iambic field attribute

    Args:
        iambic_template_instance (any): Iambic template instance
        template_property (str): Template property. Supports . notation for nested attributes
        rendered_change_type_template (dict): Rendered change type template
        apply_attr_behavior (str): How to apply the attribute. One of: "Append", "Merge", "Replace"
    """
    split_property_attr = template_property.split(".")
    attr_name = split_property_attr[0]
    if isinstance(iambic_template_instance, list):
        iambic_template_instance = iambic_template_instance[0]

    if template_attr := iambic_template_instance.__fields__.get(attr_name):
        # Determine the class of the attribute
        template_attr = template_attr.type_
        if bool(get_origin(template_attr)):
            # Handle Union types by determining the preferred typing
            supported_types = template_attr.__args__
            preferred_typing = None
            for supported_type in supported_types:
                if type(supported_type) == list:
                    supported_type = supported_type.__args__[0]

                try:
                    # Prefer IambicBaseModel types
                    if issubclass(supported_type, IambicBaseModel):
                        preferred_typing = supported_type
                        break
                    elif preferred_typing is None:
                        preferred_typing = supported_type
                except TypeError:
                    continue

            template_attr = preferred_typing

        if len(split_property_attr) > 1:
            # Handle nested attributes like `ManagedPolicy.policy_document.statement`
            # TODO: Handle forked attribute. Example ManagedPolicy.policy_document can be list or object
            return update_iambic_template_with_change(
                getattr(iambic_template_instance, attr_name),
                ".".join(split_property_attr[1:]),
                rendered_change_type_template,
                apply_attr_behavior,
            )
        else:
            # This is the final attribute
            new_template_val = template_attr(**rendered_change_type_template)
            if expires_at := rendered_change_type_template.get("expires_at"):
                # Reset it to the original value
                new_template_val.expires_at = expires_at

            # Set the attribute on the iambic template instance based on the apply_attr_behavior
            if apply_attr_behavior == "Append":
                new_template_val = [new_template_val]
                if cur_val := getattr(iambic_template_instance, attr_name, []):
                    new_template_val = cur_val + new_template_val
                setattr(iambic_template_instance, attr_name, new_template_val)
                return iambic_template_instance
            elif apply_attr_behavior == "Merge":
                raise NotImplementedError(
                    "Merge attribute has not yet been implemented"
                )
            elif apply_attr_behavior == "Replace":
                raise NotImplementedError(
                    "Replace attribute has not yet been implemented"
                )
            else:
                raise ValueError(
                    f"Invalid apply_attr_behavior {apply_attr_behavior}. Must be one of: Append, Merge, Replace"
                )
    else:
        raise AttributeError(f"Template property {template_property} does not exist")


def templatize_form_val(form_val: Any) -> Any:
    """Templatizes the given form value.
    Really only useful for list[str|int] values.
    It removes duplicate elements, sorts the list, and converts lists to a json string.

    Args:
        form_val (any): Value provided by the user in the form
    Returns:
        any: Templatized form value
    """
    if isinstance(form_val, list):
        try:
            form_val = list(set(form_val))
        except Exception:
            # This is to catch values that can't be cast to a set
            pass

        if not issubclass(type(form_val[0]), BaseTemplate):
            form_val = sorted(json.loads(json.dumps(form_val)))

    return form_val


async def get_field_value(
    change_field: ChangeField,
    form_value: any,
    provider_definition: TenantProviderDefinition,
    iambic_template_ref_map: dict[str, Type[BaseTemplate]],
) -> any:
    """Validates and templatizes the field value for the given change field

    Args:
        change_field (ChangeField): Change field
        form_value (any): Value provided by the user in the form
        provider_definition (TenantProviderDefinition): List of provider definitions.
        iambic_template_ref_map (dict[str, Type[BaseTemplate]]): A map of IAMbic templates referenced in changes
    Returns:
        any: Templatized form value
    """

    field_text = change_field.field_text
    allow_none = change_field.allow_none
    allow_multiple = change_field.allow_multiple
    max_char = change_field.max_char
    validation_regex = change_field.validation_regex

    if not allow_none and form_value is None:
        raise AssertionError(f"Field {field_text} does not allow None values")
    elif max_char and len(form_value) > max_char:
        raise AssertionError(
            f"Field {field_text} must be less than {max_char} characters"
        )
    elif validation_regex and not regex.match(validation_regex, form_value):
        raise AssertionError(
            f"Field {field_text} does not match the required format {validation_regex}"
        )
    elif change_field.field_type != "Choice":
        if not allow_multiple and isinstance(form_value, list):
            raise AssertionError(f"Field {field_text} does not allow multiple values")

        if allow_multiple and not isinstance(form_value, list):
            form_value = [form_value]

        if change_field.field_type == "EnforcedTypeAhead":
            # TODO: Add validation for enforced type ahead fields
            # This would mean checking that the provided value exists.
            # Example: If there was an EnforcedTypeAhead on a noq user, the user must exist in the DB.
            pass
        elif change_field.field_type == "TypeAheadTemplateRef":
            resolved_form_value = []
            if not isinstance(form_value, list):
                form_value = [form_value]

            for template_id in form_value:
                iambic_provider = provider_definition.loaded_iambic_provider()
                iambic_template_ref = iambic_template_ref_map.get(template_id)
                if not iambic_template_ref:
                    raise AssertionError(
                        f"Field {template_id} is not a valid template Id."
                    )
                elif not evaluate_on_provider(iambic_template_ref, iambic_provider):
                    raise AssertionError(
                        f"{iambic_template_ref.resource_id} does not exist in {provider_definition.name}."
                    )

                resource_dict = {
                    "properties": iambic_template_ref.apply_resource_dict(
                        iambic_provider
                    )
                }
                if hasattr(iambic_template_ref, "identifier"):
                    resource_dict[
                        "identifier"
                    ] = get_template_str_value_for_provider_definition(
                        iambic_template_ref.identifier, provider_definition
                    )

                if isinstance(iambic_template_ref, AwsIamManagedPolicyTemplate):
                    resource_dict["properties"]["PolicyDocument"] = json.loads(
                        resource_dict["properties"]["PolicyDocument"]
                    )

                provider_specific_template = iambic_template_ref.__class__(
                    file_path=iambic_template_ref.file_path, **resource_dict
                )

                resolved_form_value.append(provider_specific_template)

            form_value = (
                resolved_form_value if allow_multiple else resolved_form_value[0]
            )

        return templatize_form_val(form_value)

    # Everything beyond this point is handling Option fields
    field_option_map = {
        o["option_text"]: o["option_value"] for o in change_field.options
    }

    if not allow_multiple:
        if len(form_value) > 1:
            # Options are always returned as a list.
            # This is a check for fields where only 1 option may be selected
            raise AssertionError(f"Field {field_text} does not allow multiple values")
        elif form_value[0] not in field_option_map:
            raise AssertionError(
                f"Field {field_text} must be one of {list(field_option_map.keys())}"
            )

        return templatize_form_val(field_option_map.get(form_value[0]))

    field_value = []
    for sub_value in form_value:
        # sub_value is a selected option
        if sub_value not in field_option_map:
            raise AssertionError(
                f"Field {field_text} must be one of {list(field_option_map.keys())}"
            )

        sub_field_value = field_option_map.get(sub_value)
        if isinstance(sub_field_value, list):
            field_value.extend(sub_field_value)
        else:
            field_value.append(sub_field_value)

    return templatize_form_val(field_value)


async def render_change_type_template(
    change_type: ChangeType,
    provider_definition: TenantProviderDefinition,
    iambic_template_ref_map: dict[str, Type[BaseTemplate]],
    request_change_type: SelfServiceRequestChangeType,
    identifier: str,
) -> EnrichedChangeType:
    """Renders change type template rendered using jinja2 with the provided parameters

    Args:
        change_type (ChangeType): The Change type object that relates to this request
        provider_definition (TenantProviderDefinition): List of provider definitions.
        iambic_template_ref_map (dict[str, Type[BaseTemplate]]): A map of IAMbic templates referenced in changes
        request_change_type (SelfServiceRequestChangeType): The change type as part of the request
    Returns:
        EnrichedChangeType: ChangeType with rendered change type template
    """
    pd_count = len(request_change_type.provider_definition_ids)
    pd_field = change_type.provider_definition_field
    if pd_field == "Allow None" and pd_count > 1:
        raise AssertionError(
            f"Change type {change_type.name} does not allow providers definitions"
        )
    elif pd_field == "Allow One" and pd_count > 1:
        raise AssertionError(
            f"Change type {change_type.name} does not allow multiple providers definitions"
        )

    field_element_map = {f.field_key: f for f in change_type.change_fields}

    # Set jinja2 template vars
    template_attrs = dict()
    if provider_definition:
        template_attrs["provider_definitions"] = templatize_form_val(
            [provider_definition.preferred_identifier]
        )

    for field in request_change_type.fields:
        field_key = field.field_key
        field_value = field.field_value
        field = field_element_map.get(field_key)
        if not field:
            raise AssertionError(f"Invalid field provided: {field_key}")
        template_attrs[field.field_key] = await get_field_value(
            field, field_value, provider_definition, iambic_template_ref_map
        )

    rtemplate = ImmutableSandboxedEnvironment(loader=BaseLoader()).from_string(
        change_type.change_template.template
    )
    return EnrichedChangeType(
        **request_change_type.dict(),
        rendered_template=json.loads(str(rtemplate.render(form=template_attrs))),
        identifier=identifier,
    )


def merge_enriched_change_types(change_types: list) -> EnrichedChangeType:
    # Start with the first change type as a representative
    representative = change_types[0].copy(deep=True)

    # Merge provider_definition_ids
    for ect in change_types[1:]:
        representative.provider_definition_ids.extend(ect.provider_definition_ids)

    # Remove duplicates
    representative.provider_definition_ids = list(
        set(representative.provider_definition_ids)
    )

    # Merge rendered_template values
    for ect in change_types[1:]:
        for key, value in ect.rendered_template.items():
            if key in representative.rendered_template:
                # Merge values and remove duplicates
                representative.rendered_template[key] = list(
                    set(representative.rendered_template[key] + value)
                )
            else:
                representative.rendered_template[key] = value

    return representative


def get_templatized_change_types(
    provider_definition_map: dict[str, TenantProviderDefinition],
    request_change_types: list[EnrichedChangeType],
) -> dict[str, list[EnrichedChangeType]]:
    """Get templates for each change type and provider definition"""
    exploded_change_type_map = defaultdict(list[EnrichedChangeType])

    # at this point, all change types should only have one provider definition
    # because they are exploded by provider definition
    for change_type in request_change_types:
        for tpd in change_type.provider_definition_ids:
            exploded_ct = EnrichedChangeType(**change_type.dict())
            exploded_ct.provider_definition_ids = [tpd]
            # Render the template for each provider definition
            # Ensures that the drift created by across provider defs is captured
            exploded_ct.rendered_template = templatize_resource(
                provider_definition_map[tpd],
                change_type.rendered_template,
                substitute_variables=False,
            )
            # exploded change types group by change type identifier, which is related to the request
            exploded_change_type_map[change_type.identifier].append(exploded_ct)

    return exploded_change_type_map


def get_merged_change_types(
    exploded_change_type_map: dict[str, list[EnrichedChangeType]]
):
    """Group change types by change type's rendered template

    Args:
        exploded_change_type_map (dict[str, list[EnrichedChangeType]]): Map of exploded change types, grouped by change type identifier, related to the request.
    """

    # definitive change types, merged with same rendered template
    merged_change_types: list[EnrichedChangeType] = []

    for exploded_change_types in exploded_change_type_map.values():
        # Attempt to merge the change types if they are the same on the boundary of change type
        merged_change_type = None
        for exploded_change_type in exploded_change_types:
            if not merged_change_type:
                merged_change_type = exploded_change_type
                merged_change_types.append(merged_change_type)
                continue

            merged_change_type.provider_definition_ids = list(
                set(
                    [
                        *merged_change_type.provider_definition_ids,
                        *exploded_change_type.provider_definition_ids,
                    ]
                )
            )

        # TODO: do we need to use DeepDiff?
        # append_to_merged = True
        # for merged_change_type in merged_change_types:
        #     # if rendered template is the same, and provider definition ids is not included yet.
        #     if not DeepDiff(
        #         exploded_change_type.rendered_template,
        #         merged_change_type.rendered_template,
        #         ignore_order=True,
        #     ):
        #         merged_change_type.provider_definition_ids = list(
        #             set(
        #                 [
        #                     *merged_change_type.provider_definition_ids,
        #                     *exploded_change_type.provider_definition_ids,
        #                 ]
        #             )
        #         )
        #         append_to_merged = False
        #         break
        # if append_to_merged:
        #     merged_change_types.append(exploded_change_type)

    return merged_change_types


async def maybe_extend_change_type_provider_definitions(
    tenant_id: int,
    request_data: SelfServiceRequestData,
    template_obj: Type[BaseTemplate],
    provider_ref: TrustedProviderResolver,
):
    """Extends the provider definition ids for the given request data if change type doesn't have at least one provider definition

    1. Use Case: Add an Inline Policy for a PermissionSet
        - Cloud Provider: aws
        - Need: I need cloud permissions.
        - Identity: NOQ::AWS::IdentityCenter::PermissionSet

    """

    additional_provider_def = None
    is_permission_set = (
        template_obj.template_type == AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE
    )

    if is_permission_set:
        tenant_org = await get_tenant_org_for_template(tenant_id, template_obj)
        provider_def = await get_account_from_org(tenant_id, tenant_org)
        additional_provider_def = provider_def
    elif any(
        not bool(change_type.provider_definition_ids)
        for change_type in request_data.changes or []
    ):
        # TODO: add comment explaining in what case this is true.
        if not provider_ref.template_provider_attribute:
            raise AssertionError(
                "Unable to determine the provider for this request. Please contact your administrator."
            )
        template_attr = template_obj
        for attr in provider_ref.template_provider_attribute.split("."):
            template_attr = getattr(template_attr, attr)

        provider_def = await list_tenant_provider_definitions(
            tenant_id, provider=provider_ref.provider, name=template_attr
        )
        additional_provider_def = provider_def[0]

    if additional_provider_def:
        for elem in range(len(request_data.changes or [])):
            if not bool(request_data.changes[elem].provider_definition_ids):
                request_data.changes[elem].provider_definition_ids.append(
                    str(additional_provider_def.id)
                )

    return request_data


async def get_tenant_org_for_template(
    tenant_id: int,
    template_obj: Type[BaseTemplate],
) -> TenantProviderDefinition:
    """Get the tenant org for the given template"""
    tenant_aws_orgs = await list_tenant_provider_definitions(
        tenant_id, provider="aws", sub_type="organizations"
    )
    if template_obj.included_orgs and template_obj.included_orgs[0] != "*":
        org_id = template_obj.included_orgs[0]
        tenant_org = next(
            (org for org in tenant_aws_orgs if org.definition["org_id"] == org_id),
            None,
        )
        if not tenant_org:
            raise AssertionError(
                f"Organization {org_id} is not defined for this tenant"
            )
    else:
        assert (
            len(tenant_aws_orgs) == 1
        ), "Please contact your administrator. An AWS Org must be defined as part of this request."
        tenant_org = tenant_aws_orgs[0]

    return tenant_org


async def get_account_from_org(
    tenant_id: int,
    tenant_org: TenantProviderDefinition,
) -> TenantProviderDefinition:
    """Get the account from the given org"""
    account_id = tenant_org.definition["org_account_id"]
    provider_def = await list_tenant_provider_definitions(
        tenant_id,
        provider="aws",
        name=account_id,
    )

    return provider_def[0]


async def maybe_add_hub_role_assume_role_policy_document(
    tenant_name: str,
    template_obj: Type[BaseTemplate],
    db_change_types: list[ChangeType],
) -> Type[BaseTemplate]:
    """
    Adds the hub role assume role policy document to the template
    if the template is an IAM role and the access rules are impacted
    if no existing policy statement exists.

    args:
        tenant_name (str): Name of the tenant
        template_obj (Type[BaseTemplate]): Template object
        db_change_types (list[ChangeType]): List of change types
    returns:
        Type[BaseTemplate]: The potentially updated Template object
    """

    hub_account: HubAccount = (
        ModelAdapter(HubAccount).load_config("hub_account", tenant_name).model
    )
    hub_role_arn = hub_account.role_arn
    impacted_template_attrs = set(
        change_type.template_attribute for change_type in db_change_types
    )

    if template_obj.template_type != AWS_IAM_ROLE_TEMPLATE_TYPE:
        return template_obj
    elif "access_rules" not in impacted_template_attrs:
        return template_obj

    statement_sid = "GeneratedUserAssumeRoleViaNoq"
    assume_role_policy_docs = template_obj.properties.assume_role_policy_document
    set_assume_role_policy_as_list = isinstance(assume_role_policy_docs, list)
    if not set_assume_role_policy_as_list:
        assume_role_policy_docs = [assume_role_policy_docs]

    for assume_role_policy_doc in assume_role_policy_docs:
        add_spoke_role_policy_statement = True
        policy_statements = assume_role_policy_doc.statement
        if not isinstance(policy_statements, list):
            policy_statements = [policy_statements]

        if any(
            policy_statement.sid == statement_sid
            for policy_statement in policy_statements
        ):
            continue

        for policy_statement in policy_statements:
            if policy_statement.included_accounts != ["*"] and sorted(
                policy_statement.included_accounts
            ) != sorted(assume_role_policy_doc.included_accounts):
                continue
            elif bool(policy_statement.excluded_accounts):
                continue
            elif policy_statement.effect != "Allow":
                continue
            elif not all(
                required_action in policy_statement.action
                for required_action in {"sts:AssumeRole", "sts:TagSession"}
            ):
                continue
            elif (
                policy_statement.principal != hub_role_arn
                and policy_statement.principal.aws != hub_role_arn
                and hub_role_arn not in policy_statement.principal.aws
            ):
                continue

            add_spoke_role_policy_statement = False
            break

        if add_spoke_role_policy_statement:
            policy_statements.append(
                PolicyStatement(
                    effect="Allow",
                    action=["sts:AssumeRole", "sts:TagSession"],
                    principal={"aws": hub_role_arn},
                    sid=statement_sid,
                )
            )
            assume_role_policy_doc.statement = policy_statements

    return template_obj


async def explode_templatize_merge_change_types(
    request_data: SelfServiceRequestData,
    db_change_type_map: dict[str, ChangeType],
    iambic_template_ref_map: dict[str, Type[BaseTemplate]],
    provider_definition_map: dict[str, TenantProviderDefinition],
) -> list[EnrichedChangeType]:
    """Explodes each change type by its provider definitions, renders the change type template, and merge it back together"""
    enriched_change_types = await _get_enriched_change_types_exploded(
        request_data,
        db_change_type_map,
        iambic_template_ref_map,
        provider_definition_map,
    )

    exploded_change_type_map = get_templatized_change_types(
        provider_definition_map, enriched_change_types
    )

    return get_merged_change_types(exploded_change_type_map)


def build_template(
    template: IambicTemplate, provider_ref: TrustedProviderResolver
) -> IambicTemplate:
    """Builds the template object from the template db model"""
    template_cls = provider_ref.template_map[template.template_type]  # type: ignore
    template_content = template.content.content
    template_content.pop("file_path", None)
    template_obj = template_cls(file_path=template.file_path, **template_content)
    return template_obj


async def get_provider_definitions(tenant_id: int, provider_definition_ids: set[str]):
    """Returns the provider definitions for the given tenant"""
    async with ASYNC_PG_SESSION() as session:
        stmt = select(TenantProviderDefinition).filter(
            TenantProviderDefinition.tenant_id == tenant_id,
            TenantProviderDefinition.id.in_(list(provider_definition_ids)),
        )
        provider_definitions = (await session.execute(stmt)).scalars().all()
        pd_db_ids = [str(pd.id) for pd in provider_definitions]
        if missing_ids := set(provider_definition_ids) - set(pd_db_ids):
            raise AssertionError(
                f"Invalid provider definition ids provided: {missing_ids}"
            )
    return provider_definitions


async def _get_template_pd_count(
    template: IambicTemplate,
    provider_ref: TrustedProviderResolver,
) -> int:
    """Returns the number of provider definitions associated with the given template"""
    if not provider_ref.included_providers_attribute:
        return 0

    # Get template provider def count
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(sql_func.count())
            .select_from(IambicTemplateProviderDefinition)
            .filter(IambicTemplateProviderDefinition.iambic_template_id == template.id)
        )
        template_pd_count = (await session.execute(stmt)).scalar()
    return template_pd_count


async def _get_enriched_change_types_exploded(
    request_data: SelfServiceRequestData,
    db_change_type_map: dict[str, ChangeType],
    iambic_template_ref_map: dict[str, Type[BaseTemplate]],
    provider_definition_map: dict[str, TenantProviderDefinition],
) -> list[EnrichedChangeType]:
    """Renders the change type templates for the given self-service request"""

    if not request_data.changes:
        log.info(
            "No changes provided for self service request",
            request_data=request_data.dict(),
        )
        return []

    tasks = []
    for change_type in request_data.changes:
        identifier = str(uuid4())
        if not bool(change_type.provider_definition_ids):
            log.error(
                "Change type does not have any provider definitions",
                change_type=change_type.change_type_id,
                change_type_name=db_change_type_map[change_type.change_type_id].name,
            )
            raise AssertionError(
                f'Change type "{db_change_type_map[change_type.change_type_id].name}" does not have any provider definitions'
            )

        for pd_id in change_type.provider_definition_ids:
            tasks.append(
                render_change_type_template(
                    db_change_type_map[change_type.change_type_id],
                    provider_definition_map[pd_id],
                    iambic_template_ref_map,
                    change_type,
                    identifier,
                )
            )
    enriched_change_types = await asyncio.gather(*tasks)
    return enriched_change_types
