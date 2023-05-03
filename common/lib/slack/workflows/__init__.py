from __future__ import annotations

from functools import partial
from typing import Callable, Optional

from common.lib.pydantic import BaseModel

FRIENDLY_RESOURCE_TYPE_NAMES = {
    "NOQ::AWS::IAM::Group": "AWS IAM Groups",
    "NOQ::AWS::IAM::ManagedPolicy": "AWS IAM Managed Policies",
    "NOQ::AWS::IAM::Role": "AWS IAM Roles",
    "NOQ::AWS::IAM::User": "AWS IAM Users",
    "NOQ::AWS::IdentityCenter::PermissionSet": "AWS Permission Sets",
    "NOQ::Google::Group": "Google Groups",
    "NOQ::Okta::App": "Okta Apps",
    "NOQ::Okta::Group": "Okta Groups",
    "NOQ::Okta::User": "Okta Users",
}


class SlackSupportedActionOption(BaseModel):
    block_generator: Optional[Callable]
    friendly_name: str
    action_id: str
    supported_actions: list[SlackSupportedActionOption] = []


class SlackResourceTypes(BaseModel):
    template_type: str
    friendly_name: str
    action_id: str
    supported_actions: list[SlackSupportedActionOption]


SlackSupportedActionOption.update_forward_refs()

SUPPORTED_RESOURCE_TYPES = []


def create_aws_groups():
    pass


def request_inline_policy():
    # Returns slack blocks for creating an inline policy
    pass


def request_predefined_permissions():
    # Returns slack blocks for requesting predefined permissions
    pass


def create_aws_resource_blocks(resource_type: str):
    # Returns slack blocks for creating an AWS resource
    pass


def delete_aws_resource_blocks(resource_type: str):
    # Returns slack blocks for deleting an AWS resource
    pass


resource_name = "aws_iam_group"
template_type = "NOQ::AWS::IAM::Group"
SUPPORTED_RESOURCE_TYPES.append(
    SlackResourceTypes(
        action_id=f"{resource_name}/menu",
        template_type=template_type,
        friendly_name=FRIENDLY_RESOURCE_TYPE_NAMES[template_type],
        supported_actions=[
            SlackSupportedActionOption(
                action_id=f"{resource_name}/create_group",
                friendly_name="Create Group",
                block_generator=partial(create_aws_resource_blocks, template_type),
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/delete_group",
                friendly_name="Delete Group",
                block_generator=partial(delete_aws_resource_blocks, template_type),
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/add_user",
                friendly_name="Add User to Group",
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/remove_user",
                friendly_name="Remove User from Group",
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/add_permissions",
                friendly_name="Add Permissions",
                supported_actions=[
                    SlackSupportedActionOption(
                        friendly_name="Add Predefined Permissions",
                        action_id=f"{resource_name}/add_permissions/predefined_permissions",
                        block_generator=request_predefined_permissions,
                    ),
                    SlackSupportedActionOption(
                        friendly_name="Request specific permissions (Inline Policy)",
                        action_id=f"{resource_name}/add_permissions/inline_policy",
                        block_generator=request_inline_policy,
                    ),
                    SlackSupportedActionOption(
                        friendly_name="Attach a Managed Policy",
                        action_id=f"{resource_name}/add_permissions/managed_policy",
                    ),
                ],
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/remove_permissions",
                friendly_name="Remove Permissions",
            ),
            SlackSupportedActionOption(
                action_id=f"{resource_name}/remove_unused_permissions",
                friendly_name="Remove Unused Permissions",
            ),
        ],
    )
)

