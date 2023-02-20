from typing import Any, Dict

import ujson as json
from humanfriendly import format_timespan

request_permissions_to_resource_block = None  # TODO

friendly_resource_type_names = {
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

request_access_to_resource_block = json.loads(
    """
{
    "type": "modal",
    "callback_id": "request_access_to_resource",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "submit": {
        "type": "plain_text",
        "text": "Submit Request",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Select an App*"
            }
        },
        {
            "type": "actions",
            "block_id": "app_block",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_app_type",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Okta Apps",
                                "emoji": true
                            },
                            "value": "NOQ::Okta::App"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Okta Groups",
                                "emoji": true
                            },
                            "value": "NOQ::Okta::Group"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "AWS Identity Center Permission Sets",
                                "emoji": true
                            },
                            "value": "NOQ::AWS::IdentityCenter::PermissionSet"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "AWS IAM Roles",
                                "emoji": true
                            },
                            "value": "NOQ::AWS::IAM::Role"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Google Groups",
                                "emoji": true
                            },
                            "value": "NOQ::Google::Group"
                        }
                    ]
                }
            ]
        },
        {
            "type": "section",
            "block_id": "request_access",
            "text": {
                "type": "mrkdwn",
                "text": "*Request Access to one or more resources*"
            },
            "accessory": {
                "action_id": "select_resources",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select resources"
                },
                "min_query_length": 2
            }
        },
        {
            "type": "input",
            "block_id": "duration",
            "element": {
                "type": "static_select",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Hour",
                            "emoji": true
                        },
                        "value": "in 1 hour"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "2 Hours",
                            "emoji": true
                        },
                        "value": "in 2 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "4 Hours",
                            "emoji": true
                        },
                        "value": "in 4 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "8 Hours",
                            "emoji": true
                        },
                        "value": "in 8 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "24 Hours",
                            "emoji": true
                        },
                        "value": "in 1 day"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "3 Days",
                            "emoji": true
                        },
                        "value": "in 3 days"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Week",
                            "emoji": true
                        },
                        "value": "in 1 Week"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Month",
                            "emoji": true
                        },
                        "value": "in 1 Month"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Never",
                            "emoji": true
                        },
                        "value": "no_expire"
                    }
                ],
                "action_id": "duration"
            },
            "label": {
                "type": "plain_text",
                "text": "Expiration",
                "emoji": true
            }
        },
        {
            "type": "input",
            "block_id": "justification",
            "element": {
                "type": "plain_text_input",
                "multiline": true,
                "action_id": "justification",
                "placeholder": {
                    "type": "plain_text",
                    "text": "I need access for..."
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Justification",
                "emoji": true
            }
        }
    ]
}
"""
)


remove_unused_identities_sample = [
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "Cloud identities associated with your team have not been used in the past 180 days. Please review these identities and let us know which action to take.",
            "emoji": True,
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "<fakeLink.toNoqRole.com|prod: role/LemurApp> ",
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Ignore (Do not Delete)",
                "emoji": True,
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Ignore Forever (Do not Delete)",
                        "emoji": True,
                    },
                    "value": "ignore",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Delete Immediately",
                        "emoji": True,
                    },
                    "value": "delete",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Re-assign to a different team",
                        "emoji": True,
                    },
                    "value": "reassign",
                },
            ],
            "action_id": "static_select-action",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "<fakeLink.toNoqRole.com|test: role/teleport> ",
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Ignore (Do not Delete)",
                "emoji": True,
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Ignore Forever (Do not Delete)",
                        "emoji": True,
                    },
                    "value": "ignore",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Delete Immediately",
                        "emoji": True,
                    },
                    "value": "delete",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Re-assign to a different team",
                        "emoji": True,
                    },
                    "value": "reassign",
                },
            ],
            "action_id": "static_select-action",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "<fakeLink.toNoqRole.com|staging: role/Nonerole> ",
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Ignore (Do not Delete)",
                "emoji": True,
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Ignore Forever (Do not Delete)",
                        "emoji": True,
                    },
                    "value": "ignore",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Delete Immediately",
                        "emoji": True,
                    },
                    "value": "delete",
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Re-assign to a different team",
                        "emoji": True,
                    },
                    "value": "reassign",
                },
            ],
            "action_id": "static_select-action",
        },
    },
    {"type": "divider"},
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Submit", "emoji": True},
                "value": "submit",
                "action_id": "submit",
            }
        ],
    },
]


