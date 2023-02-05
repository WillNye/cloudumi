import json

from humanfriendly import format_timespan

request_permissions_to_resource_block = None  # TODO

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
				"min_query_length": 1
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
						"value": "3600"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "2 Hours",
							"emoji": true
						},
						"value": "7200"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "4 Hours",
							"emoji": true
						},
						"value": "14400"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "8 Hours",
							"emoji": true
						},
						"value": "28800"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "24 Hours",
							"emoji": true
						},
						"value": "86400"
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
                "text": "Submitting response... Please wait.",
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
                "action_id": "select_resources_action",
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
                        "value": "list"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Read*",
                            "emoji": true
                        },
                        "value": "read"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Write",
                            "emoji": true
                        },
                        "value": "write"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Permissions Management",
                            "emoji": true
                        },
                        "value": "permissions_management"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Tagging",
                            "emoji": true
                        },
                        "value": "tagging"
                    }
                ],
                "action_id": "desired_permissions"
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
                        "value": "3600"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "2 Hours",
                            "emoji": true
                        },
                        "value": "7200"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "4 Hours",
                            "emoji": true
                        },
                        "value": "14400"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "8 Hours",
                            "emoji": true
                        },
                        "value": "28800"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "24 Hours",
                            "emoji": true
                        },
                        "value": "86400"
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
							"text": "Request Access",
							"emoji": true
						},
						"value": "request_access_to_identity"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Request Cloud Permissions",
							"emoji": true
						},
						"value": "request_permissions_for_identity"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Create a cloud identity or resource",
							"emoji": true
						},
						"value": "create_cloud_identity_or_resource"
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
            "element": {
                "type": "radio_buttons",
                "options": [
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
                "action_id": "self-service-step-2-option-selection"
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
				"min_query_length": 1
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
				"min_query_length": 1
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
						"value": "3600"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "2 Hours",
							"emoji": true
						},
						"value": "7200"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "4 Hours",
							"emoji": true
						},
						"value": "14400"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "8 Hours",
							"emoji": true
						},
						"value": "28800"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "24 Hours",
							"emoji": true
						},
						"value": "86400"
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


def self_service_permissions_review_blocks(
    requester, resources, duration, approvers, justification, pull_request_url
):

    if duration == "no_expire":
        duration_friendly = "Forever"
    else:
        duration_friendly = format_timespan(int(duration))

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
                    f"Please review it at {pull_request_url}"
                ),
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Requester:*\n {requester}"},
                {"type": "mrkdwn", "text": f"*Requested Resources:*\n {resource_text}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Length of Access:*\n {duration_friendly}",
                },
                {"type": "mrkdwn", "text": f"*Approvers:*\n {approvers}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Justification:*\n {justification}"},
        },
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