RESOURCE_TYPES = {
    "NOQ::AWS::IAM::Group": {
        "friendly_name": "AWS IAM Groups",
        "supported_actions": {
            "aws_iam_group/create": {
                "friendly_name": "Create Group",
            },
            "aws_iam_group/delete": {
                "friendly_name": "Delete Group",
            },
            "aws_iam_group/add_user": {
                "friendly_name": "Add User to Group",
            },
            "aws_iam_group/remove_user": {
                "friendly_name": "Remove User from Group",
            },
            "aws_iam_group/add_permissions": {
                "friendly_name": "Add Permissions",
            },
            "aws_iam_group/remove_permissions": {
                "friendly_name": "Remove Permissions",
            },
            "aws_iam_group/remove_unused_permissions": {
                "friendly_name": "Remove Unused Permissions",
            },
            "aws_iam_group/perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::AWS::IAM::ManagedPolicy": {
        "friendly_name": "AWS IAM Managed Policies",
        "supported_actions": {
            "create_aws_managed_policy": {
                "friendly_name": "Create Managed Policy",
            },
            "delete_managed_policy": {
                "friendly_name": "Delete Managed Policy",
            },
            "add_aws_permissions": {
                "friendly_name": "Add Permissions",
            },
            "add_update_tags": {
                "friendly_name": "Add/Update Tags",
            },
            "remove_tags": {
                "friendly_name": "Remove Tags",
            },
            "remove_unused_permissions": {
                "friendly_name": "Remove Unused Permissions",
            },
            "perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::AWS::IAM::Role": {
        "friendly_name": "AWS IAM Roles",
        "supported_actions": {
            "create_role": {
                "friendly_name": "Create Role",
            },
            "delete_role": {
                "friendly_name": "Delete Role",
            },
            "add_aws_permissions": {
                "friendly_name": "Add Permissions",
            },
            "remove_aws_permissions": {
                "friendly_name": "Remove Permissions",
            },
            "add_update_tags": {
                "friendly_name": "Add/Update Tags",
            },
            "remove_tags": {
                "friendly_name": "Remove Tags",
            },
            "remove_unused_permissions": {
                "friendly_name": "Remove Unused Permissions",
            },
            "perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::AWS::IAM::User": {
        "friendly_name": "AWS IAM Users",
        "supported_actions": {
            "create_role": {
                "friendly_name": "Create User",
            },
            "delete_role": {
                "friendly_name": "Delete User",
            },
            "add_aws_permissions": {
                "friendly_name": "Add Permissions",
            },
            "remove_aws_permissions": {
                "friendly_name": "Remove Permissions",
            },
            "add_update_tags": {
                "friendly_name": "Add/Update Tags",
            },
            "remove_tags": {
                "friendly_name": "Remove Tags",
            },
            "remove_unused_permissions": {
                "friendly_name": "Remove Unused Permissions",
            },
        },
    },
    "NOQ::AWS::IdentityCenter::PermissionSet": {
        "friendly_name": "AWS Permission Sets",
        "supported_actions": {
            "request_access": {
                "friendly_name": "Request Access",
            },
            "create_permission_set": {
                "friendly_name": "Create Permission Set",
            },
            "delete_permission_set": {
                "friendly_name": "Delete Permission Set",
            },
            "add_aws_permissions": {
                "friendly_name": "Add Permissions",
            },
            "remove_aws_permissions": {
                "friendly_name": "Remove Permissions",
            },
            "add_update_tags": {
                "friendly_name": "Add/Update Tags",
            },
            "remove_tags": {
                "friendly_name": "Remove Tags",
            },
            "remove_unused_permissions": {
                "friendly_name": "Remove Unused Permissions",
            },
        },
    },
    "NOQ::Google::Group": {
        "friendly_name": "Google Groups",
        "supported_actions": {
            "request_access_google_group": {
                "friendly_name": "Request Access to Group",
            },
            "create_google_group": {
                "friendly_name": "Create Group",
            },
            "delete_google_group": {
                "friendly_name": "Delete Group",
            },
            "perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::Okta::App": {
        "friendly_name": "Okta Apps",
        "supported_actions": {
            "request_access_okta_app": {
                "friendly_name": "Request Access to Okta App",
            },
            "create_okta_app": {
                "friendly_name": "Create Okta App",
            },
            "delete_okta_app": {
                "friendly_name": "Delete Okta App",
            },
            "perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::Okta::Group": {
        "friendly_name": "Okta Groups",
        "supported_actions": {
            "request_access_okta_group": {
                "friendly_name": "Request Access to Okta Group",
            },
            "create_okta_group": {
                "friendly_name": "Create Okta Group",
            },
            "delete_okta_group": {
                "friendly_name": "Delete Okta Group",
            },
            "perform_access_review": {
                "friendly_name": "Perform Access Review",
            },
        },
    },
    "NOQ::Okta::User": {
        "friendly_name": "Okta Users",
        "supported_actions": {
            "create_okta_user": {
                "friendly_name": "Create Okta User",
            },
            "delete_okta_user": {
                "friendly_name": "Delete Okta User",
            },
        },
    },
}


class SlackWorkflows:
    def __init__(self, tenant) -> None:
        self.tenant = tenant

    def get_self_service_step_1_blocks(self):
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":wave: Hello! What do you need help with?",
                },
                "block_id": "self-service-select",
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Okta Application",
                                "emoji": True,
                            },
                            "value": "NOQ::Okta::App",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Okta Group Membership",
                                "emoji": True,
                            },
                            "value": "NOQ::Okta::Group",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Google Group Membership",
                                "emoji": True,
                            },
                            "value": "NOQ::Google::Group",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "AWS Credentials",
                                "emoji": True,
                            },
                            "value": "aws-credentials",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "AWS Permissions or Tags",
                                "emoji": True,
                            },
                            "value": "aws-permissions-or-tags",
                        },
                    ],
                    "action_id": "self-service-select",
                },
            },
        ]
        blocks.append(self.get_cancel_button_block())
        return blocks

    def get_self_service_step_1_blocks_v2(self):
        blocks = []
        block_options = []
        for resource_type in SUPPORTED_RESOURCE_TYPES:
            block_options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": resource_type.friendly_name,
                        "emoji": True,
                    },
                    "value": resource_type.template_type,
                },
            )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":wave: Hello! What resource type do you need help with?",
                },
                "block_id": "self-service-select-action",
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True,
                    },
                    "options": block_options,
                    "action_id": "self-service-select-1-action",
                },
            },
        )

        blocks.append(self.get_cancel_button_block())
        return blocks

    def get_self_service_step_2_blocks_v2(self, template_type):
        blocks = []
        block_options = []
        for resource_type in SUPPORTED_RESOURCE_TYPES:
            if resource_type.template_type == template_type:
                for action in resource_type.supported_actions:
                    block_options.append(
                        {
                            "text": {
                                "type": "plain_text",
                                "text": action.friendly_name,
                                "emoji": True,
                            },
                            "value": action.action_id,
                        },
                    )
        if not block_options:
            return None
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "What would you like to do?",
                },
                "block_id": "self-service-select-2-block",
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item",
                        "emoji": True,
                    },
                    "options": block_options,
                    "action_id": "self-service-select-2-action",
                },
            },
        )
        blocks.append(self.get_cancel_button_block())
        # blocks.append(self.get_back_button_block())  # TODO: Need to pass action ID

    def get_select_aws_accounts_block(self, selected_accounts):
        select_accounts_block = {
            "type": "input",
            "block_id": "select_aws_accounts",
            "element": {
                "action_id": "select_aws_accounts",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select AWS Accounts",
                },
                "min_query_length": 0,
            },
            "label": {"type": "plain_text", "text": " ", "emoji": True},
        }

        if selected_accounts is not None:
            select_accounts_block["element"]["initial_options"] = selected_accounts
        return select_accounts_block

    def get_duration_block(self, duration=None):
        blocks = []

        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "How long do you need it for?"},
            }
        )
        duration_block = {
            "type": "input",
            "block_id": "duration",
            "element": {
                "type": "static_select",
                "options": [
                    # TODO: 5 minutes is for quick testing, remove
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "5 Minutes",
                            "emoji": True,
                        },
                        "value": "in 5 minutes",
                    },
                    {
                        "text": {"type": "plain_text", "text": "1 Hour", "emoji": True},
                        "value": "in 1 hour",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "2 Hours",
                            "emoji": True,
                        },
                        "value": "in 2 hours",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "4 Hours",
                            "emoji": True,
                        },
                        "value": "in 4 hours",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "8 Hours",
                            "emoji": True,
                        },
                        "value": "in 8 hours",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "24 Hours",
                            "emoji": True,
                        },
                        "value": "in 1 day",
                    },
                    {
                        "text": {"type": "plain_text", "text": "3 Days", "emoji": True},
                        "value": "in 3 days",
                    },
                    {
                        "text": {"type": "plain_text", "text": "1 Week", "emoji": True},
                        "value": "in 1 Week",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Month",
                            "emoji": True,
                        },
                        "value": "in 1 Month",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Forever",
                            "emoji": True,
                        },
                        "value": "no_expire",
                    },
                ],
                "action_id": "duration",
            },
            "label": {"type": "plain_text", "text": " ", "emoji": True},
        }

        if duration is not None:
            selected_block = None
            for block in duration_block["element"]["options"]:
                if block["value"] == duration:
                    selected_block = block
                    break
            duration_block["element"]["initial_option"] = selected_block
        blocks.append(duration_block)
        return blocks

    def get_select_resources_block(self, resource_type, selected_resources=None):
        friendly_resource_type_name = FRIENDLY_RESOURCE_TYPE_NAMES.get(
            resource_type, resource_type
        )
        select_resources_block = {
            "type": "input",
            "block_id": "select_resources",
            "element": {
                "action_id": f"select_resources/{resource_type}",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": f"Select {friendly_resource_type_name}",
                },
                "min_query_length": 2,
            },
            "label": {"type": "plain_text", "text": " ", "emoji": True},
        }

        if selected_resources is not None:
            select_resources_block["element"]["initial_options"] = selected_resources
        return select_resources_block

    def get_justification_block(self, justification=None):
        justification_block = {
            "type": "input",
            "block_id": "justification",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "justification",
                "placeholder": {"type": "plain_text", "text": "I need access for..."},
            },
            "label": {"type": "plain_text", "text": " ", "emoji": True},
        }
        if justification is not None:
            justification_block["element"]["initial_value"] = justification
        return justification_block

    def get_cancel_button_block(self):
        return {
            "type": "actions",
            "block_id": "cancel_button_block",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel", "emoji": True},
                    "value": "cancel_request",
                    "style": "danger",
                    "action_id": "cancel_request",
                }
            ],
        }

    def get_back_button_block(self, action_id):
        return {
            "type": "actions",
            "block_id": "cancel_button_block",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel", "emoji": True},
                    "value": action_id,
                    "action_id": action_id,
                }
            ],
        }

    def generate_self_service_request_aws_credentials_step_2_option_selection(
        self,
        resource_type,
        update=False,
        selected_resources=None,
        selected_accounts=None,
        duration=None,
        justification=None,
        request_id=None,
    ):
        friendly_resource_type_name = FRIENDLY_RESOURCE_TYPE_NAMES.get(
            resource_type, resource_type
        )
        elements = []
        submit_verbiage = "Create my request" if not update else "Update request"
        elements.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Which {friendly_resource_type_name} would you like access to?",
                },
            }
        )

        select_resources_block = self.get_select_resources_block(
            resource_type, selected_resources
        )
        elements.append(select_resources_block)

        select_accounts_block = self.get_select_aws_accounts_block(selected_accounts)
        elements.append(select_accounts_block)

        duration_block = self.get_duration_block(duration)
        elements.extend(duration_block)
        justification_block = self.get_justification_block(justification)
        elements.append(justification_block)

        create_update_request_str = "create_access_request"
        if update:
            create_update_request_str = f"update_access_request/{request_id}"
        elements.append(
            {
                "type": "actions",
                "block_id": "create_button_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": submit_verbiage,
                            "emoji": True,
                        },
                        "value": create_update_request_str,
                        "action_id": create_update_request_str,
                    }
                ],
            }
        )
        elements.append(self.get_cancel_button_block())
        return elements

    def generate_self_service_step_2_app_group_access(
        self,
        resource_type,
        selected_options=None,
        justification=None,
        duration=None,
        update=False,
        message_ts=None,
        channel_id=None,
        branch_name=None,
        pull_request_id=None,
        user_email=None,
        request_id=None,
    ) -> list[dict]:
        friendly_resource_type_name = FRIENDLY_RESOURCE_TYPE_NAMES.get(
            resource_type, resource_type
        )
        elements = []
        submit_verbiage = "Create my request" if not update else "Update request"

        elements.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Which {friendly_resource_type_name} would you like access to?",
                },
            }
        )

        select_resources_block = self.get_select_resources_block(
            resource_type, selected_options
        )
        elements.append(select_resources_block)

        duration_block = self.get_duration_block(duration)
        elements.extend(duration_block)
        elements.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Why do you need it?"},
            }
        )

        justification_block = self.get_justification_block(justification)
        elements.append(justification_block)

        create_update_request_str = "create_access_request"
        if update:
            create_update_request_str = f"update_access_request/{request_id}"
        elements.append(
            {
                "type": "actions",
                "block_id": "create_button_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": submit_verbiage,
                            "emoji": True,
                        },
                        "value": create_update_request_str,
                        "action_id": create_update_request_str,
                    }
                ],
            }
        )
        elements.append(self.get_cancel_button_block())

        return elements

    def select_predefined_policy_blocks(
        self,
        selected_identities=None,
        selected_predefined_policy=None,
        selected_resources=None,
        selected_permissions=None,
        selected_duration=None,
        justification=None,
        request_id=None,
        update=False,
    ):
        # submit_verbiage = "Create my request" if not update else "Update request"

        elements = []

        # select_identities_block = {
        #     "type": "section",
        #     "block_id": "select_identities",
        #     "text": {"type": "mrkdwn", "text": "*Identities*"},
        #     "accessory": {
        #         "action_id": "select_identities_action",
        #         "type": "multi_external_select",
        #         "placeholder": {"type": "plain_text", "text": "Select identities"},
        #         "min_query_length": 3,
        #     },
        # }

        # if selected_identities:
        #     select_identities_block["accessory"][
        #         "initial_options"
        #     ] = selected_identities
        # elements.append(select_identities_block)

        selected_predefined_policy_block = {
            "type": "section",
            "block_id": "select_aws_predefined_policies",
            "text": {"type": "mrkdwn", "text": "*Pre-defined Policy*"},
            "accessory": {
                "action_id": "select_aws_predefined_policies",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select Pre-defined Policies",
                },
                "min_query_length": 1,
            },
        }
        if selected_predefined_policy:
            selected_predefined_policy_block["accessory"][
                "initial_options"
            ] = selected_predefined_policy
        elements.append(selected_predefined_policy_block)

        # duration_block = self.get_duration_block(selected_duration)

        # elements.extend(duration_block)

        # justification_block = self.get_justification_block(justification)
        # elements.append(justification_block)

        # create_update_request_str = "create_cloud_predefined_policy_request"
        # if update:
        #     create_update_request_str = (
        #         f"update_cloud_predefined_policy_request/{request_id}"
        #     )

        # elements.append(
        #     {
        #         "type": "actions",
        #         "block_id": "create_button_block",
        #         "elements": [
        #             {
        #                 "type": "button",
        #                 "text": {
        #                     "type": "plain_text",
        #                     "text": submit_verbiage,
        #                     "emoji": True,
        #                 },
        #                 "value": create_update_request_str,  # "request_cloud_permissions_to_resources",
        #                 "action_id": create_update_request_str,  # "request_cloud_permissions_to_resources",
        #             }
        #         ],
        #     }
        # )

        elements.append(self.get_cancel_button_block())

        return elements

    def select_desired_permissions_blocks(
        self,
        selected_identities=None,
        selected_services=None,
        selected_resources=None,
        selected_permissions=None,
        selected_duration=None,
        justification=None,
        request_id=None,
        update=False,
    ):
        submit_verbiage = "Create my request" if not update else "Update request"

        elements = []

        select_identities_block = {
            "type": "section",
            "block_id": "select_identities",
            "text": {"type": "mrkdwn", "text": "*Identities*"},
            "accessory": {
                "action_id": "select_identities_action",
                "type": "multi_external_select",
                "placeholder": {"type": "plain_text", "text": "Select identities"},
                "min_query_length": 3,
            },
        }

        if selected_identities:
            select_identities_block["accessory"][
                "initial_options"
            ] = selected_identities
        elements.append(select_identities_block)

        selected_services_block = {
            "type": "section",
            "block_id": "select_services",
            "text": {"type": "mrkdwn", "text": "*Services*"},
            "accessory": {
                "action_id": "select_aws_services_action",
                "type": "multi_external_select",
                "placeholder": {"type": "plain_text", "text": "Select AWS services"},
                "min_query_length": 1,
            },
        }
        if selected_services:
            selected_services_block["accessory"]["initial_options"] = selected_services
        elements.append(selected_services_block)

        select_resources_block = {
            "type": "section",
            "block_id": "select_resources",
            "text": {"type": "mrkdwn", "text": "*Resources*"},
            "accessory": {
                "action_id": "select_aws_resources_action",
                "type": "multi_external_select",
                "placeholder": {"type": "plain_text", "text": "Select resources"},
                "min_query_length": 1,
            },
        }
        if selected_resources:
            select_resources_block["accessory"]["initial_options"] = selected_resources

        elements.append(select_resources_block)

        desired_permissions_block = {
            "type": "input",
            "block_id": "desired_permissions",
            "element": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select Permissions",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "List", "emoji": True},
                        "value": "List",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Read", "emoji": True},
                        "value": "Read",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Write", "emoji": True},
                        "value": "Write",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Permissions Management",
                            "emoji": True,
                        },
                        "value": "Permissions management",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Tagging",
                            "emoji": True,
                        },
                        "value": "Tagging",
                    },
                ],
                "action_id": "desired_permissions_action",
            },
            "label": {
                "type": "plain_text",
                "text": "Desired Permissions",
                "emoji": True,
            },
        }

        if selected_permissions:
            desired_permissions_block["element"][
                "initial_options"
            ] = selected_permissions

        elements.append(desired_permissions_block)

        duration_block = self.get_duration_block(selected_duration)

        elements.extend(duration_block)

        justification_block = {
            "type": "input",
            "block_id": "justification",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "justification",
                "placeholder": {"type": "plain_text", "text": "I need access for..."},
            },
            "label": {"type": "plain_text", "text": "Justification", "emoji": True},
        }

        if justification:
            justification_block["element"]["initial_value"] = justification
        elements.append(justification_block)

        create_update_request_str = "create_cloud_permissions_request"
        if update:
            create_update_request_str = f"update_cloud_permissions_request/{request_id}"

        elements.append(
            {
                "type": "actions",
                "block_id": "create_button_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": submit_verbiage,
                            "emoji": True,
                        },
                        "value": create_update_request_str,  # "request_cloud_permissions_to_resources",
                        "action_id": create_update_request_str,  # "request_cloud_permissions_to_resources",
                    }
                ],
            }
        )

        elements.append(self.get_cancel_button_block())

        return elements

    def generate_update_or_remove_tags_blocks(
        self,
        update: bool = False,
        request_id: Optional[str] = None,
    ):
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Select one or more cloud identities to update tags:",
                },
            },
            {
                "type": "section",
                "block_id": "select_identities",
                "text": {"type": "mrkdwn", "text": "*Identities*"},
                "accessory": {
                    "action_id": "select_identities_action",
                    "type": "multi_external_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select identities",
                    },
                    "min_query_length": 3,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Do you want to add/update or remove tags?",
                },
            },
            {
                "type": "input",
                "block_id": "tag_action",
                "element": {
                    "type": "radio_buttons",
                    "action_id": "tag_action",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Add/Update",
                                "emoji": True,
                            },
                            "value": "create_update",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Remove",
                                "emoji": True,
                            },
                            "value": "remove",
                        },
                    ],
                },
                "label": {
                    "type": "plain_text",
                    "text": "Tag Action",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "tag_key_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "tag_key_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter the Tag Key",
                        "emoji": True,
                    },
                },
                "label": {"type": "plain_text", "text": "Tag Key", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "tag_value_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "tag_value_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter the Tag Value",
                        "emoji": True,
                    },
                },
                "label": {"type": "plain_text", "text": "Tag Value", "emoji": True},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "justification",
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "justification",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "I need access for...",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Justification",
                    "emoji": True,
                },
            },
        ]
        create_update_request_str = "create_update_tag_request"
        if update:
            create_update_request_str = f"create_update_tag_request/{request_id}"

        blocks.append(
            {
                "type": "actions",
                "block_id": "create_button_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Create Request",
                            "emoji": True,
                        },
                        "value": create_update_request_str,
                        "action_id": create_update_request_str,
                    }
                ],
            }
        )
        blocks.append(self.get_cancel_button_block())
        return blocks

    def self_service_request_permissions_step_2_option_selection(self):
        blocks = [
            {
                "type": "input",
                "block_id": "self_service_permissions_step_2_block",
                "element": {
                    "type": "radio_buttons",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Pre-defined Policy",
                                "emoji": True,
                            },
                            "value": "select_predefined_policy",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Inline Policy",
                                "emoji": True,
                            },
                            "value": "update_inline_policies",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Managed Policy",
                                "emoji": True,
                            },
                            "value": "update_managed_policies",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Tags",
                                "emoji": True,
                            },
                            "value": "update_tags",
                        },
                    ],
                    "action_id": "self_service_request_permissions_step_2_option_selection",
                },
                "label": {
                    "type": "plain_text",
                    "text": "What type of permissions change would you like?",
                    "emoji": True,
                },
            },
        ]
        blocks.append(self.get_cancel_button_block())
        return blocks

    def get_self_service_submission_success_blocks(
        self, permalink: str, updated: bool = False
    ):
        submit_string = "submitted" if not updated else "updated"
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Your request has been successfully {submit_string}. Click <{permalink}|*here*> to see more details.",
                },
            },
        ]

    def self_service_permissions_review_blocks(
        self,
        requester,
        identities,
        # services,
        # resources,
        # permissions,
        raw_duration,
        reviewers,
        justification,
        pull_request_url,
        branch_name,
        request_id,
        user_email,
    ):
        duration = raw_duration
        if raw_duration == "no_expire":
            duration = "Never"

        identities_text = ""
        for identity_type, identity_names in identities.items():
            identity_type = identity_type.replace("NOQ::", "").replace("::", " ")
            identities_text += f"{identity_type}: {', '.join(identity_names)}\n"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "A cloud permissions request is awaiting your review. "
                        f"View the full request here: {pull_request_url}."
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n <@{requester}>"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Requested Identities:*\n {identities_text}",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Expiration:*\n {duration}",
                    },
                    {"type": "mrkdwn", "text": f"*Reviewers:*\n {reviewers}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Justification:*\n {justification}",
                },
            },
            {
                "type": "actions",
                "block_id": "review_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": "Approve",
                        },
                        "style": "primary",
                        "value": "approve",
                        "action_id": "approve_request",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "emoji": True, "text": "Deny"},
                        "style": "danger",
                        "value": "deny",
                        "action_id": "deny_request",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": ":gear: Edit",
                        },
                        "style": "primary",
                        "value": "edit",
                        "action_id": f"update_permissions_request/{request_id}",
                    },
                ],
            },
        ]

    def self_service_access_review_blocks(
        self,
        requester,
        resources,
        raw_duration,
        reviewers,
        justification,
        pull_request_url,
        branch_name,
        request_id,
        user_email,
    ):
        duration = raw_duration
        if raw_duration == "no_expire":
            duration = "Never"

        resource_text = ""
        for resource_type, resource_names in resources.items():
            resource_type = resource_type.replace("NOQ::", "").replace("::", " ")
            resource_text += f"{resource_type}: {', '.join(resource_names)}\n"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "An access request is awaiting your review. "
                        f"View the full request here: {pull_request_url}."
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n <@{requester}>"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Requested Resources:*\n {resource_text}",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Expiration:*\n {duration}",
                    },
                    {"type": "mrkdwn", "text": f"*Reviewers:*\n {reviewers}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Justification:*\n {justification}",
                },
            },
            {
                "type": "actions",
                "block_id": "review_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": "Approve",
                        },
                        "style": "primary",
                        "value": "approve",
                        "action_id": "approve_request",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "emoji": True, "text": "Deny"},
                        "style": "danger",
                        "value": "deny",
                        "action_id": "deny_request",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": ":gear: Edit",
                        },
                        "style": "primary",
                        "value": "edit",
                        "action_id": f"update_permissions_request/{request_id}",
                    },
                ],
            },
        ]