unauthorized_change_sample = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "An unauthorized Cloud Identity Modification was detected and automatically remediated.\n\n*<fakeLink.toEmployeeProfile.com|Click here to view CloudTrail Logs>*",
        },
    },
    {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": "*Identity:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/effective_permissions_demo_role>",
            },
            {"type": "mrkdwn", "text": "*Action:*\tiam:attachrolepolicy"},
            {
                "type": "mrkdwn",
                "text": "*Actor:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/prod_admin>",
            },
            {
                "type": "mrkdwn",
                "text": "*Policy Details:*\t<fakeLink.toPolicy.com|arn:aws:iam::aws:policy/AdministratorAccess>",
            },
            {"type": "mrkdwn", "text": "*Session Name:*\tcurtis@noq.dev"},
        ],
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "emoji": True,
                    "text": "Approve and Submit Request",
                },
                "style": "primary",
                "value": "click_me_123",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "Ignore"},
                "style": "danger",
                "value": "click_me_123",
            },
        ],
    },
]


request_access_to_resource_success = json.loads(
    """{
    "type": "modal",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Close",
        "emoji": true
    },
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "Submitting request... Please wait.",
                "emoji": true
            }
        }
    ]
}"""
)

select_desired_permissions_modal = json.loads(
    """
{
    "type": "modal",
    "callback_id": "request_cloud_permissions_to_resources",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "submit": {
        "type": "plain_text",
        "text": "Submit Request",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "blocks": [
        {
            "type": "section",
            "block_id": "select_identities",
            "text": {
                "type": "mrkdwn",
                "text": "*Identities*"
            },
            "accessory": {
                "action_id": "select_identities_action",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select identities"
                },
                "min_query_length": 3
            }
        },
        {
            "type": "section",
            "block_id": "select_services",
            "text": {
                "type": "mrkdwn",
                "text": "*Services*"
            },
            "accessory": {
                "action_id": "select_aws_services_action",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select AWS services"
                },
                "min_query_length": 1
            }
        },
        {
            "type": "section",
            "block_id": "select_resources",
            "text": {
                "type": "mrkdwn",
                "text": "*Resources*"
            },
            "accessory": {
                "action_id": "select_aws_resources_action",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select resources"
                },
                "min_query_length": 1
            }
        },
        {
            "type": "input",
            "block_id": "desired_permissions",
            "element": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select Permissions",
                    "emoji": true
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "List",
                            "emoji": true
                        },
                        "value": "List"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Read",
                            "emoji": true
                        },
                        "value": "Read"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Write",
                            "emoji": true
                        },
                        "value": "Write"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Permissions Management",
                            "emoji": true
                        },
                        "value": "Permissions management"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Tagging",
                            "emoji": true
                        },
                        "value": "Tagging"
                    }
                ],
                "action_id": "desired_permissions_action"
            },
            "label": {
                "type": "plain_text",
                "text": "Desired Permissions",
                "emoji": true
            }
        },
        {
            "type": "input",
            "block_id": "duration",
            "element": {
                "type": "static_select",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Hour",
                            "emoji": true
                        },
                        "value": "in 1 hour"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "2 Hours",
                            "emoji": true
                        },
                        "value": "in 2 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "4 Hours",
                            "emoji": true
                        },
                        "value": "in 4 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "8 Hours",
                            "emoji": true
                        },
                        "value": "in 8 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "24 Hours",
                            "emoji": true
                        },
                        "value": "in 1 day"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "3 Days",
                            "emoji": true
                        },
                        "value": "in 3 days"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Week",
                            "emoji": true
                        },
                        "value": "in 1 Week"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Month",
                            "emoji": true
                        },
                        "value": "in 1 Month"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Never",
                            "emoji": true
                        },
                        "value": "no_expire"
                    }
                ],
                "action_id": "duration"
            },
            "label": {
                "type": "plain_text",
                "text": "Expiration",
                "emoji": true
            }
        },
        {
            "type": "input",
            "block_id": "justification",
            "element": {
                "type": "plain_text_input",
                "multiline": true,
                "action_id": "justification",
                "placeholder": {
                    "type": "plain_text",
                    "text": "I need access for..."
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Justification",
                "emoji": true
            }
        }
    ]
}"""
)