# request_access_to_resource_block = json.loads(
#     """
# {
#     "type": "modal",
#     "callback_id": "request_access_to_resource",
#     "title": {
#         "type": "plain_text",
#         "text": "Noq",
#         "emoji": true
#     },
#     "submit": {
#         "type": "plain_text",
#         "text": "Submit Request",
#         "emoji": true
#     },
#     "close": {
#         "type": "plain_text",
#         "text": "Cancel",
#         "emoji": true
#     },
#     "blocks": [
#         {
#             "type": "section",
#             "text": {
#                 "type": "mrkdwn",
#                 "text": "*Select an App*"
#             }
#         },
#         {
#             "type": "actions",
#             "block_id": "app_block",
#             "elements": [
#                 {
#                     "type": "static_select",
#                     "action_id": "select_app_type",
#                     "options": [
#                         {
#                             "text": {
#                                 "type": "plain_text",
#                                 "text": "Okta Apps",
#                                 "emoji": true
#                             },
#                             "value": "NOQ::Okta::App"
#                         },
#                         {
#                             "text": {
#                                 "type": "plain_text",
#                                 "text": "Okta Groups",
#                                 "emoji": true
#                             },
#                             "value": "NOQ::Okta::Group"
#                         },
#                         {
#                             "text": {
#                                 "type": "plain_text",
#                                 "text": "AWS Identity Center Permission Sets",
#                                 "emoji": true
#                             },
#                             "value": "NOQ::AWS::IdentityCenter::PermissionSet"
#                         },
#                         {
#                             "text": {
#                                 "type": "plain_text",
#                                 "text": "AWS IAM Roles",
#                                 "emoji": true
#                             },
#                             "value": "NOQ::AWS::IAM::Role"
#                         },
#                         {
#                             "text": {
#                                 "type": "plain_text",
#                                 "text": "Google Groups",
#                                 "emoji": true
#                             },
#                             "value": "NOQ::Google::Group"
#                         }
#                     ]
#                 }
#             ]
#         },
#         {
#             "type": "section",
#             "block_id": "request_access",
#             "text": {
#                 "type": "mrkdwn",
#                 "text": "*Request Access to one or more resources*"
#             },
#             "accessory": {
#                 "action_id": "select_resources",
#                 "type": "multi_external_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Select resources"
#                 },
#                 "min_query_length": 2
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "duration",
#             "element": {
#                 "type": "static_select",
#                 "options": [
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "1 Hour",
#                             "emoji": true
#                         },
#                         "value": "in 1 hour"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "2 Hours",
#                             "emoji": true
#                         },
#                         "value": "in 2 hours"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "4 Hours",
#                             "emoji": true
#                         },
#                         "value": "in 4 hours"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "8 Hours",
#                             "emoji": true
#                         },
#                         "value": "in 8 hours"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "24 Hours",
#                             "emoji": true
#                         },
#                         "value": "in 1 day"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "3 Days",
#                             "emoji": true
#                         },
#                         "value": "in 3 days"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "1 Week",
#                             "emoji": true
#                         },
#                         "value": "in 1 Week"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "1 Month",
#                             "emoji": true
#                         },
#                         "value": "in 1 Month"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Never",
#                             "emoji": true
#                         },
#                         "value": "no_expire"
#                     }
#                 ],
#                 "action_id": "duration"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Expiration",
#                 "emoji": true
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "justification",
#             "element": {
#                 "type": "plain_text_input",
#                 "multiline": true,
#                 "action_id": "justification",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "I need access for..."
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Justification",
#                 "emoji": true
#             }
#         }
#     ]
# }
# """
# )