self_service_step_1_option_selection = json.loads(
    """{
    "type": "modal",
    "callback_id": "self_service_step_1",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "submit": {
        "type": "plain_text",
        "text": "Next",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "blocks": [
        {
            "type": "input",
            "block_id": "self_service_step_1_block",
            "element": {
                "type": "radio_buttons",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Request access to an application, group, or AWS permission set",
                            "emoji": true
                        },
                        "value": "request_access_to_identity"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Request Permission or tag changes to a cloud identity",
                            "emoji": true
                        },
                        "value": "request_permissions_for_identity"
                    }
                ],
                "action_id": "self_service_step_1_option_selection"
            },
            "label": {
                "type": "plain_text",
                "text": "What would you like to do?",
                "emoji": true
            }
        }
    ]
}"""
)

self_service_request_permissions_step_2_option_selection = json.loads(
    """{
    "type": "modal",
    "callback_id": "self_service_request_permissions_step_2_option_selection",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "submit": {
        "type": "plain_text",
        "text": "Next",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "blocks": [
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
                            "emoji": true
                        },
                        "value": "select_predefined_policy"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Inline Policy",
                            "emoji": true
                        },
                        "value": "update_inline_policies"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Managed Policy",
                            "emoji": true
                        },
                        "value": "update_managed_policies"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Tags",
                            "emoji": true
                        },
                        "value": "update_tags"
                    }
                ],
                "action_id": "self_service_step_2_option_selection"
            },
            "label": {
                "type": "plain_text",
                "text": "What type of permissions change would you like?",
                "emoji": true
            }
        }
    ]
}"""
)

select_desired_managed_policies_modal = json.loads(
    """{
    "type": "modal",
    "callback_id": "request_permissions_to_resource",
    "title": {
        "type": "plain_text",
        "text": "Noq",
        "emoji": true
    },
    "submit": {
        "type": "plain_text",
        "text": "Submit Request",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "blocks": [
        {
            "type": "section",
            "block_id": "select_identities",
            "text": {
                "type": "mrkdwn",
                "text": "*Identities*"
            },
            "accessory": {
                "action_id": "select_identities_action",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select identities"
                },
                "min_query_length": 2
            }
        },
        {
            "type": "section",
            "block_id": "select_managed_policies",
            "text": {
                "type": "mrkdwn",
                "text": "*Managed Policies*"
            },
            "accessory": {
                "action_id": "select_managed_policies_action",
                "type": "multi_external_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select managed policies"
                },
                "min_query_length": 2
            }
        },
        {
            "type": "input",
            "block_id": "duration",
            "element": {
                "type": "static_select",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Hour",
                            "emoji": true
                        },
                        "value": "in 1 hour"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "2 Hours",
                            "emoji": true
                        },
                        "value": "in 2 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "4 Hours",
                            "emoji": true
                        },
                        "value": "in 4 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "8 Hours",
                            "emoji": true
                        },
                        "value": "in 8 hours"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "24 Hours",
                            "emoji": true
                        },
                        "value": "in 1 day"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "3 Days",
                            "emoji": true
                        },
                        "value": "in 3 days"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Week",
                            "emoji": true
                        },
                        "value": "in 1 Week"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "1 Month",
                            "emoji": true
                        },
                        "value": "in 1 Month"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Never",
                            "emoji": true
                        },
                        "value": "no_expire"
                    }
                ],
                "action_id": "duration"
            },
            "label": {
                "type": "plain_text",
                "text": "Expiration",
                "emoji": true
            }
        },
        {
            "type": "input",
            "block_id": "justification",
            "element": {
                "type": "plain_text_input",
                "multiline": true,
                "action_id": "justification",
                "placeholder": {
                    "type": "plain_text",
                    "text": "I need this for..."
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Justification",
                "emoji": true
            }
        }
    ]
}"""
)


self_service_submission_success = """
{
  "type": "modal",
  "callback_id": "request_success",
  "title": {
    "type": "plain_text",
    "text": "Request Successful"
  },
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Your request has been successfully submitted. Click the link below to view more details:"
      }
    },
    {
      "type": "section",
      "block_id": "view_details_section",
      "text": {
        "type": "mrkdwn",
        "text": "{{pull_request_url}}"
      }
    }
  ],
  "submit": {
    "type": "plain_text",
    "text": "Close"
  }
}
"""


def get_self_service_submission_success_blocks(pull_request_url: str):
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Your request has been successfully submitted. Click the link below to view more details:",
            },
        },
        {
            "type": "section",
            "block_id": "view_details_section",
            "text": {"type": "mrkdwn", "text": pull_request_url},
        },
    ]


def self_service_permissions_review_blocks(
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

    pull_request_id = pull_request_url.split("/")[-1]

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
                {"type": "mrkdwn", "text": f"*Requested Resources:*\n {resource_text}"},
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
            "text": {"type": "mrkdwn", "text": f"*Justification:*\n {justification}"},
        },
        {
            "type": "actions",
            "block_id": "review_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "emoji": True, "text": "Approve"},
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
                    "action_id": "edit_request",
                },
            ],
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"branch_name/{branch_name}",
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"duration/{raw_duration}",
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"request_id/{request_id}",
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"user_email/{user_email}",
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"pull_request_id/{pull_request_id}",
        }
        # TODO: Allow approvers to approve or deny the request within Slack
        # Caveat: Requests with changes to multiple files will require different
        # approval flows
        # {
        #     "type": "actions",
        #     "block_id": "approval_denial",
        #     "elements": [
        #         {
        #             "type": "button",
        #             "text": {
        #                 "type": "plain_text",
        #                 "text": "Approve"
        #             },
        #             "style": "primary",
        #             "value": "approve",
        #             "action_id": "approve_request"
        #         },
        #         {
        #             "type": "button",
        #             "text": {
        #                 "type": "plain_text",
        #                 "text": "Deny"
        #             },
        #             "style": "danger",
        #             "value": "deny",
        #             "action_id": "deny_request"
        #         }
        #     ]
        # }
    ]


update_or_remove_tags_modal = {
    "type": "modal",
    "callback_id": "request_update_or_remove_tags",
    "title": {"type": "plain_text", "text": "Tag Management", "emoji": True},
    "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
    "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
    "blocks": [
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
                "placeholder": {"type": "plain_text", "text": "Select identities"},
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
                        "value": "add_update",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Remove", "emoji": True},
                        "value": "remove",
                    },
                ],
            },
            "label": {"type": "plain_text", "text": "Tag Action", "emoji": True},
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
                "placeholder": {"type": "plain_text", "text": "I need access for..."},
            },
            "label": {"type": "plain_text", "text": "Justification", "emoji": True},
        },
    ],
}

self_service_step_1_blocks = """[
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":wave: Hello! What do you need help with?"
			},
            "block_id": "self-service-select",
			"accessory": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select an item",
					"emoji": true
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Okta Application",
							"emoji": true
						},
						"value": "NOQ::Okta::App"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Okta Group Membership",
							"emoji": true
						},
						"value": "NOQ::Okta::Group"
					},
                    {
						"text": {
							"type": "plain_text",
							"text": "Google Group Membership",
							"emoji": true
						},
						"value": "NOQ::Google::Group"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "AWS Console or Credentials",
							"emoji": true
						},
						"value": "aws-console-credentials"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "AWS Permissions or Tags",
							"emoji": true
						},
						"value": "aws-permissions-or-tags"
					}
				],
				"action_id": "self-service-select"
			}
		}
	]"""


def generate_self_service_step_2_app_group_access(
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
    friendly_resource_type_name = friendly_resource_type_names.get(
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

    select_resources = {
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
    if selected_options is not None:
        select_resources["element"]["initial_options"] = selected_options
    elements.append(select_resources)

    elements.append(
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
                {
                    "text": {"type": "plain_text", "text": "1 Hour", "emoji": True},
                    "value": "in 1 hour",
                },
                {
                    "text": {"type": "plain_text", "text": "2 Hours", "emoji": True},
                    "value": "in 2 hours",
                },
                {
                    "text": {"type": "plain_text", "text": "4 Hours", "emoji": True},
                    "value": "in 4 hours",
                },
                {
                    "text": {"type": "plain_text", "text": "8 Hours", "emoji": True},
                    "value": "in 8 hours",
                },
                {
                    "text": {"type": "plain_text", "text": "24 Hours", "emoji": True},
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
                    "text": {"type": "plain_text", "text": "1 Month", "emoji": True},
                    "value": "in 1 Month",
                },
                {
                    "text": {"type": "plain_text", "text": "Forever", "emoji": True},
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
    elements.append(duration_block)
    elements.append(
        {"type": "section", "text": {"type": "mrkdwn", "text": "Why do you need it?"}}
    )

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

    elements.append(justification_block)

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
                    # TODO: Change to update?
                    "value": "create_request",
                    "action_id": "create_request",
                }
            ],
        }
    )

    elements.append(
        {
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
    )

    elements.append(
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": resource_type,
        }
    )

    elements.append(
        {
            "type": "section",
            "text": {"type": "plain_text", "text": " ", "emoji": True},
            "block_id": f"update/{update}",
        }
    )

    if channel_id:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"channel_id/{channel_id}",
            }
        )

    if message_ts:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"message_ts/{message_ts}",
            }
        )

    if branch_name:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"branch_name/{branch_name}",
            }
        )
    if pull_request_id:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"pull_request_id/{pull_request_id}",
            }
        )
    if user_email:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"user_email/{user_email}",
            }
        )
    if request_id:
        elements.append(
            {
                "type": "section",
                "text": {"type": "plain_text", "text": " ", "emoji": True},
                "block_id": f"request_id/{request_id}",
            }
        )

    return elements