# remove_unused_identities_sample = [
#     {
#         "type": "section",
#         "text": {
#             "type": "plain_text",
#             "text": "Cloud identities associated with your team have not been used in the past 180 days. Please review these identities and let us know which action to take.",
#             "emoji": True,
#         },
#     },
#     {
#         "type": "section",
#         "text": {
#             "type": "mrkdwn",
#             "text": "<fakeLink.toNoqRole.com|prod: role/LemurApp> ",
#         },
#         "accessory": {
#             "type": "static_select",
#             "placeholder": {
#                 "type": "plain_text",
#                 "text": "Ignore (Do not Delete)",
#                 "emoji": True,
#             },
#             "options": [
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Ignore Forever (Do not Delete)",
#                         "emoji": True,
#                     },
#                     "value": "ignore",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Delete Immediately",
#                         "emoji": True,
#                     },
#                     "value": "delete",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Re-assign to a different team",
#                         "emoji": True,
#                     },
#                     "value": "reassign",
#                 },
#             ],
#             "action_id": "static_select-action",
#         },
#     },
#     {
#         "type": "section",
#         "text": {
#             "type": "mrkdwn",
#             "text": "<fakeLink.toNoqRole.com|test: role/teleport> ",
#         },
#         "accessory": {
#             "type": "static_select",
#             "placeholder": {
#                 "type": "plain_text",
#                 "text": "Ignore (Do not Delete)",
#                 "emoji": True,
#             },
#             "options": [
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Ignore Forever (Do not Delete)",
#                         "emoji": True,
#                     },
#                     "value": "ignore",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Delete Immediately",
#                         "emoji": True,
#                     },
#                     "value": "delete",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Re-assign to a different team",
#                         "emoji": True,
#                     },
#                     "value": "reassign",
#                 },
#             ],
#             "action_id": "static_select-action",
#         },
#     },
#     {
#         "type": "section",
#         "text": {
#             "type": "mrkdwn",
#             "text": "<fakeLink.toNoqRole.com|staging: role/Nonerole> ",
#         },
#         "accessory": {
#             "type": "static_select",
#             "placeholder": {
#                 "type": "plain_text",
#                 "text": "Ignore (Do not Delete)",
#                 "emoji": True,
#             },
#             "options": [
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Ignore Forever (Do not Delete)",
#                         "emoji": True,
#                     },
#                     "value": "ignore",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Delete Immediately",
#                         "emoji": True,
#                     },
#                     "value": "delete",
#                 },
#                 {
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Re-assign to a different team",
#                         "emoji": True,
#                     },
#                     "value": "reassign",
#                 },
#             ],
#             "action_id": "static_select-action",
#         },
#     },
#     {"type": "divider"},
#     {
#         "type": "actions",
#         "elements": [
#             {
#                 "type": "button",
#                 "text": {"type": "plain_text", "text": "Submit", "emoji": True},
#                 "value": "submit",
#                 "action_id": "submit",
#             }
#         ],
#     },
# ]