#     return [
# 		{
# 			"type": "section",
# 			"text": {
# 				"type": "mrkdwn",
# 				"text": f"Which {friendly_resource_type_name} would you like access to?"
# 			}
# 		},
# 		{
# 			"type": "input",
#             "block_id": "select_resources",
# 			"element": {
# 				"action_id": f"select_resources/{resource_type}",
# 				"type": "multi_external_select",
# 				"placeholder": {
# 					"type": "plain_text",
# 					"text": f"Select {friendly_resource_type_name}"
# 				},
# 				"min_query_length": 2
# 			},
# 			"label": {
# 				"type": "plain_text",
# 				"text": " ",
# 				"emoji": True
# 			}
# 		},
# 		{
# 			"type": "section",
# 			"text": {
# 				"type": "mrkdwn",
# 				"text": "How long do you need it for?"
# 			}
# 		},
# 		{
# 			"type": "input",
# 			"block_id": "duration",
# 			"element": {
# 				"type": "static_select",
# 				"options": [
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "1 Hour",
# 							"emoji": True
# 						},
# 						"value": "in 1 hour"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "2 Hours",
# 							"emoji": True
# 						},
# 						"value": "in 2 hours"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "4 Hours",
# 							"emoji": True
# 						},
# 						"value": "in 4 hours"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "8 Hours",
# 							"emoji": True
# 						},
# 						"value": "in 8 hours"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "24 Hours",
# 							"emoji": True
# 						},
# 						"value": "in 1 day"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "3 Days",
# 							"emoji": True
# 						},
# 						"value": "in 3 days"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "1 Week",
# 							"emoji": True
# 						},
# 						"value": "in 1 Week"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "1 Month",
# 							"emoji": True
# 						},
# 						"value": "in 1 Month"
# 					},
# 					{
# 						"text": {
# 							"type": "plain_text",
# 							"text": "Forever",
# 							"emoji": True
# 						},
# 						"value": "no_expire"
# 					}
# 				],
# 				"action_id": "duration"
# 			},
# 			"label": {
# 				"type": "plain_text",
# 				"text": " ",
# 				"emoji": True
# 			}
# 		},
# 		{
# 			"type": "section",
# 			"text": {
# 				"type": "mrkdwn",
# 				"text": "Why do you need it?"
# 			}
# 		},
# 		{
# 			"type": "input",
# 			"block_id": "justification",
# 			"element": {
# 				"type": "plain_text_input",
# 				"multiline": True,
# 				"action_id": "justification",
# 				"placeholder": {
# 					"type": "plain_text",
# 					"text": "I need access for..."
# 				}
# 			},
# 			"label": {
# 				"type": "plain_text",
# 				"text": " ",
# 				"emoji": True
# 			}
# 		},
# 		{
# 			"type": "actions",
#             "block_id": "create_button_block",
# 			"elements": [
# 				{
# 					"type": "button",
# 					"text": {
# 						"type": "plain_text",
# 						"text": "Create my request",
# 						"emoji": True
# 					},
# 					"value": "create_request",
# 					"action_id": "create_request"
# 				}
# 			]
# 		},
#   {
# 			"type": "actions",
#             "block_id": "cancel_button_block",
# 			"elements": [
# 				{
# 					"type": "button",
# 					"text": {
# 						"type": "plain_text",
# 						"text": "Cancel",
# 						"emoji": True
# 					},
# 					"value": "cancel_request",
#                     "style": "danger",
# 					"action_id": "cancel_request"
# 				}
# 			]
# 		},
#         {
# 			"type": "section",
# 			"text": {
# 				"type": "plain_text",
# 				"text": " ",
# 				"emoji": True
# 			},
# 			"block_id": resource_type
# 		},
#         {
# 			"type": "section",
# 			"text": {
# 				"type": "plain_text",
# 				"text": " ",
# 				"emoji": True
# 			},
# 			"block_id": f"update/{update}"
# 		},
#     ]