# unauthorized_change_sample = [
#     {
#         "type": "section",
#         "text": {
#             "type": "mrkdwn",
#             "text": "An unauthorized Cloud Identity Modification was detected and automatically remediated.\n\n*<fakeLink.toEmployeeProfile.com|Click here to view CloudTrail Logs>*",
#         },
#     },
#     {
#         "type": "section",
#         "fields": [
#             {
#                 "type": "mrkdwn",
#                 "text": "*Identity:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/effective_permissions_demo_role>",
#             },
#             {"type": "mrkdwn", "text": "*Action:*\tiam:attachrolepolicy"},
#             {
#                 "type": "mrkdwn",
#                 "text": "*Actor:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/prod_admin>",
#             },
#             {
#                 "type": "mrkdwn",
#                 "text": "*Policy Details:*\t<fakeLink.toPolicy.com|arn:aws:iam::aws:policy/AdministratorAccess>",
#             },
#             {"type": "mrkdwn", "text": "*Session Name:*\tcurtis@noq.dev"},
#         ],
#     },
#     {
#         "type": "actions",
#         "elements": [
#             {
#                 "type": "button",
#                 "text": {
#                     "type": "plain_text",
#                     "emoji": True,
#                     "text": "Approve and Submit Request",
#                 },
#                 "style": "primary",
#                 "value": "click_me_123",
#             },
#             {
#                 "type": "button",
#                 "text": {"type": "plain_text", "emoji": True, "text": "Ignore"},
#                 "style": "danger",
#                 "value": "click_me_123",
#             },
#         ],
#     },
# ]


# request_access_to_resource_success = json.loads(
#     """{
#     "type": "modal",
#     "title": {
#         "type": "plain_text",
#         "text": "Noq",
#         "emoji": true
#     },
#     "close": {
#         "type": "plain_text",
#         "text": "Close",
#         "emoji": true
#     },
#     "blocks": [
#         {
#             "type": "section",
#             "text": {
#                 "type": "plain_text",
#                 "text": "Submitting request... Please wait.",
#                 "emoji": true
#             }
#         }
#     ]
# }"""
# )


# def select_desired_permissions_message():
#     return [
#         {
#             "type": "section",
#             "block_id": "select_identities",
#             "text": {"type": "mrkdwn", "text": "*Identities*"},
#             "accessory": {
#                 "action_id": "select_identities_action",
#                 "type": "multi_external_select",
#                 "placeholder": {"type": "plain_text", "text": "Select identities"},
#                 "min_query_length": 3,
#             },
#         },
#         {
#             "type": "section",
#             "block_id": "select_services",
#             "text": {"type": "mrkdwn", "text": "*Services*"},
#             "accessory": {
#                 "action_id": "select_aws_services_action",
#                 "type": "multi_external_select",
#                 "placeholder": {"type": "plain_text", "text": "Select AWS services"},
#                 "min_query_length": 1,
#             },
#         },
#         {
#             "type": "section",
#             "block_id": "select_resources",
#             "text": {"type": "mrkdwn", "text": "*Resources*"},
#             "accessory": {
#                 "action_id": "select_aws_resources_action",
#                 "type": "multi_external_select",
#                 "placeholder": {"type": "plain_text", "text": "Select resources"},
#                 "min_query_length": 1,
#             },
#         },
#         {
#             "type": "input",
#             "block_id": "desired_permissions",
#             "element": {
#                 "type": "multi_static_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Select Permissions",
#                     "emoji": True,
#                 },
#                 "options": [
#                     {
#                         "text": {"type": "plain_text", "text": "List", "emoji": True},
#                         "value": "List",
#                     },
#                     {
#                         "text": {"type": "plain_text", "text": "Read", "emoji": True},
#                         "value": "Read",
#                     },
#                     {
#                         "text": {"type": "plain_text", "text": "Write", "emoji": True},
#                         "value": "Write",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Permissions Management",
#                             "emoji": True,
#                         },
#                         "value": "Permissions management",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Tagging",
#                             "emoji": True,
#                         },
#                         "value": "Tagging",
#                     },
#                 ],
#                 "action_id": "desired_permissions_action",
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Desired Permissions",
#                 "emoji": True,
#             },
#         },
#         {
#             "type": "input",
#             "block_id": "duration",
#             "element": {
#                 "type": "static_select",
#                 "options": [
#                     {
#                         "text": {"type": "plain_text", "text": "1 Hour", "emoji": True},
#                         "value": "in 1 hour",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "2 Hours",
#                             "emoji": True,
#                         },
#                         "value": "in 2 hours",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "4 Hours",
#                             "emoji": True,
#                         },
#                         "value": "in 4 hours",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "8 Hours",
#                             "emoji": True,
#                         },
#                         "value": "in 8 hours",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "24 Hours",
#                             "emoji": True,
#                         },
#                         "value": "in 1 day",
#                     },
#                     {
#                         "text": {"type": "plain_text", "text": "3 Days", "emoji": True},
#                         "value": "in 3 days",
#                     },
#                     {
#                         "text": {"type": "plain_text", "text": "1 Week", "emoji": True},
#                         "value": "in 1 Week",
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "1 Month",
#                             "emoji": True,
#                         },
#                         "value": "in 1 Month",
#                     },
#                     {
#                         "text": {"type": "plain_text", "text": "Never", "emoji": True},
#                         "value": "no_expire",
#                     },
#                 ],
#                 "action_id": "duration",
#             },
#             "label": {"type": "plain_text", "text": "Expiration", "emoji": True},
#         },
#         {
#             "type": "input",
#             "block_id": "justification",
#             "element": {
#                 "type": "plain_text_input",
#                 "multiline": True,
#                 "action_id": "justification",
#                 "placeholder": {"type": "plain_text", "text": "I need access for..."},
#             },
#             "label": {"type": "plain_text", "text": "Justification", "emoji": True},
#         },
#     ]


# self_service_step_1_option_selection = json.loads(
#     """{
#     "type": "modal",
#     "callback_id": "self_service_step_1",
#     "title": {
#         "type": "plain_text",
#         "text": "Noq",
#         "emoji": true
#     },
#     "submit": {
#         "type": "plain_text",
#         "text": "Next",
#         "emoji": true
#     },
#     "close": {
#         "type": "plain_text",
#         "text": "Cancel",
#         "emoji": true
#     },
#     "blocks": [
#         {
#             "type": "input",
#             "block_id": "self_service_step_1_block",
#             "element": {
#                 "type": "radio_buttons",
#                 "options": [
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Request access to an application, group, or AWS permission set",
#                             "emoji": true
#                         },
#                         "value": "request_access_to_identity"
#                     },
#                     {
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Request Permission or tag changes to a cloud identity",
#                             "emoji": true
#                         },
#                         "value": "request_permissions_for_identity"
#                     }
#                 ],
#                 "action_id": "self_service_step_1_option_selection"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "What would you like to do?",
#                 "emoji": true
#             }
#         }
#     ]
# }"""
# )


# self_service_submission_success = """
# {
#   "type": "modal",
#   "callback_id": "request_success",
#   "title": {
#     "type": "plain_text",
#     "text": "Request Successful"
#   },
#   "blocks": [
#     {
#       "type": "section",
#       "text": {
#         "type": "mrkdwn",
#         "text": "Your request has been successfully submitted. Click the link below to view more details:"
#       }
#     },
#     {
#       "type": "section",
#       "block_id": "view_details_section",
#       "text": {
#         "type": "mrkdwn",
#         "text": "{{pull_request_url}}"
#       }
#     }
#   ],
#   "submit": {
#     "type": "plain_text",
#     "text": "Close"
#   }
# }
# """
